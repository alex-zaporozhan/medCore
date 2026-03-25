"""Celery tasks: Owner Morning Brief and AI Supervisor Summary to Telegram (B5.6)."""

import asyncio
import logging
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from src.core.config import settings
from src.domain.entities.owner_integration_settings import OwnerIntegrationSettings
from src.infrastructure.database.base import AsyncSessionLocal
from src.infrastructure.external_apis.telegram_sender import TelegramSender, TelegramSenderError
from src.infrastructure.messaging.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_owner_chat_id_fallback() -> str | None:
    """Fallback: config/env when no DB settings."""
    chat_id = (getattr(settings, "telegram_owner_chat_id", None) or "") or (
        (settings.telegram_admin_chat_id or "").strip()
    )
    return chat_id if chat_id else None


async def _send_owner_morning_brief_async(
    clinic_id: str | None = None,
    chat_id_override: str | None = None,
) -> None:
    """Build morning brief for clinic and send to Telegram. chat_id_override or from OwnerIntegrationSettings or config."""
    if not (settings.telegram_bot_token or "").strip():
        logger.debug("owner_integrations: no telegram bot token, skip morning brief")
        return

    yesterday = date.today() - timedelta(days=1)
    async with AsyncSessionLocal() as session:
        chat_id = chat_id_override
        if not chat_id and clinic_id:
            try:
                clinic_uuid = UUID(clinic_id)
                row = await session.execute(
                    select(OwnerIntegrationSettings).where(
                        OwnerIntegrationSettings.clinic_id == clinic_uuid,
                        OwnerIntegrationSettings.owner_morning_brief_enabled.is_(True),
                    ).limit(1)
                )
                r = row.scalar_one_or_none()
                if r and (r.owner_telegram_chat_id or "").strip():
                    chat_id = r.owner_telegram_chat_id.strip()
            except (ValueError, Exception):
                pass
        if not chat_id:
            chat_id = _get_owner_chat_id_fallback()
        if not chat_id:
            logger.debug("owner_integrations: no telegram chat_id configured, skip morning brief")
            return

        from src.application.services.report_service import ReportsService

        report_svc = ReportsService(session)
        clinic_uuid: UUID | None = None
        if clinic_id:
            try:
                clinic_uuid = UUID(clinic_id)
            except ValueError:
                pass
        try:
            dashboard = await report_svc.get_dashboard_report(yesterday, clinic_id=clinic_uuid)
        except Exception as e:
            logger.warning("owner_integrations: failed to get dashboard report", extra={"error": str(e)})
            return

        total_bookings = (
            int(dashboard.bookings_pending)
            + int(dashboard.bookings_confirmed)
            + int(dashboard.bookings_completed)
            + int(dashboard.bookings_cancelled)
            + int(dashboard.bookings_no_show)
        )
        served_bookings = int(dashboard.bookings_completed)
        completion_rate = (served_bookings / total_bookings * 100.0) if total_bookings > 0 else 0.0
        no_show_rate = (int(dashboard.bookings_no_show) / total_bookings * 100.0) if total_bookings > 0 else 0.0

        risks: list[str] = []
        if int(dashboard.bookings_no_show) > 0:
            risks.append(f"no-show: {dashboard.bookings_no_show}")
        if int(dashboard.bookings_cancelled) > 0:
            risks.append(f"отмены: {dashboard.bookings_cancelled}")
        if float(dashboard.day_pulse_score) < 40:
            risks.append(f"низкий пульс дня: {dashboard.day_pulse_score}/100")
        risk_line = ", ".join(risks) if risks else "существенных рисков не выявлено"

        lines = [
            "📊 Утренний бриф",
            f"Дата: {yesterday}",
            "",
            "Сводка за вчера:",
            (
                "  Записи: "
                f"всего {total_bookings}, подтверждено {dashboard.bookings_confirmed}, "
                f"завершено {dashboard.bookings_completed}, отменено {dashboard.bookings_cancelled}, "
                f"no-show {dashboard.bookings_no_show}"
            ),
            f"  Конверсия в визит: {completion_rate:.1f}%",
            f"  No-show rate: {no_show_rate:.1f}%",
            f"  Новые пациенты: {dashboard.new_patients}",
            f"  Лиды: {dashboard.new_leads_count}",
            f"  Писали в чат: {dashboard.chat_writers_count}",
            f"  Пульс дня: {dashboard.day_pulse_score}/100",
            f"  Выручка: {dashboard.revenue}",
            "",
            f"Риски: {risk_line}",
            "Фокус на сегодня:",
            "  1) закрыть no-show / отмены с прозвоном;",
            "  2) подтвердить ближайшие записи;",
            "  3) догреть лиды и вернуть незавершённые диалоги.",
        ]
        text = "\n".join(lines)

        try:
            sender = TelegramSender()
            await sender.send(
                chat_id=chat_id,
                message=text,
                template="owner_morning_brief",
            )
            logger.info("owner_integrations: morning brief sent", extra={"chat_id": chat_id, "clinic_id": clinic_id})
        except TelegramSenderError as e:
            logger.warning("owner_integrations: telegram send failed", extra={"error": str(e)})


