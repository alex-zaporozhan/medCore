"""API tests for admin loyalty endpoints (policy and subscription usages)."""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.loyalty_service import (
    LoyaltyService,
    PurchaseSubscriptionInput,
    UseSubscriptionForBookingInput,
)
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.payment import Payment
from src.domain.entities.subscription_package import SubscriptionPackage


@pytest.mark.asyncio
async def test_get_loyalty_policy_smoke(client: AsyncClient, admin_auth: dict) -> None:
    """GET /admin/loyalty/policy returns default structure for clinic without policy."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    response = await client.get("/api/v1/admin/loyalty/policy", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "clinic_id" in data
    assert "cashback_percent" in data
    assert "allow_pay_with_points" in data


@pytest.mark.asyncio
async def test_subscription_usages_list_by_patient(
    client: AsyncClient,
    admin_auth: dict,
    db_session: AsyncSession,
    seed_data: dict,
) -> None:
    """GET /admin/loyalty/subscription-usages returns usages for given patient."""
    clinic_id = UUID(admin_auth["clinic_id"])
    patient_id = UUID(str(seed_data["patient_id"]))
    booking_id = uuid4()
    payment_id = uuid4()

    loyalty_service = LoyaltyService(db_session)

    booking = Booking(
        id=booking_id,
        clinic_id=clinic_id,
        patient_id=patient_id,
        doctor_id=UUID(str(seed_data["doctor_id"])),
        service_id=UUID(str(seed_data["service_id"])),
        appointment_date=datetime.now(timezone.utc).date(),
        appointment_time=datetime.now(timezone.utc).time().replace(second=0, microsecond=0),
        status=BookingStatus.PENDING,
        prepayment_amount=Decimal("0.00"),
        payment_id=None,
        paid_by_subscription=False,
        notes=None,
        erp_processed=False,
        erp_error_code=None,
    )
    db_session.add(booking)
    payment = Payment(
        id=payment_id,
        clinic_id=clinic_id,
        booking_id=booking_id,
        provider="test",
        provider_payment_id=f"test-{payment_id}",
        amount=Decimal("1000.00"),
        currency="RUB",
        status="succeeded",
        provider_metadata=None,
    )
    db_session.add(payment)

    package = SubscriptionPackage(
        clinic_id=clinic_id,
        code="TEST_USAGE",
        name="Test usage package",
        description=None,
        kind="visits",
        services_included=[],
        total_visits=5,
        total_amount=None,
        price=Decimal("1000.00"),
        validity_days=30,
        is_active=True,
    )
    db_session.add(package)
    await db_session.flush()
    await db_session.refresh(package)

    now = datetime.now(timezone.utc)
    subscription = await loyalty_service.purchase_subscription(
        PurchaseSubscriptionInput(
            clinic_id=clinic_id,
            patient_id=patient_id,
            package_id=package.id,
            payment_id=payment_id,
            purchased_at=now,
        )
    )

    await loyalty_service.use_subscription_for_booking(
        UseSubscriptionForBookingInput(
            clinic_id=clinic_id,
            booking_id=booking_id,
            subscription_id=subscription.id,
            used_visits=2,
            used_amount=None,
            used_at=now + timedelta(days=1),
        )
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    response = await client.get(
        "/api/v1/admin/loyalty/subscription-usages",
        headers=headers,
        params={"patient_id": str(patient_id)},
    )
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    # In seed-independent environment there may be more data, so we only assert at least one usage.
    assert any(item["customer_subscription_id"] == str(subscription.id) for item in items)

