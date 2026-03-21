"""FamilyLink + loyalty subscription spend (LOY_FAMILY_013)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.family_link_service import FamilyLinkService
from src.application.services.loyalty_service import (
    FamilySpendDenied,
    LoyaltyService,
    PurchaseSubscriptionInput,
    UseSubscriptionForBookingInput,
)
from src.application.services.wallet_service import (
    EarnPointsInput,
    SpendPointsInput,
    WalletFamilySpendDenied,
    WalletService,
)
from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient
from src.domain.entities.subscription_package import SubscriptionPackage


@pytest.mark.asyncio
async def test_family_link_allows_beneficiary_spend(db_session: AsyncSession) -> None:
    clinic_id = uuid4()
    owner_id = uuid4()
    child_id = uuid4()
    booking_id = uuid4()
    db_session.add(Clinic(id=clinic_id, name="C", prepayment_amount=0))
    db_session.add(
        Patient(id=owner_id, clinic_id=clinic_id, phone="+1001", full_name="Owner")
    )
    db_session.add(
        Patient(id=child_id, clinic_id=clinic_id, phone="+1002", full_name="Child")
    )
    await db_session.flush()

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

    loyalty = LoyaltyService(db_session)
    fls = FamilyLinkService(db_session)
    now = datetime.now(timezone.utc)
    purchase = await loyalty.purchase_subscription(
        PurchaseSubscriptionInput(
            clinic_id=clinic_id,
            patient_id=owner_id,
            package_id=package.id,
            payment_id=uuid4(),
            purchased_at=now,
        )
    )
    await fls.create_family_link(
        clinic_id,
        primary_patient_id=owner_id,
        related_patient_id=child_id,
        relation_type="parent",
        can_spend_from_owner_loyalty=True,
        can_view_owner_history=True,
    )
    await db_session.flush()

    usage = await loyalty.use_subscription_for_booking(
        UseSubscriptionForBookingInput(
            clinic_id=clinic_id,
            booking_id=booking_id,
            subscription_id=purchase.id,
            used_visits=1,
            used_amount=None,
            used_at=now + timedelta(days=1),
            beneficiary_patient_id=child_id,
        )
    )
    assert usage.beneficiary_patient_id == child_id
    assert usage.family_link_id is not None

    timeline = await loyalty.get_subscription_usages_for_patient_timeline(
        clinic_id, child_id
    )
    assert len(timeline) == 1
    _u, meta = timeline[0]
    assert meta["timeline_view"] == "family_member_viewer"
    assert meta["subscription_owner_patient_id"] == str(owner_id)


@pytest.mark.asyncio
async def test_family_link_denies_without_link(db_session: AsyncSession) -> None:
    clinic_id = uuid4()
    owner_id = uuid4()
    child_id = uuid4()
    booking_id = uuid4()
    db_session.add(Clinic(id=clinic_id, name="C", prepayment_amount=0))
    db_session.add(
        Patient(id=owner_id, clinic_id=clinic_id, phone="+2001", full_name="Owner")
    )
    db_session.add(
        Patient(id=child_id, clinic_id=clinic_id, phone="+2002", full_name="Child")
    )
    await db_session.flush()

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

    loyalty = LoyaltyService(db_session)
    now = datetime.now(timezone.utc)
    purchase = await loyalty.purchase_subscription(
        PurchaseSubscriptionInput(
            clinic_id=clinic_id,
            patient_id=owner_id,
            package_id=package.id,
            payment_id=uuid4(),
            purchased_at=now,
        )
    )

    with pytest.raises(FamilySpendDenied):
        await loyalty.use_subscription_for_booking(
            UseSubscriptionForBookingInput(
                clinic_id=clinic_id,
                booking_id=booking_id,
                subscription_id=purchase.id,
                used_visits=1,
                used_amount=None,
                used_at=now + timedelta(days=1),
                beneficiary_patient_id=child_id,
            )
        )


@pytest.mark.asyncio
async def test_patient_can_use_subscription_respects_family_link(
    db_session: AsyncSession,
) -> None:
    clinic_id = uuid4()
    owner_id = uuid4()
    child_id = uuid4()
    db_session.add(Clinic(id=clinic_id, name="C", prepayment_amount=0))
    db_session.add(
        Patient(id=owner_id, clinic_id=clinic_id, phone="+3001", full_name="Owner")
    )
    db_session.add(
        Patient(id=child_id, clinic_id=clinic_id, phone="+3002", full_name="Child")
    )
    await db_session.flush()

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

    loyalty = LoyaltyService(db_session)
    fls = FamilyLinkService(db_session)
    now = datetime.now(timezone.utc)
    purchase = await loyalty.purchase_subscription(
        PurchaseSubscriptionInput(
            clinic_id=clinic_id,
            patient_id=owner_id,
            package_id=package.id,
            payment_id=uuid4(),
            purchased_at=now,
        )
    )
    await fls.create_family_link(
        clinic_id,
        primary_patient_id=owner_id,
        related_patient_id=child_id,
        relation_type="parent",
        can_spend_from_owner_loyalty=True,
        can_view_owner_history=False,
    )
    await db_session.flush()

    assert await loyalty.patient_can_use_subscription(
        clinic_id, purchase, child_id, now
    )
    assert not await loyalty.patient_can_use_subscription(
        clinic_id, purchase, uuid4(), now
    )


@pytest.mark.asyncio
async def test_wallet_spend_for_beneficiary_with_family_link(
    db_session: AsyncSession,
) -> None:
    clinic_id = uuid4()
    owner_id = uuid4()
    child_id = uuid4()
    db_session.add(Clinic(id=clinic_id, name="C", prepayment_amount=0))
    db_session.add(
        Patient(id=owner_id, clinic_id=clinic_id, phone="+4001", full_name="Owner")
    )
    db_session.add(
        Patient(id=child_id, clinic_id=clinic_id, phone="+4002", full_name="Child")
    )
    await db_session.flush()

    fls = FamilyLinkService(db_session)
    await fls.create_family_link(
        clinic_id,
        primary_patient_id=owner_id,
        related_patient_id=child_id,
        relation_type="parent",
        can_spend_from_owner_loyalty=True,
        can_view_owner_history=False,
    )
    await db_session.flush()

    ws = WalletService(db_session)
    now = datetime.now(timezone.utc)
    await ws.earn_points(
        EarnPointsInput(
            clinic_id=clinic_id,
            patient_id=owner_id,
            amount=Decimal("50.00"),
            happened_at=now,
        )
    )
    tx = await ws.spend_points(
        SpendPointsInput(
            clinic_id=clinic_id,
            patient_id=owner_id,
            amount=Decimal("10.00"),
            happened_at=now,
            beneficiary_patient_id=child_id,
        )
    )
    assert tx.family_link_id is not None
    assert tx.beneficiary_patient_id == child_id


@pytest.mark.asyncio
async def test_wallet_spend_beneficiary_denied_without_link(
    db_session: AsyncSession,
) -> None:
    clinic_id = uuid4()
    owner_id = uuid4()
    child_id = uuid4()
    db_session.add(Clinic(id=clinic_id, name="C", prepayment_amount=0))
    db_session.add(
        Patient(id=owner_id, clinic_id=clinic_id, phone="+5001", full_name="Owner")
    )
    db_session.add(
        Patient(id=child_id, clinic_id=clinic_id, phone="+5002", full_name="Child")
    )
    await db_session.flush()

    ws = WalletService(db_session)
    now = datetime.now(timezone.utc)
    await ws.earn_points(
        EarnPointsInput(
            clinic_id=clinic_id,
            patient_id=owner_id,
            amount=Decimal("20.00"),
            happened_at=now,
        )
    )
    with pytest.raises(WalletFamilySpendDenied):
        await ws.spend_points(
            SpendPointsInput(
                clinic_id=clinic_id,
                patient_id=owner_id,
                amount=Decimal("5.00"),
                happened_at=now,
                beneficiary_patient_id=child_id,
            )
        )
