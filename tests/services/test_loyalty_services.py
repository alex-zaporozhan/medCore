"""Tests for loyalty subscription and wallet services."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.loyalty_service import (
    InsufficientSubscriptionBalance,
    LoyaltyService,
    PurchaseSubscriptionInput,
    UseSubscriptionForBookingInput,
)
from src.application.services.wallet_service import (
    InsufficientWalletBalance,
    WalletService,
    EarnPointsInput,
    SpendPointsInput,
)
from src.domain.entities.subscription_package import SubscriptionPackage


@pytest.mark.asyncio
async def test_loyalty_purchase_and_use_visits(db_session: AsyncSession) -> None:
    clinic_id = uuid4()
    patient_id = uuid4()
    booking_id = uuid4()
    payment_id = uuid4()

    service = LoyaltyService(db_session)

    package = SubscriptionPackage(
        clinic_id=clinic_id,
        code="TEST10",
        name="10 visits",
        description=None,
        kind="visits",
        services_included=[],
        total_visits=10,
        total_amount=None,
        price=Decimal("1000.00"),
        validity_days=30,
        is_active=True,
    )
    db_session.add(package)
    await db_session.flush()
    await db_session.refresh(package)

    now = datetime.now(timezone.utc)
    purchase = await service.purchase_subscription(
        PurchaseSubscriptionInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            package_id=package.id,
            payment_id=payment_id,
            purchased_at=now,
        )
    )
    assert purchase.status == "active"
    assert purchase.remaining_visits == 10
    assert purchase.expires_at is not None

    usage = await service.use_subscription_for_booking(
        UseSubscriptionForBookingInput(
            clinic_id=clinic_id,
            booking_id=booking_id,
            subscription_id=purchase.id,
            used_visits=3,
            used_amount=None,
            used_at=now + timedelta(days=1),
        )
    )
    assert usage.used_visits == 3

    refreshed = await service.customer_repo.get_by_id(purchase.id)
    assert refreshed is not None
    assert refreshed.remaining_visits == 7
    assert refreshed.status == "active"

    with pytest.raises(InsufficientSubscriptionBalance):
        await service.use_subscription_for_booking(
            UseSubscriptionForBookingInput(
                clinic_id=clinic_id,
                booking_id=booking_id,
                subscription_id=purchase.id,
                used_visits=100,
                used_amount=None,
                used_at=now + timedelta(days=2),
            )
        )


@pytest.mark.asyncio
async def test_loyalty_purchase_subscription_idempotent_by_payment_id(
    db_session: AsyncSession,
) -> None:
    clinic_id = uuid4()
    patient_id = uuid4()
    payment_id = uuid4()

    service = LoyaltyService(db_session)

    package = SubscriptionPackage(
        clinic_id=clinic_id,
        code="IDEMPOTENT",
        name="Idempotent package",
        description=None,
        kind="visits",
        services_included=[],
        total_visits=1,
        total_amount=None,
        price=Decimal("100.00"),
        validity_days=10,
        is_active=True,
    )
    db_session.add(package)
    await db_session.flush()
    await db_session.refresh(package)

    now = datetime.now(timezone.utc)
    first = await service.purchase_subscription(
        PurchaseSubscriptionInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            package_id=package.id,
            payment_id=payment_id,
            purchased_at=now,
        )
    )
    second = await service.purchase_subscription(
        PurchaseSubscriptionInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            package_id=package.id,
            payment_id=payment_id,
            purchased_at=now,
        )
    )

    assert first.id == second.id


@pytest.mark.asyncio
async def test_wallet_earn_and_spend(db_session: AsyncSession) -> None:
    clinic_id = uuid4()
    patient_id = uuid4()
    now = datetime.now(timezone.utc)

    wallet_service = WalletService(db_session)

    earn_tx = await wallet_service.earn_points(
        EarnPointsInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            amount=Decimal("100.00"),
            happened_at=now,
            booking_id=None,
            subscription_id=None,
            description="test earn",
        )
    )
    assert earn_tx.amount == Decimal("100.00")

    wallet = await wallet_service.get_or_create_wallet(
        clinic_id=clinic_id,
        patient_id=patient_id,
    )
    assert wallet.balance == Decimal("100.00")

    spend_tx = await wallet_service.spend_points(
        SpendPointsInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            amount=Decimal("40.00"),
            happened_at=now + timedelta(minutes=5),
            booking_id=None,
            description="test spend",
        )
    )
    assert spend_tx.amount == Decimal("40.00")

    wallet_after = await wallet_service.get_or_create_wallet(
        clinic_id=clinic_id,
        patient_id=patient_id,
    )
    assert wallet_after.balance == Decimal("60.00")

    with pytest.raises(InsufficientWalletBalance):
        await wallet_service.spend_points(
            SpendPointsInput(
                clinic_id=clinic_id,
                patient_id=patient_id,
                amount=Decimal("1000.00"),
                happened_at=now + timedelta(minutes=10),
                booking_id=None,
                description="overspend",
            )
        )

