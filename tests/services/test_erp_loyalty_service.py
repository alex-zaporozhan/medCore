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
from src.domain.entities.customer_subscription import CustomerSubscription
from src.domain.entities.erp_loyalty_obligation import ErpLoyaltyObligation


@pytest.mark.asyncio
async def test_create_obligation_from_sale_count_based(db_session: AsyncSession) -> None:
    clinic_id = uuid4()
    patient_id = uuid4()
    subscription_id = uuid4()
    now = datetime.now(timezone.utc)

    service = ErpLoyaltyService(session=db_session)

    snapshot = await service.create_obligation_from_sale(
        CreateObligationFromSaleInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            customer_subscription_id=subscription_id,
            package_price=Decimal("1000.00"),
            kind="COUNT_BASED",
            total_visits=10,
            total_amount=None,
            created_at=now,
        )
    )

    assert snapshot.clinic_id == clinic_id
    assert snapshot.patient_id == patient_id
    assert snapshot.customer_subscription_id == subscription_id
    assert snapshot.initial_amount == Decimal("1000.00")
    assert snapshot.remaining_amount == Decimal("1000.00")
    assert snapshot.status == "active"

    obligation = await db_session.get(ErpLoyaltyObligation, snapshot.id)
    assert obligation is not None
    assert obligation.remaining_amount == Decimal("1000.00")


@pytest.mark.asyncio
async def test_create_obligation_from_sale_balance_based(db_session: AsyncSession) -> None:
    clinic_id = uuid4()
    patient_id = uuid4()
    subscription_id = uuid4()
    now = datetime.now(timezone.utc)

    service = ErpLoyaltyService(session=db_session)

    snapshot = await service.create_obligation_from_sale(
        CreateObligationFromSaleInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            customer_subscription_id=subscription_id,
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
async def test_register_write_off_for_visit_full_and_partial(db_session: AsyncSession) -> None:
    clinic_id = uuid4()
    patient_id = uuid4()
    subscription_id = uuid4()
    booking_id = uuid4()
    usage_id = uuid4()
    now = datetime.now(timezone.utc)

    # Prepare subscription and obligation
    sub = CustomerSubscription(
        clinic_id=clinic_id,
        patient_id=patient_id,
        subscription_package_id=uuid4(),
        status="active",
        purchased_at=now,
        activated_at=now,
        expires_at=None,
        remaining_visits=None,
        remaining_amount=Decimal("1000.00"),
        payment_id=None,
        notes=None,
    )
    db_session.add(sub)
    await db_session.flush()

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

    # Partial write-off
    summary_partial = await service.register_write_off_for_visit(
        RegisterWriteOffForVisitInput(
            clinic_id=clinic_id,
            booking_id=booking_id,
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
            booking_id=booking_id,
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
) -> None:
    clinic_id = uuid4()
    patient_id = uuid4()
    subscription_id = uuid4()
    booking_id = uuid4()
    usage_id = uuid4()
    now = datetime.now(timezone.utc)

    sub = CustomerSubscription(
        clinic_id=clinic_id,
        patient_id=patient_id,
        subscription_package_id=uuid4(),
        status="active",
        purchased_at=now,
        activated_at=now,
        expires_at=None,
        remaining_visits=None,
        remaining_amount=Decimal("500.00"),
        payment_id=None,
        notes=None,
    )
    db_session.add(sub)
    await db_session.flush()

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

    summary = await service.register_write_off_for_visit(
        RegisterWriteOffForVisitInput(
            clinic_id=clinic_id,
            booking_id=booking_id,
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
async def test_create_obligation_from_sale_invalid_inputs(db_session: AsyncSession) -> None:
    clinic_id = uuid4()
    patient_id = uuid4()
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


