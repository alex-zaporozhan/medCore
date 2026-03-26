"""Celery tasks for booking and reminder notifications."""

import asyncio
import logging
from uuid import UUID

from src.core.datetime_utils import utc_now

from sqlalchemy import select

from src.application.services.notification_service import send_with_fallback
from src.domain.entities.booking import Booking
from src.domain.entities.clinic import Clinic
from src.domain.entities.notification import Notification
from src.domain.entities.patient import Patient
from src.infrastructure.database.base import AsyncSessionLocal
from src.infrastructure.messaging.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _send_notification_async(
    clinic_id: UUID,
    patient_id: UUID | None,
    booking_id: UUID | None,
    channel: str,
    template: str,
    message: str,
    meta: dict,
) -> None:
    """Create notification record, call delivery (Telegram/SMS/log), update status."""
    async with AsyncSessionLocal() as session:
        try:
            async with session.begin():
                notification = Notification(
                    clinic_id=clinic_id,
                    patient_id=patient_id,
                    admin_id=None,
                    booking_id=booking_id,
                    channel=channel,
                    template=template,
                    payload={"message": message, **meta},
                    status="pending",
                    error=None,
                    sent_at=None,
                )
                session.add(notification)
                await session.flush()

                chat_id: str | None = None
                phone: str | None = None
                email: str | None = None
                preferred_channel = channel
                if patient_id:
                    patient_result = await session.execute(
                        select(Patient).where(Patient.id == patient_id)
                    )
                    patient = patient_result.scalar_one_or_none()
                    if patient:
                        chat_id = patient.telegram_chat_id
                        phone = patient.phone
                        email = patient.email
                        preferred_channel = patient.preferred_channel or channel

                success, error_msg = await send_with_fallback(
                    chat_id=chat_id,
                    phone=phone,
                    email=email,
                    message=message,
                    template=template,
                    meta=meta,
                    preferred_channel=preferred_channel,
                )
                now = utc_now()
                if success:
                    notification.status = "sent"
                    notification.sent_at = now
                else:
                    notification.status = "failed"
                    notification.error = error_msg
                    notification.sent_at = now
        except Exception:
            logger.exception("Notification save/send failed", extra={"template": template})
            raise


