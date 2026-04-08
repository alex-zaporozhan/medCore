import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .event_bus import EventBus
from .standard_events import (
    BOOKING_CANCELLED,
    BOOKING_NO_SHOW,
    booking_event_dedup_id,
)
from .domain_event import DomainEvent
from src.application.services.task_service import TaskService
from src.domain.entities.booking import Booking
from src.domain.entities.task import Task
from src.domain.interfaces.repositories.task_repository import TaskRepository
from src.infrastructure.database.lead_repo_impl import LeadRepositoryImpl
from src.infrastructure.database.task_repo_impl import TaskRepositoryImpl
from src.infrastructure.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


def _parse_dedup_uuid(event: DomainEvent, event_name: str, booking_id: UUID) -> UUID:
    raw = event.payload.get("dedup_id")
    if raw:
        try:
            return UUID(str(raw))
        except Exception:
            pass
    return booking_event_dedup_id(event_name, booking_id)


async def _has_open_task_for_source_event(
    session: AsyncSession,
    clinic_id: UUID,
    source_event_id: UUID,
) -> bool:
    stmt = (
        select(Task.id)
        .where(
            Task.clinic_id == clinic_id,
            Task.source_event_id == source_event_id,
            Task.status.in_(("open", "in_progress")),
        )
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none() is not None


async def create_system_task_for_cancelled_booking(
    event: DomainEvent,
    session: AsyncSession,
) -> None:
    """Create system task when booking is cancelled (idempotent per dedup_id)."""
    booking_id_raw = event.payload.get("booking_id")
    if not booking_id_raw:
        logger.warning("[Tasks] BOOKING_CANCELLED without booking_id payload")
        return
    try:
        booking_id = UUID(str(booking_id_raw))
    except Exception:
        logger.warning(
            "[Tasks] BOOKING_CANCELLED with invalid booking_id payload",
            extra={"payload": event.payload},
        )
        return

    booking = await session.get(Booking, booking_id)
    if not booking:
        logger.warning(
            "[Tasks] Booking not found for cancelled event",
            extra={"booking_id": str(booking_id)},
        )
        return

    dedup_uuid = _parse_dedup_uuid(event, BOOKING_CANCELLED, booking_id)
    if await _has_open_task_for_source_event(session, booking.clinic_id, dedup_uuid):
        logger.info(
            "[Tasks] Skip duplicate BOOKING_CANCELLED task",
            extra={"booking_id": str(booking_id), "dedup_id": str(dedup_uuid)},
        )
        return

    lead_repo = LeadRepositoryImpl(session)
    lead = await lead_repo.get_lead_by_primary_booking_id(booking.clinic_id, booking.id)
    lead_id = lead.id if lead else None

    repo: TaskRepository = TaskRepositoryImpl(session)
    service = TaskService(repo)

    trace_id = event.payload.get("trace_id")
    trace_id_str = str(trace_id) if trace_id else None
    description = (
        "Запись отменена. Свяжитесь с пациентом, чтобы переназначить визит "
        "или предложить слот другим пациентам."
    )
    if trace_id:
        description += f" trace_id={trace_id} event_id={event.event_id}."

    due_at = datetime.now(timezone.utc) + timedelta(days=1)
    await service.create_task(
        clinic_id=booking.clinic_id,
        title="Обработать отменённую запись",
        description=description,
        priority="high",
        creator_id=None,
        assignee_id=None,
        role_assignee="admin",
        due_at=due_at,
        booking_id=booking.id,
        patient_id=booking.patient_id,
        lead_id=lead_id,
        source="system",
        source_event_id=dedup_uuid,
        trace_id=trace_id_str,
    )


async def create_system_task_for_no_show(
    event: DomainEvent,
    session: AsyncSession,
) -> None:
    """Create system task when patient no-shows (idempotent per dedup_id)."""
    booking_id_raw = event.payload.get("booking_id")
    if not booking_id_raw:
        logger.warning("[Tasks] BOOKING_NO_SHOW without booking_id payload")
        return
    try:
        booking_id = UUID(str(booking_id_raw))
    except Exception:
        logger.warning(
            "[Tasks] BOOKING_NO_SHOW with invalid booking_id payload",
            extra={"payload": event.payload},
        )
        return

    booking = await session.get(Booking, booking_id)
    if not booking:
        logger.warning(
            "[Tasks] Booking not found for no-show event",
            extra={"booking_id": str(booking_id)},
        )
        return

    dedup_uuid = _parse_dedup_uuid(event, BOOKING_NO_SHOW, booking_id)
    if await _has_open_task_for_source_event(session, booking.clinic_id, dedup_uuid):
        logger.info(
            "[Tasks] Skip duplicate BOOKING_NO_SHOW task",
            extra={"booking_id": str(booking_id), "dedup_id": str(dedup_uuid)},
        )
        return

    lead_repo = LeadRepositoryImpl(session)
    lead = await lead_repo.get_lead_by_primary_booking_id(booking.clinic_id, booking.id)
    lead_id = lead.id if lead else None

    repo: TaskRepository = TaskRepositoryImpl(session)
    service = TaskService(repo)

    trace_id = event.payload.get("trace_id")
    trace_id_str = str(trace_id) if trace_id else None
    description = (
        "Пациент не пришёл на приём. Свяжитесь с пациентом, уточните причину "
        "и предложите новую дату/время."
    )
    if trace_id:
        description += f" trace_id={trace_id} event_id={event.event_id}."

    due_at = datetime.now(timezone.utc) + timedelta(days=1)
    await service.create_task(
        clinic_id=booking.clinic_id,
        title="Обработать no-show пациента",
        description=description,
        priority="medium",
        creator_id=None,
        assignee_id=None,
        role_assignee="admin",
        due_at=due_at,
        booking_id=booking.id,
        patient_id=booking.patient_id,
        lead_id=lead_id,
        source="system",
        source_event_id=dedup_uuid,
        trace_id=trace_id_str,
    )


def register_tasks_event_handlers(event_bus: EventBus) -> None:
    """
    Register task-related event handlers.

    NOTE: EventBus handlers here are thin; they are expected to be wrapped with
    database session management at the publishing site (see event publisher / session scope).
    """

    async def _on_cancelled(event: DomainEvent) -> None:
        async with AsyncSessionLocal() as session:
            await create_system_task_for_cancelled_booking(event, session)
            await session.commit()

    async def _on_no_show(event: DomainEvent) -> None:
        async with AsyncSessionLocal() as session:
            await create_system_task_for_no_show(event, session)
            await session.commit()

    event_bus.subscribe(BOOKING_CANCELLED, _on_cancelled)
    event_bus.subscribe(BOOKING_NO_SHOW, _on_no_show)
