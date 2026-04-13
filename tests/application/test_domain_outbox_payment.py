"""Outbox enqueue + dispatch for PaymentSuccess (ADR-009)."""

from datetime import time
from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from src.application.services.domain_outbox_service import (
    dispatch_domain_outbox_batch,
    enqueue_payment_success_event,
)
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.domain_outbox import DomainOutbox
from src.domain.entities.payment import Payment
from src.infrastructure.database import base as db_base


@pytest.fixture(autouse=True)
async def _empty_domain_outbox_for_isolation(init_db):
    """
    Session-scoped seed shares one DB across modules; other tests can leave unpublished
    outbox rows while ``dispatch_domain_outbox_batch`` is capped (Settings.domain_outbox_dispatch_batch_limit).
    """
    async with db_base.engine.begin() as conn:
        await conn.execute(text("DELETE FROM domain_outbox"))
    yield


@pytest.mark.asyncio
async def test_payment_webhook_leaves_no_pending_outbox_after_dispatch(
    client: AsyncClient, seed_data: dict
):
    """After succeeded webhook, outbox row is published (post-commit dispatch)."""
    booking_id = uuid4()
    payment_row_id = uuid4()
    provider_pid = f"yookassa-outbox-{uuid4().hex[:12]}"
    clinic_id = seed_data["clinic_id"]
    appt_time = time(10, 0, 0)

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=seed_data["patient_id"],
                doctor_id=seed_data["doctor_id"],
                service_id=seed_data["service_id"],
                appointment_date=seed_data["date"],
                appointment_time=appt_time,
                status=BookingStatus.AWAITING_PAYMENT,
                prepayment_amount=500,
            )
        )
        session.add(
            Payment(
                id=payment_row_id,
                clinic_id=clinic_id,
                booking_id=booking_id,
                provider="yookassa",
                provider_payment_id=provider_pid,
                amount=500,
                currency="RUB",
                status="pending",
            )
        )
        await session.flush()
        booking = await session.get(Booking, booking_id)
        assert booking is not None
        booking.payment_id = payment_row_id
        await session.commit()

    class _FakeYooKassa:
        def get_payment(self, pid: str) -> dict:
            return {"status": "succeeded", "id": pid}

    with patch(
        "src.application.services.payment_service.YooKassaClient",
        return_value=_FakeYooKassa(),
    ):
        r = await client.post(
            "/api/v1/payments/webhook",
            json={
                "type": "notification",
                "event": "payment.succeeded",
                "object": {"id": provider_pid},
            },
        )
    assert r.status_code == 200

    async with db_base.AsyncSessionLocal() as session:
        result = await session.execute(
            select(DomainOutbox).where(DomainOutbox.dedup_key == f"payment_success:{payment_row_id}")
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.published_at is not None


@pytest.mark.asyncio
async def test_dispatch_domain_outbox_batch_second_run_empty(seed_data: dict):
    """Manual enqueue + dispatch: second batch processes nothing new."""
    booking_id = uuid4()
    payment_row_id = uuid4()
    clinic_id = seed_data["clinic_id"]
    appt_time = time(12, 0, 0)

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=seed_data["patient_id"],
                doctor_id=seed_data["doctor_id"],
                service_id=seed_data["service_id"],
                appointment_date=seed_data["date"],
                appointment_time=appt_time,
                status=BookingStatus.CONFIRMED,
                prepayment_amount=500,
            )
        )
        pay = Payment(
            id=payment_row_id,
            clinic_id=clinic_id,
            booking_id=booking_id,
            provider="yookassa",
            provider_payment_id=f"manual-{uuid4().hex[:10]}",
            amount=500,
            currency="RUB",
            status="succeeded",
        )
        session.add(pay)
        await session.flush()
        booking = await session.get(Booking, booking_id)
        assert booking is not None
        booking.payment_id = payment_row_id
        await enqueue_payment_success_event(session, pay)
        await session.commit()

    n1 = await dispatch_domain_outbox_batch(limit=20)
    assert n1 == 1
    n2 = await dispatch_domain_outbox_batch(limit=20)
    assert n2 == 0

    async with db_base.AsyncSessionLocal() as session:
        result = await session.execute(
            select(DomainOutbox).where(DomainOutbox.dedup_key == f"payment_success:{payment_row_id}")
        )
        row = result.scalar_one()
        assert row.published_at is not None


@pytest.mark.asyncio
async def test_dispatch_increments_attempts_on_corrupt_payload():
    """Malformed outbox payload must not spin silently; attempts + last_error set."""
    oid = uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(
            DomainOutbox(
                id=oid,
                aggregate_type="test",
                aggregate_id=uuid4(),
                event_type="PaymentSuccess",
                payload={"invalid": True},
                dedup_key=None,
            )
        )
        await session.commit()

    published = await dispatch_domain_outbox_batch(limit=10)
    assert published == 0

    async with db_base.AsyncSessionLocal() as session:
        row = await session.get(DomainOutbox, oid)
        assert row is not None
        assert row.attempts >= 1
        assert row.last_error is not None
        assert "corrupt_outbox_payload" in row.last_error
