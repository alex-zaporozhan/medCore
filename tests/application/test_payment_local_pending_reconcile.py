"""P1-4 / QA-AUDIT-002: stale ``local-pending:`` payment reconcile (patient + platform contours)."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import update

from src.application.services.payment_local_pending_reconcile_service import (
    reconcile_stale_patient_payment_local_pending,
    reconcile_stale_platform_payment_local_pending,
    run_payment_local_pending_reconcile_pass,
)
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.payment import Payment
from src.domain.entities.platform_signup_intent import PlatformSignupIntent
from src.domain.entities.platform_subscription_payment import PlatformSubscriptionPayment
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_reconcile_patient_returns_zero_when_yookassa_not_configured(init_db, seed_data) -> None:
    from src.application.services import payment_local_pending_reconcile_service as mod

    booking_id = uuid4()
    pay_id = uuid4()
    clinic_id = seed_data["clinic_id"]
    appt_time = time(17, 59, 0)

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
                id=pay_id,
                clinic_id=clinic_id,
                booking_id=booking_id,
                provider="yookassa",
                provider_payment_id="local-pending:deadbeef",
                amount=Decimal("500.00"),
                currency="RUB",
                status="pending",
            )
        )
        await session.commit()

    class _Unconfigured:
        def is_configured(self) -> bool:
            return False

    with patch.object(mod.settings, "payment_local_pending_reconcile_enabled", True):
        with patch.object(mod, "YooKassaClient", return_value=_Unconfigured()):
            async with db_base.AsyncSessionLocal() as session:
                async with session.begin():
                    n = await reconcile_stale_patient_payment_local_pending(session)
            assert n == 0


@pytest.mark.asyncio
async def test_reconcile_patient_stale_local_pending_invokes_create_payment(
    init_db, seed_data, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.application.services import payment_local_pending_reconcile_service as mod

    monkeypatch.setattr(mod.settings, "payment_local_pending_reconcile_enabled", True)

    booking_id = uuid4()
    pay_id = uuid4()
    clinic_id = seed_data["clinic_id"]
    appt_time = time(16, 59, 0)

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
                id=pay_id,
                clinic_id=clinic_id,
                booking_id=booking_id,
                provider="yookassa",
                provider_payment_id="local-pending:stale-row",
                amount=Decimal("500.00"),
                currency="RUB",
                status="pending",
            )
        )
        await session.flush()
        b = await session.get(Booking, booking_id)
        assert b is not None
        b.payment_id = pay_id
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        await session.execute(
            update(Payment)
            .where(Payment.id == pay_id)
            .values(created_at=datetime.now(UTC) - timedelta(minutes=15))
        )
        await session.commit()

    mock_create = AsyncMock()
    with patch.object(mod, "YooKassaClient") as yk_cls:
        yk_cls.return_value.is_configured.return_value = True
        with patch.object(mod, "PaymentService") as ps_cls:
            ps_cls.return_value.create_payment = mock_create
            async with db_base.AsyncSessionLocal() as session:
                async with session.begin():
                    n = await reconcile_stale_patient_payment_local_pending(session)

    assert n == 1
    mock_create.assert_awaited_once()
    assert mock_create.await_args is not None
    assert mock_create.await_args.args[0] == booking_id


@pytest.mark.asyncio
async def test_reconcile_platform_stale_local_pending_updates_provider_id(
    init_db, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.application.services import payment_local_pending_reconcile_service as mod

    monkeypatch.setattr(mod.settings, "payment_local_pending_reconcile_enabled", True)

    intent_id = uuid4()
    pay_row_id = uuid4()

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            PlatformSignupIntent(
                id=intent_id,
                status="pending_payment",
                email="reconcile-plat@example.com",
                tariff_snapshot={"plan_slug": "start", "billing_period": "monthly"},
            )
        )
        session.add(
            PlatformSubscriptionPayment(
                id=pay_row_id,
                signup_intent_id=intent_id,
                provider="yookassa",
                provider_payment_id="local-pending:plat-stale",
                amount=Decimal("1000.00"),
                currency="RUB",
                status="pending",
            )
        )
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        await session.execute(
            update(PlatformSubscriptionPayment)
            .where(PlatformSubscriptionPayment.id == pay_row_id)
            .values(created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=20))
        )
        await session.commit()

    def _fake_create_platform_payment(*_a, **_k):
        return ("yk-real-payment-id", "https://pay.example/confirm")

    with patch.object(mod, "YooKassaClient") as yk_cls:
        inst = yk_cls.return_value
        inst.is_configured.return_value = True
        inst.create_platform_subscription_payment = _fake_create_platform_payment
        with patch.object(mod, "_checkout_return_url", return_value="https://app.example/after-pay"):
            async with db_base.AsyncSessionLocal() as session:
                async with session.begin():
                    n = await reconcile_stale_platform_payment_local_pending(session)

    assert n == 1
    async with db_base.AsyncSessionLocal() as session:
        row = await session.get(PlatformSubscriptionPayment, pay_row_id)
        assert row is not None
        assert row.provider_payment_id == "yk-real-payment-id"


@pytest.mark.asyncio
async def test_run_payment_local_pending_reconcile_pass_runs_both_contours(init_db, monkeypatch) -> None:
    from src.application.services import payment_local_pending_reconcile_service as mod

    monkeypatch.setattr(mod.settings, "payment_local_pending_reconcile_enabled", True)

    with (
        patch.object(
            mod,
            "reconcile_stale_patient_payment_local_pending",
            new=AsyncMock(return_value=1),
        ),
        patch.object(
            mod,
            "reconcile_stale_platform_payment_local_pending",
            new=AsyncMock(return_value=2),
        ),
    ):
        p, b = await run_payment_local_pending_reconcile_pass()

    assert (p, b) == (1, 2)


def test_celery_reconcile_local_pending_task_returns_counts(monkeypatch) -> None:
    from src.infrastructure.messaging.tasks import payment_reconciliation_tasks as tasks

    monkeypatch.setattr(
        tasks,
        "run_payment_local_pending_reconcile_pass",
        AsyncMock(return_value=(3, 0)),
    )
    out = tasks.reconcile_local_pending_payments()
    assert out == {"patient_rows_touched": 3, "platform_rows_touched": 0}
