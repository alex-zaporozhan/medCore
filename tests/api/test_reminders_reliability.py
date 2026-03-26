"""Regression tests: reminders task reliability."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.core.datetime_utils import utc_now
from src.domain.entities.booking import Booking
from src.domain.entities.notification import Notification
from src.infrastructure.database.base import AsyncSessionLocal
from src.infrastructure.messaging.tasks import notifications as notifications_tasks


async def _create_confirmed_booking(seed_data: dict, patient_id):
    async with AsyncSessionLocal() as session:
        booking = Booking(
            id=uuid4(),
            clinic_id=seed_data["clinic_id"],
            patient_id=patient_id,
            doctor_id=seed_data["doctor_id"],
            service_id=seed_data["service_id"],
            appointment_date=(utc_now() + timedelta(hours=24)).date(),
            appointment_time=(utc_now() + timedelta(hours=24)).time().replace(microsecond=0),
            status="confirmed",
            prepayment_amount=0,
        )
        session.add(booking)
        await session.commit()
        return booking.id


@pytest.mark.asyncio
async def test_run_reminders_task_signature_and_dedup(seed_data: dict):
    """run_reminders task can run and does not enqueue duplicate reminder for same booking/template."""
    booking_id = await _create_confirmed_booking(seed_data, seed_data["patient_id"])
    enqueued: list[str] = []

    class _FakeTask:
        @staticmethod
        def delay(value: str):
            enqueued.append(value)

    original_24 = notifications_tasks.send_reminder_24h_task
    original_2 = notifications_tasks.send_reminder_2h_task
    notifications_tasks.send_reminder_24h_task = _FakeTask  # type: ignore[assignment]
    notifications_tasks.send_reminder_2h_task = _FakeTask  # type: ignore[assignment]
    try:
        notifications_tasks.run_reminders_task()
        assert str(booking_id) in enqueued

        async with AsyncSessionLocal() as session:
            session.add(
                Notification(
                    clinic_id=seed_data["clinic_id"],
                    patient_id=seed_data["patient_id"],
                    admin_id=None,
                    booking_id=booking_id,
                    channel="sms",
                    template="reminder_24h",
                    payload={"booking_id": str(booking_id)},
                    status="sent",
                    error=None,
                    sent_at=utc_now(),
                )
            )
            await session.commit()

        enqueued.clear()
        notifications_tasks.run_reminders_task()
        assert str(booking_id) not in enqueued
    finally:
        notifications_tasks.send_reminder_24h_task = original_24
        notifications_tasks.send_reminder_2h_task = original_2

    async with AsyncSessionLocal() as session:
        row = await session.execute(
            select(Notification).where(
                Notification.booking_id == booking_id,
                Notification.template == "reminder_24h",
            )
        )
        assert row.scalar_one_or_none() is not None
