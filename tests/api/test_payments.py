"""Tests: POST /api/v1/payments/webhook and payment idempotency (contour A)."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.domain.entities.booking import Booking, BookingStatus, coerce_booking_status
from src.domain.entities.payment import Payment
from src.infrastructure.database import base as db_base
from src.infrastructure.external_apis.yookassa_client import YooKassaClientError
from tests.booking_slot import unique_booking_slot


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_payments_webhook(client: AsyncClient):
    """POST /api/v1/payments/webhook with mock YooKassa payload returns 200 and status ok."""
    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": "test-payment-unknown-id"},
    }
    response = await client.post(
        "/api/v1/payments/webhook",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_payments_webhook_succeeded_twice_idempotent(
    client: AsyncClient,
    seed_data: dict,
):
    """
    Two YooKassa payment.succeeded notifications with the same provider_payment_id
    must confirm the booking once (no duplicate transition / duplicate side effects).
    Mocks YooKassa API fetch; uses real DB row (LEAD / PRINCIPLE U-006).
    """
    booking_id = uuid4()
    payment_row_id = uuid4()
    provider_pid = f"yookassa-idem-{uuid4().hex[:16]}"
    clinic_id = seed_data["clinic_id"]
    slot_day, appt_time = unique_booking_slot(seed_data["date"], hour=16)

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=seed_data["patient_id"],
                doctor_id=seed_data["doctor_id"],
                service_id=seed_data["service_id"],
                appointment_date=slot_day,
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
        booking.payment_id = payment_row_id
        await session.commit()

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }

    class _FakeYooKassa:
        def get_payment(self, pid: str) -> dict:
            assert pid == provider_pid
            return {"status": "succeeded", "id": pid}

    with patch(
        "src.application.services.payment_service.YooKassaClient",
        return_value=_FakeYooKassa(),
    ):
        r1 = await client.post("/api/v1/payments/webhook", json=payload)
        r2 = await client.post("/api/v1/payments/webhook", json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json().get("status") == "ok"
    assert r2.json().get("status") == "ok"

    async with db_base.AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        pay = await session.get(Payment, payment_row_id)
        assert booking is not None
        assert coerce_booking_status(booking.status) == BookingStatus.CONFIRMED
        assert pay is not None
        assert pay.status == "succeeded"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_payments_webhook_yookassa_unavailable_returns_502(
    client: AsyncClient, seed_data: dict
):
    """P0-3: local payment row matched but YooKassa get_payment fails → 502 (PSP retry), not silent 2xx."""
    booking_id = uuid4()
    payment_row_id = uuid4()
    provider_pid = f"yookassa-verify-fail-{uuid4().hex[:12]}"
    clinic_id = seed_data["clinic_id"]
    slot_day, appt_time = unique_booking_slot(seed_data["date"], hour=11)

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=seed_data["patient_id"],
                doctor_id=seed_data["doctor_id"],
                service_id=seed_data["service_id"],
                appointment_date=slot_day,
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
        booking.payment_id = payment_row_id
        await session.commit()

    class _BoomYooKassa:
        def get_payment(self, pid: str) -> dict:
            assert pid == provider_pid
            raise YooKassaClientError("simulated upstream")

    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": provider_pid},
    }
    with patch(
        "src.application.services.payment_service.YooKassaClient",
        return_value=_BoomYooKassa(),
    ):
        r = await client.post("/api/v1/payments/webhook", json=payload)

    assert r.status_code == 502
    body = r.json()
    assert body.get("code") == "provider_verify_failed"

    async with db_base.AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        pay = await session.get(Payment, payment_row_id)
        assert booking is not None
        assert coerce_booking_status(booking.status) == BookingStatus.AWAITING_PAYMENT
        assert pay is not None
        assert pay.status == "pending"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_payments_webhook_optional_secret_header(client: AsyncClient, monkeypatch):
    """Contour A: when PATIENT_PAYMENT_WEBHOOK_SECRET is set, require X-Patient-Payment-Webhook-Secret (U-006)."""
    from src.core.config import settings
    from src.core.payment_webhook_governance import PATIENT_PAYMENT_WEBHOOK_SECRET_HEADER

    monkeypatch.setattr(settings, "patient_payment_webhook_secret", "whsec-patient-test")
    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": "no-such-payment"},
    }
    r403 = await client.post("/api/v1/payments/webhook", json=payload)
    assert r403.status_code == 403

    r_ok = await client.post(
        "/api/v1/payments/webhook",
        json=payload,
        headers={PATIENT_PAYMENT_WEBHOOK_SECRET_HEADER: "whsec-patient-test"},
    )
    assert r_ok.status_code == 200
    assert r_ok.json().get("status") == "ok"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_payments_webhook_rate_limited_per_ip(
    client: AsyncClient, monkeypatch
):
    """Contour A: Redis per-IP limit when enabled (symmetry with contour B)."""
    from src.core.config import settings
    from src.infrastructure.database.redis_client import get_redis

    monkeypatch.setattr(settings, "rate_patient_payment_webhook_ip_limit", 1)
    monkeypatch.setattr(settings, "rate_patient_payment_webhook_ip_window_seconds", 60)
    # Earlier tests in this module share the same ASGI client IP; reset counters so
    # this test observes limit=1 from a clean window (order-independent).
    redis = await get_redis()
    async for key in redis.scan_iter(match="rate:patient_payment_webhook:ip:*"):
        await redis.delete(key)
    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": "test-payment-unknown-id"},
    }
    r1 = await client.post("/api/v1/payments/webhook", json=payload)
    r2 = await client.post("/api/v1/payments/webhook", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 429
    body = r2.json()
    assert body.get("code") == "rate_limited"
