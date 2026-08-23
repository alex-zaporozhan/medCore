from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.erp_loyalty_dto import (
    CreateObligationFromSaleInput,
    RegisterWriteOffForVisitInput,
)
from src.application.services.erp_loyalty_service import (
    ErpLoyaltyError,
    ErpLoyaltyService,
)
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.erp_loyalty_obligation import ErpLoyaltyObligation
from src.domain.entities.subscription_package import SubscriptionPackage
from src.domain.entities.subscription_usage import SubscriptionUsage
from tests.booking_slot import unique_booking_slot


async def _create_subscription(
    db_session: AsyncSession,
    *,
    clinic_id,
    patient_id,
    now: datetime,
    kind: str = "balance",
    remaining_amount: Decimal | None = Decimal("1000.00"),
) -> CustomerSubscription:
    pkg = SubscriptionPackage(
        clinic_id=clinic_id,
        code=f"erp-loyalty-{uuid4().hex[:8]}",
        name="ERP Loyalty Test Package",
        description=None,
        kind=kind,
        services_included=[],
        total_visits=10 if kind == "visits" else None,
        total_amount=Decimal("2000.00") if kind == "balance" else None,
        price=Decimal("1000.00"),
        validity_days=30,
        is_active=True,
    )
    db_session.add(pkg)
    await db_session.flush()
    sub = CustomerSubscription(
        clinic_id=clinic_id,
        patient_id=patient_id,
        subscription_package_id=pkg.id,
        status="active",
        purchased_at=now,
        activated_at=now,
        expires_at=None,
        remaining_visits=10 if kind == "visits" else None,
        remaining_amount=remaining_amount,
        payment_id=None,
        notes=None,
    )
    db_session.add(sub)
    await db_session.flush()
    return sub


@pytest.mark.asyncio
async def test_create_obligation_from_sale_count_based(
    db_session: AsyncSession, seed_data
) -> None:
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    now = datetime.now(timezone.utc)
    sub = await _create_subscription(
        db_session, clinic_id=clinic_id, patient_id=patient_id, now=now, kind="visits"
    )

    service = ErpLoyaltyService(session=db_session)

    snapshot = await service.create_obligation_from_sale(
        CreateObligationFromSaleInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            customer_subscription_id=sub.id,
            package_price=Decimal("1000.00"),
            kind="COUNT_BASED",
            total_visits=10,
            total_amount=None,
            created_at=now,
        )
    )

    assert snapshot.clinic_id == clinic_id
    assert snapshot.patient_id == patient_id
    assert snapshot.customer_subscription_id == sub.id
    assert snapshot.initial_amount == Decimal("1000.00")
    assert snapshot.remaining_amount == Decimal("1000.00")
    assert snapshot.status == "active"

    obligation = await db_session.get(ErpLoyaltyObligation, snapshot.id)
    assert obligation is not None
    assert obligation.remaining_amount == Decimal("1000.00")


@pytest.mark.asyncio
async def test_create_obligation_from_sale_balance_based(
    db_session: AsyncSession, seed_data
) -> None:
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    now = datetime.now(timezone.utc)
    sub = await _create_subscription(
        db_session, clinic_id=clinic_id, patient_id=patient_id, now=now, kind="balance"
    )

    service = ErpLoyaltyService(session=db_session)

    snapshot = await service.create_obligation_from_sale(
        CreateObligationFromSaleInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            customer_subscription_id=sub.id,
            package_price=Decimal("1500.00"),
            kind="BALANCE_BASED",
            total_visits=None,
            total_amount=Decimal("2000.00"),
            created_at=now,
        )
    )

    assert snapshot.initial_amount == Decimal("2000.00")
    assert snapshot.remaining_amount == Decimal("2000.00")


