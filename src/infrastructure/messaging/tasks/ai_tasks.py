"""Celery tasks related to AI-generated operational tasks."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from celery import shared_task
from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.domain.entities.booking import Booking
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.clinic import Clinic
from src.domain.entities.clinic_ai_settings import ClinicAiSettings
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.payroll_policy import PayrollPolicy
from src.infrastructure.external_apis.ai_client import AiClient
from src.application.services.task_service import TaskService
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl


# JSON contract for AI response: list of task suggestions
class AiTaskSuggestionItem(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    role_assignee: str | None = None
    due_at: datetime | None = None
    links: dict[str, Any] | None = None  # e.g. {"booking_ids": [...], "patient_ids": [...]}


class AiTaskSuggestionsResponse(BaseModel):
    tasks: list[AiTaskSuggestionItem] = Field(default_factory=list)


async def _build_session() -> AsyncSession:
    """
    Create a short-lived AsyncSession for use inside Celery tasks.

    Celery работает в отдельном процессе, поэтому мы создаём отдельный движок
    и фабрику сессий, не завися от FastAPI DI.
    """
    engine = create_async_engine(settings.database_url, echo=settings.debug)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    return session_factory()


async def _collect_daily_anomalies(session: AsyncSession) -> list[dict[str, Any]]:
    """Собрать аномалии за период для AI Task Generator: отмены, no-show, ERP, CRM."""
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    anomalies: list[dict[str, Any]] = []

    # Отменённые записи за сутки
    cancelled_stmt: Select = select(Booking).where(
        and_(
            Booking.status == "cancelled",
            Booking.updated_at >= day_ago,
        )
    )
    cancelled_result = await session.execute(cancelled_stmt)
    cancelled = cancelled_result.scalars().all()
    if cancelled:
        anomalies.append(
            {
                "type": "cancellations",
                "count": len(cancelled),
                "booking_ids": [str(b.id) for b in cancelled],
            }
        )

    # No-show за сутки
    no_show_stmt = select(Booking).where(
        and_(
            Booking.status == "no_show",
            Booking.updated_at >= day_ago,
        )
    )
    no_show_result = await session.execute(no_show_stmt)
    no_shows = no_show_result.scalars().all()
    if no_shows:
        anomalies.append(
            {
                "type": "no_shows",
                "count": len(no_shows),
                "booking_ids": [str(b.id) for b in no_shows],
            }
        )

    # Клиники без кассы
    subq = select(Cashbox.clinic_id).distinct()
    clinics_with_cashbox = await session.execute(subq)
    clinic_ids_with_cashbox = {r[0] for r in clinics_with_cashbox.all()}
    all_clinics = await session.execute(select(Clinic.id))
    all_clinic_ids = {r[0] for r in all_clinics.all()}
    no_cashbox = all_clinic_ids - clinic_ids_with_cashbox
    if no_cashbox:
        anomalies.append(
            {
                "type": "no_cashbox",
                "clinic_ids": [str(cid) for cid in no_cashbox],
            }
        )

    # Клиники без ни одной политики ЗП
    subq_payroll = select(PayrollPolicy.clinic_id).distinct()
    clinics_with_payroll = await session.execute(subq_payroll)
    clinic_ids_payroll = {r[0] for r in clinics_with_payroll.all()}
    no_payroll = all_clinic_ids - clinic_ids_payroll
    if no_payroll:
        anomalies.append(
            {
                "type": "no_payroll_policy",
                "clinic_ids": [str(cid) for cid in no_payroll],
            }
        )

    # Лиды без движения 7+ дней (open)
    leads_stale = await session.execute(
        select(LeadCard).where(
            and_(
                LeadCard.status == "open",
                LeadCard.updated_at < week_ago,
            )
        )
    )
    leads = leads_stale.scalars().all()
    if leads:
        anomalies.append(
            {
                "type": "leads_without_movement",
                "count": len(leads),
                "lead_ids": [str(l.id) for l in leads],
            }
        )

    return anomalies


@shared_task(name="ai_tasks.run_ai_task_generator")
def run_ai_task_generator() -> None:
    """
    Periodic Celery job that asks AI to propose operational tasks for clinics.

    - собирает аномалии за период;
    - вызывает AiClient в режиме аналитики;
    - создаёт Task с source="ai_auto".
    """

    import asyncio

    async def _run() -> None:
        session = await _build_session()
        try:
            # Только клиники с включённым AI Task Generator (флаг ai_tasks_enabled отдельно от ai_enabled)
            settings_stmt = select(ClinicAiSettings).where(
                ClinicAiSettings.ai_tasks_enabled.is_(True)
            )
            settings_result = await session.execute(settings_stmt)
            clinics_settings = settings_result.scalars().all()
            if not clinics_settings:
                return

            anomalies = await _collect_daily_anomalies(session)
            if not anomalies:
                return

            ai_client = AiClient()
            if not ai_client.is_configured():
                return

            payload: dict[str, Any] = {
                "model": settings.ai_provider_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ты помощник операционного менеджера клиники. На основе списка аномалий "
                            "предложи задачи для администраторов/менеджеров. Верни JSON с ключом 'tasks' — "
                            "массив объектов с полями: title (обязательно), description, priority (low|medium|high|urgent), "
                            "role_assignee (admin|manager|doctor), due_at (ISO datetime), links (объект с booking_ids, patient_ids и т.д.)."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Аномалии за период: {anomalies}",
                    },
                ],
            }

            data = await ai_client.complete(payload)
            tasks_raw = data.get("tasks") if isinstance(data, dict) else None
            if not isinstance(tasks_raw, list):
                return

            # Строгая валидация: только валидные элементы создаём как задачи
            validated: list[AiTaskSuggestionItem] = []
            for item in tasks_raw:
                if not isinstance(item, dict):
                    continue
                try:
                    validated.append(AiTaskSuggestionItem.model_validate(item))
                except Exception:
                    continue

            repo = TaskRepositoryImpl(session)
            service = TaskService(repo)

            for clinic_setting in clinics_settings:
                for t in validated:
                    await service.create_task(
                        clinic_id=clinic_setting.clinic_id,
                        title=t.title[:500],
                        description=t.description,
                        priority=t.priority,
                        due_at=t.due_at,
                        role_assignee=t.role_assignee,
                        source="ai_auto",
                        source_event_id=None,
                    )

            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    asyncio.run(_run())

