"""API tests for admin loyalty summary-by-contact endpoint."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.loyalty_service import (
    LoyaltyService,
    PurchaseSubscriptionInput,
)
from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.domain.entities.subscription_package import SubscriptionPackage


@pytest.mark.asyncio
async def test_admin_loyalty_summary_by_contact_returns_patient_loyalty(
    client: AsyncClient,
    admin_auth: dict,
    db_session: AsyncSession,
    seed_data,
) -> None:
    """GET /admin/loyalty/summary-by-contact returns mapped patient loyalty by contact phone."""
    clinic_id = seed_data["clinic_id"]

    # Create patient via seed_data helper: there is at least one patient with phone in seed.
    from src.domain.entities.patient import Patient

    patient = Patient(
        clinic_id=clinic_id,
        phone="+79990001122",
        full_name="Loyalty Contact Test",
        email=None,
    )
    db_session.add(patient)
    await db_session.flush()
    await db_session.refresh(patient)

    # Create subscription package and purchased subscription for this patient
    loyalty_service = LoyaltyService(db_session)
    package = SubscriptionPackage(
        clinic_id=clinic_id,
        code="OMNI_SUMMARY",
        name="Omni Summary Package",
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
    await loyalty_service.purchase_subscription(
        PurchaseSubscriptionInput(
            clinic_id=clinic_id,
            patient_id=patient.id,
            package_id=package.id,
            payment_id=None,
            purchased_at=now,
        )
    )
    await db_session.commit()

    # Create omnichannel contact with same phone
    async with db_session.bind.connect() as _:
        omni_service = OmnichannelChatService(db_session)
        contact = await omni_service.create_contact(
            business_account_id=clinic_id,
            full_name="Loyalty Contact Test",
            primary_phone=patient.phone,
        )
        await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    response = await client.get(
        "/api/v1/admin/loyalty/summary-by-contact",
        params={"contact_id": str(contact.id)},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["patient_id"] == str(patient.id)
    assert data["patient_full_name"] == patient.full_name
    assert data["patient_phone"] == patient.phone
    assert isinstance(data["subscriptions"], list)
    assert len(data["subscriptions"]) >= 1