@pytest.mark.asyncio
async def test_register_write_off_for_visit_full_and_partial(
    db_session: AsyncSession, seed_data
) -> None:
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    usage_id = uuid4()
    now = datetime.now(timezone.utc)
    booking_day, booking_time = unique_booking_slot(seed_data["date"], hour=11)
    booking = Booking(
        clinic_id=clinic_id,
        patient_id=patient_id,
        doctor_id=seed_data["doctor_id"],
        service_id=seed_data["service_id"],
        appointment_date=booking_day,
        appointment_time=booking_time,
        status=BookingStatus.CONFIRMED,
        prepayment_amount=Decimal("0.00"),
        payment_id=None,
        paid_by_subscription=False,
        notes="erp loyalty write-off test",
    )
    db_session.add(booking)
    await db_session.flush()

    # Prepare subscription and obligation
    sub = await _create_subscription(
        db_session,
        clinic_id=clinic_id,
        patient_id=patient_id,
        now=now,
        kind="balance",
        remaining_amount=Decimal("1000.00"),
    )

    service = ErpLoyaltyService(session=db_session)
    create_snapshot = await service.create_obligation_from_sale(
        CreateObligationFromSaleInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            customer_subscription_id=sub.id,
            package_price=Decimal("1000.00"),
            kind="BALANCE_BASED",
            total_visits=None,
            total_amount=Decimal("1000.00"),
            created_at=now,
        )
    )
    usage = SubscriptionUsage(
        id=usage_id,
        clinic_id=clinic_id,
        customer_subscription_id=sub.id,
        booking_id=booking.id,
        used_visits=None,
        used_amount=Decimal("0.00"),
        used_at=now,
        beneficiary_patient_id=None,
        family_link_id=None,
    )
    db_session.add(usage)
    await db_session.flush()

    # Partial write-off
    summary_partial = await service.register_write_off_for_visit(
        RegisterWriteOffForVisitInput(
            clinic_id=clinic_id,
            booking_id=booking.id,
            customer_subscription_id=sub.id,
            subscription_usage_id=usage_id,
            used_visits=None,
            used_amount=Decimal("400.00"),
            happened_at=now,
        )
    )
    assert summary_partial.total_write_off_amount == Decimal("400.00")

    obligation = await db_session.get(ErpLoyaltyObligation, create_snapshot.id)
    assert obligation is not None
    assert obligation.remaining_amount == Decimal("600.00")
    assert obligation.status == "active"

    # Full write-off to zero
    summary_full = await service.register_write_off_for_visit(
        RegisterWriteOffForVisitInput(
            clinic_id=clinic_id,
            booking_id=booking.id,
            customer_subscription_id=sub.id,
            subscription_usage_id=usage_id,
            used_visits=None,
            used_amount=Decimal("600.00"),
            happened_at=now,
        )
    )
    assert summary_full.total_write_off_amount == Decimal("600.00")

    await db_session.refresh(obligation)
    assert obligation.remaining_amount == Decimal("0")
    assert obligation.status == "settled"


@pytest.mark.asyncio
async def test_register_write_off_for_visit_overspend_clamped_with_warning(
    db_session: AsyncSession,
    seed_data,
) -> None:
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    usage_id = uuid4()
    now = datetime.now(timezone.utc)
    booking_day, booking_time = unique_booking_slot(seed_data["date"], hour=12)
    booking = Booking(
        clinic_id=clinic_id,
        patient_id=patient_id,
        doctor_id=seed_data["doctor_id"],
        service_id=seed_data["service_id"],
        appointment_date=booking_day,
        appointment_time=booking_time,
        status=BookingStatus.CONFIRMED,
        prepayment_amount=Decimal("0.00"),
        payment_id=None,
        paid_by_subscription=False,
        notes="erp loyalty overspend test",
    )
    db_session.add(booking)
    await db_session.flush()

    sub = await _create_subscription(
        db_session,
        clinic_id=clinic_id,
        patient_id=patient_id,
        now=now,
        kind="balance",
        remaining_amount=Decimal("500.00"),
    )

    service = ErpLoyaltyService(session=db_session)
    create_snapshot = await service.create_obligation_from_sale(
        CreateObligationFromSaleInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            customer_subscription_id=sub.id,
            package_price=Decimal("500.00"),
            kind="BALANCE_BASED",
            total_visits=None,
            total_amount=Decimal("500.00"),
            created_at=now,
        )
    )
    usage = SubscriptionUsage(
        id=usage_id,
        clinic_id=clinic_id,
        customer_subscription_id=sub.id,
        booking_id=booking.id,
        used_visits=None,
        used_amount=Decimal("0.00"),
        used_at=now,
        beneficiary_patient_id=None,
        family_link_id=None,
    )
    db_session.add(usage)
    await db_session.flush()

    summary = await service.register_write_off_for_visit(
        RegisterWriteOffForVisitInput(
            clinic_id=clinic_id,
            booking_id=booking.id,
            customer_subscription_id=sub.id,
            subscription_usage_id=usage_id,
            used_visits=None,
            used_amount=Decimal("800.00"),
            happened_at=now,
        )
    )

    assert summary.total_write_off_amount == Decimal("500.00")
    assert "attempt_write_off_more_than_remaining" in summary.warnings

    obligation = await db_session.get(ErpLoyaltyObligation, create_snapshot.id)
    assert obligation is not None
    assert obligation.remaining_amount == Decimal("0")
    assert obligation.status == "settled"


@pytest.mark.asyncio
async def test_create_obligation_from_sale_invalid_inputs(
    db_session: AsyncSession, seed_data
) -> None:
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    subscription_id = uuid4()
    now = datetime.now(timezone.utc)

    service = ErpLoyaltyService(session=db_session)

    with pytest.raises(ErpLoyaltyError):
        await service.create_obligation_from_sale(
            CreateObligationFromSaleInput(
                clinic_id=clinic_id,
                patient_id=patient_id,
                customer_subscription_id=subscription_id,
                package_price=Decimal("1000.00"),
                kind="COUNT_BASED",
                total_visits=0,
                total_amount=None,
                created_at=now,
            )
        )

    with pytest.raises(ErpLoyaltyError):
        await service.create_obligation_from_sale(
            CreateObligationFromSaleInput(
                clinic_id=clinic_id,
                patient_id=patient_id,
                customer_subscription_id=subscription_id,
                package_price=Decimal("1000.00"),
                kind="BALANCE_BASED",
                total_visits=None,
                total_amount=Decimal("0.00"),
                created_at=now,
            )
        )