async def _send_ai_supervisor_summary_async(
    clinic_id: str | None = None,
    recipient_chat_ids_override: list[str] | None = None,
) -> None:
    """Build AI Supervisor daily summary and send to Telegram. Recipients from override or OwnerIntegrationSettings or config."""
    if not (settings.telegram_bot_token or "").strip():
        logger.debug("owner_integrations: no telegram bot token, skip ai supervisor summary")
        return

    today = date.today()
    async with AsyncSessionLocal() as session:
        chat_ids: list[str] = list(recipient_chat_ids_override) if recipient_chat_ids_override else []
        if not chat_ids and clinic_id:
            try:
                clinic_uuid = UUID(clinic_id)
                row = await session.execute(
                    select(OwnerIntegrationSettings).where(
                        OwnerIntegrationSettings.clinic_id == clinic_uuid,
                        OwnerIntegrationSettings.ai_supervisor_enabled.is_(True),
                    ).limit(1)
                )
                r = row.scalar_one_or_none()
                if r and r.ai_supervisor_recipient_chat_ids:
                    chat_ids = [c for c in r.ai_supervisor_recipient_chat_ids if c and str(c).strip()]
            except (ValueError, Exception):
                pass
        if not chat_ids:
            fallback = _get_owner_chat_id_fallback()
            if fallback:
                chat_ids = [fallback]
        if not chat_ids:
            logger.debug("owner_integrations: no recipient chat_ids, skip ai supervisor summary")
            return

        from src.application.services.attention_feed_service import AttentionFeedService
        from src.application.services.report_service import ReportsService

        report_svc = ReportsService(session)
        clinic_uuid: UUID | None = None
        if clinic_id:
            try:
                clinic_uuid = UUID(clinic_id)
            except ValueError:
                pass

        lines = ["📋 Итоги дня (AI Supervisor)", f"Дата: {today}", ""]

        try:
            feed_svc = AttentionFeedService(session)
            if clinic_uuid:
                feed = await feed_svc.get_feed(clinic_uuid)
                follow_up = len(feed.follow_up) if feed.follow_up else 0
                retention = len(feed.retention_gap) if feed.retention_gap else 0
                conflicts = len(feed.conflicts) if feed.conflicts else 0
                lines.append(f"Attention Feed: follow-up {follow_up}, retention {retention}, conflicts {conflicts}")
        except Exception as e:
            logger.warning("owner_integrations: attention feed failed", extra={"error": str(e)})
            lines.append("Attention Feed: (не удалось загрузить)")

        try:
            dashboard = await report_svc.get_dashboard_report(today, clinic_id=clinic_uuid)
            lines.append("")
            lines.append(f"Сегодня: отмены {dashboard.bookings_cancelled}, no-show {dashboard.bookings_no_show}")
        except Exception as e:
            logger.warning("owner_integrations: dashboard report failed", extra={"error": str(e)})

        text = "\n".join(lines)
        sender = TelegramSender()
        for chat_id in chat_ids:
            try:
                await sender.send(
                    chat_id=chat_id,
                    message=text,
                    template="ai_supervisor_summary",
                )
                logger.info("owner_integrations: ai supervisor summary sent", extra={"chat_id": chat_id, "clinic_id": clinic_id})
            except TelegramSenderError as e:
                logger.warning("owner_integrations: telegram send failed", extra={"chat_id": chat_id, "error": str(e)})


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="owner_integrations.send_owner_morning_brief")
def send_owner_morning_brief(clinic_id: str | None = None) -> None:
    """B5.6: Morning brief for owner (yesterday stats, today bookings). Runs at 09:00 UTC."""
    _run_async(_send_owner_morning_brief_async(clinic_id))


@celery_app.task(name="owner_integrations.send_ai_supervisor_summary")
def send_ai_supervisor_summary(clinic_id: str | None = None) -> None:
    """B5.6: Evening AI Supervisor summary (attention feed, cancellations, no-show). Runs at 20:00 UTC."""
    _run_async(_send_ai_supervisor_summary_async(clinic_id))


async def _send_all_morning_briefs_async() -> None:
    """Iterate clinics with owner_morning_brief_enabled and owner_telegram_chat_id; send brief for each. Fallback: config."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(OwnerIntegrationSettings).where(
                OwnerIntegrationSettings.owner_morning_brief_enabled.is_(True),
                OwnerIntegrationSettings.owner_telegram_chat_id.isnot(None),
                OwnerIntegrationSettings.owner_telegram_chat_id != "",
            )
        )
        rows = result.scalars().all()
    if rows:
        for row in rows:
            await _send_owner_morning_brief_async(
                clinic_id=str(row.clinic_id),
                chat_id_override=(row.owner_telegram_chat_id or "").strip(),
            )
    else:
        await _send_owner_morning_brief_async(None)


async def _send_all_ai_supervisor_summaries_async() -> None:
    """Iterate clinics with ai_supervisor_enabled and recipient_chat_ids; send summary for each. Fallback: config."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(OwnerIntegrationSettings).where(
                OwnerIntegrationSettings.ai_supervisor_enabled.is_(True),
            )
        )
        rows = result.scalars().all()
    if rows:
        for row in rows:
            ids = [c for c in (row.ai_supervisor_recipient_chat_ids or []) if c and str(c).strip()]
            if ids:
                await _send_ai_supervisor_summary_async(
                    clinic_id=str(row.clinic_id),
                    recipient_chat_ids_override=ids,
                )
    else:
        await _send_ai_supervisor_summary_async(None)


@celery_app.task(name="owner_integrations.send_all_morning_briefs")
def send_all_morning_briefs() -> None:
    """Beat: send morning brief for each clinic with enabled settings, or fallback to config."""
    _run_async(_send_all_morning_briefs_async())


@celery_app.task(name="owner_integrations.send_all_ai_supervisor_summaries")
def send_all_ai_supervisor_summaries() -> None:
    """Beat: send AI supervisor summary for each clinic with enabled settings, or fallback to config."""
    _run_async(_send_all_ai_supervisor_summaries_async())
