"""P1-4: local payment row before YooKassa create (contour A)."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from tests.booking_slot import unique_booking_slot

from src.application.services.payment_service import (
    PaymentService,
    _LOCAL_PENDING_PROVIDER_PAYMENT_PREFIX,
)
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.clinic import Clinic
from src.domain.entities.payment import Payment
from src.infrastructure.database import base as db_base
from src.infrastructure.external_apis.yookassa_client import YooKassaClientError


@pytest.mark.asyncio
async def test_create_payment_yookassa_fail_leaves_local_pending_row(
    seed_data: dict, monkeypatch: pytest.MonkeyPatch
):
    clinic_id = seed_data["clinic_id"]
    booking_id = uuid4()
    slot_day, slot_time = unique_booking_slot(seed_data["date"], hour=6)

    class _FailingYk:
        def create_payment(self, amount, return_url, description, booking_id):  # noqa: ARG002
            raise YooKassaClientError("simulated provider failure")

    async with db_base.AsyncSessionLocal() as session:
        clinic = await session.get(Clinic, clinic_id)
        assert clinic is not None
        clinic.prepayment_enabled = True
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=seed_data["patient_id"],
                doctor_id=seed_data["doctor_id"],
                service_id=seed_data["service_id"],
                appointment_date=slot_day,
                appointment_time=slot_time,
                status=BookingStatus.AWAITING_PAYMENT,
                prepayment_amount=500,
            )
        )
        await session.commit()

    from src.application.services import payment_service as ps_mod

    async with db_base.AsyncSessionLocal() as session:
        svc = PaymentService(session)
        monkeypatch.setattr(ps_mod, "_yookassa_client_for_clinic", lambda _clinic: _FailingYk())
        with pytest.raises(ValueError, match="simulated"):
            await svc.create_payment(booking_id)
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        rows = list(
            (
                await session.execute(select(Payment).where(Payment.booking_id == booking_id))
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].provider_payment_id.startswith(_LOCAL_PENDING_PROVIDER_PAYMENT_PREFIX)
        assert rows[0].status == "pending"


@pytest.mark.asyncio
async def test_create_payment_idempotent_second_call_uses_get_payment_only(
    seed_data: dict, monkeypatch: pytest.MonkeyPatch
):
    clinic_id = seed_data["clinic_id"]
    booking_id = uuid4()
    slot_day, slot_time = unique_booking_slot(seed_data["date"], hour=7)
    counters = {"create": 0, "get": 0}
    ext_id = f"yookassa-ext-{uuid4().hex[:12]}"

    class _CountingYk:
        def create_payment(self, amount, return_url, description, booking_id):  # noqa: ARG002
            counters["create"] += 1
            return ext_id, "https://pay.example/confirm"

        def get_payment(self, provider_payment_id: str) -> dict:
            counters["get"] += 1
            assert provider_payment_id == ext_id
            return {
                "id": ext_id,
                "confirmation": {"type": "redirect", "confirmation_url": "https://pay.example/replay"},
            }

    async with db_base.AsyncSessionLocal() as session:
        clinic = await session.get(Clinic, clinic_id)
        assert clinic is not None
        clinic.prepayment_enabled = True
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=seed_data["patient_id"],
                doctor_id=seed_data["doctor_id"],
                service_id=seed_data["service_id"],
                appointment_date=slot_day,
                appointment_time=slot_time,
                status=BookingStatus.AWAITING_PAYMENT,
                prepayment_amount=500,
            )
        )
        await session.commit()

    from src.application.services import payment_service as ps_mod

    monkeypatch.setattr(ps_mod, "_yookassa_client_for_clinic", lambda _clinic: _CountingYk())
    async with db_base.AsyncSessionLocal() as session:
        svc = PaymentService(session)
        r1 = await svc.create_payment(booking_id)
        await session.commit()
    assert counters["create"] == 1
    assert r1.provider_payment_id == ext_id

    async with db_base.AsyncSessionLocal() as session:
        svc = PaymentService(session)
        r2 = await svc.create_payment(booking_id)
        await session.commit()
    assert counters["create"] == 1
    assert counters["get"] == 1
    assert r2.payment_url == "https://pay.example/replay"
    assert r2.provider_payment_id == ext_id

    async with db_base.AsyncSessionLocal() as session:
        n = await session.scalar(select(func.count()).where(Payment.booking_id == booking_id))
        assert n == 1