def _run_async(coro):
    """Run async coroutine from sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="notifications.send_booking_created", bind=True)
def send_booking_created_task(self, booking_id: str, trace_id: str | None = None):
    """Send notification when booking is created (patient + optional admin)."""
    bid = UUID(booking_id)

    async def _do():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == bid, Booking.deleted_at.is_(None))
            )
            booking = result.scalar_one_or_none()
            if not booking:
                logger.warning("send_booking_created: booking not found", extra={"booking_id": booking_id})
                return
            clinic_result = await session.execute(select(Clinic).where(Clinic.id == booking.clinic_id).limit(1))
            clinic = clinic_result.scalar_one_or_none()
            clinic_name = (clinic and clinic.name) or "Клиника"
            patient_result = await session.execute(select(Patient).where(Patient.id == booking.patient_id))
            patient = patient_result.scalar_one_or_none()
            phone = (patient and patient.phone) or ""
            channel = (patient and patient.preferred_channel) or "sms"

        message = (
            f"Запись создана в {clinic_name}. "
            f"Дата: {booking.appointment_date}, время: {booking.appointment_time}. "
            f"Оплатите предоплату для подтверждения."
        )
        await _send_notification_async(
            clinic_id=booking.clinic_id,
            patient_id=booking.patient_id,
            booking_id=booking.id,
            channel=channel,
            template="new_booking",
            message=message,
            meta={
                "booking_id": str(booking.id),
                "phone": phone,
                "trace_id": trace_id or "",
            },
        )
        # Optional: notify admin in Telegram (admin_chat_id from TELEGRAM_BOT channel or env)
        from src.application.services.omnichannel_integrations_config_service import (
            OmnichannelIntegrationsConfigService,
        )
        config_svc = OmnichannelIntegrationsConfigService(session)
        admin_chat_id = await config_svc.get_telegram_admin_chat_id_for_clinic(booking.clinic_id)
        if admin_chat_id:
            try:
                await send_with_fallback(
                    chat_id=admin_chat_id,
                    message=f"Новая запись в {clinic_name}: {booking.appointment_date} {booking.appointment_time}.",
                    template="omni_ai_suggestion",
                    preferred_channel="telegram",
                )
            except Exception:
                logger.warning(
                    "send_booking_created: failed to notify admin in Telegram",
                    extra={"booking_id": str(booking.id), "clinic_id": str(booking.clinic_id)},
                )

    _run_async(_do())
    return {"booking_id": booking_id, "status": "sent"}


@celery_app.task(name="notifications.send_booking_cancelled", bind=True)
def send_booking_cancelled_task(self, booking_id: str, trace_id: str | None = None):
    """Send notification when booking is cancelled."""
    bid = UUID(booking_id)

    async def _do():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == bid, Booking.deleted_at.is_(None))
            )
            booking = result.scalar_one_or_none()
            if not booking:
                logger.warning("send_booking_cancelled: booking not found", extra={"booking_id": booking_id})
                return

        message = (
            f"Ваша запись на {booking.appointment_date} в {booking.appointment_time} отменена. "
            "При необходимости создайте новую запись."
        )
        await _send_notification_async(
            clinic_id=booking.clinic_id,
            patient_id=booking.patient_id,
            booking_id=booking.id,
            channel="sms",
            template="booking_cancelled",
            message=message,
            meta={
                "booking_id": str(booking.id),
                "trace_id": trace_id or "",
            },
        )
        # Optional: notify admin in Telegram
        from src.application.services.omnichannel_integrations_config_service import (
            OmnichannelIntegrationsConfigService,
        )
        config_svc = OmnichannelIntegrationsConfigService(session)
        admin_chat_id = await config_svc.get_telegram_admin_chat_id_for_clinic(booking.clinic_id)
        if admin_chat_id:
            try:
                await send_with_fallback(
                    chat_id=admin_chat_id,
                    message=f"Запись отменена: {booking.appointment_date} {booking.appointment_time}.",
                    template="omni_ai_suggestion",
                    preferred_channel="telegram",
                )
            except Exception:
                logger.warning(
                    "send_booking_cancelled: failed to notify admin in Telegram",
                    extra={"booking_id": str(booking.id), "clinic_id": str(booking.clinic_id)},
                )

    _run_async(_do())
    return {"booking_id": booking_id, "status": "sent"}


@celery_app.task(name="notifications.send_reminder_24h", bind=True)
def send_reminder_24h_task(self, booking_id: str, trace_id: str | None = None):
    """Send reminder 24 hours before appointment."""
    bid = UUID(booking_id)

    async def _do():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == bid, Booking.deleted_at.is_(None))
            )
            booking = result.scalar_one_or_none()
            if not booking or booking.status != "confirmed":
                return
            patient_result = await session.execute(select(Patient).where(Patient.id == booking.patient_id))
            patient = patient_result.scalar_one_or_none()

        message = (
            f"Напоминание: завтра у вас приём {booking.appointment_date} в {booking.appointment_time}. "
            "Подтвердите явку или отмените запись."
        )
        await _send_notification_async(
            clinic_id=booking.clinic_id,
            patient_id=booking.patient_id,
            booking_id=booking.id,
            channel=patient.preferred_channel if patient else "sms",
            template="reminder_24h",
            message=message,
            meta={
                "booking_id": str(booking.id),
                "trace_id": trace_id or "",
            },
        )

    _run_async(_do())
    return {"booking_id": booking_id, "status": "sent"}


@celery_app.task(name="notifications.send_reminder_2h", bind=True)
def send_reminder_2h_task(self, booking_id: str, trace_id: str | None = None):
    """Send reminder 2 hours before appointment."""
    bid = UUID(booking_id)

    async def _do():
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Booking).where(Booking.id == bid, Booking.deleted_at.is_(None))
            )
            booking = result.scalar_one_or_none()
            if not booking or booking.status != "confirmed":
                return
            patient_result = await session.execute(select(Patient).where(Patient.id == booking.patient_id))
            patient = patient_result.scalar_one_or_none()

        message = (
            f"Через 2 часа приём: {booking.appointment_date} в {booking.appointment_time}. "
            "Ждём вас."
        )
        await _send_notification_async(
            clinic_id=booking.clinic_id,
            patient_id=booking.patient_id,
            booking_id=booking.id,
            channel=patient.preferred_channel if patient else "sms",
            template="reminder_2h",
            message=message,
            meta={
                "booking_id": str(booking.id),
                "trace_id": trace_id or "",
            },
        )

    _run_async(_do())
    return {"booking_id": booking_id, "status": "sent"}


@celery_app.task(name="notifications.run_reminders", bind=True)
def run_reminders_task(self):
    """
    Periodic task (e.g. every 15 min): find confirmed bookings in 24h and 2h windows,
    enqueue send_reminder_24h and send_reminder_2h.
    """
    from datetime import timedelta

    now = utc_now()
    date_24 = (now + timedelta(hours=24)).date()
    date_2 = (now + timedelta(hours=2)).date()

    async def _do():
        async with AsyncSessionLocal() as session:
            for target_date, task_fn in ((date_24, send_reminder_24h_task), (date_2, send_reminder_2h_task)):
                result = await session.execute(
                    select(Booking).where(
                        Booking.status == "confirmed",
                        Booking.deleted_at.is_(None),
                        Booking.appointment_date == target_date,
                    )
                )
                for b in result.scalars().all():
                    template = "reminder_24h" if task_fn is send_reminder_24h_task else "reminder_2h"
                    already_queued_or_sent = await session.execute(
                        select(Notification.id)
                        .where(
                            Notification.booking_id == b.id,
                            Notification.template == template,
                        )
                        .limit(1)
                    )
                    if already_queued_or_sent.scalar_one_or_none() is not None:
                        continue
                    task_fn.delay(str(b.id))

    _run_async(_do())
    return {"status": "ok"}
