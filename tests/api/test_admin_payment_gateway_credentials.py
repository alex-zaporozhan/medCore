"""Tests for admin payment gateway credentials endpoint."""

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.domain.entities.clinic_payment_gateway import ClinicPaymentGateway
from src.infrastructure.database import base as db_base


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_admin_can_store_gateway_credentials_for_clinic(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """Admin can store encrypted payment gateway credentials for own clinic (204, row created)."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = admin_auth["clinic_id"]

    payload = {
        "gateway": "tinkoff",
        "payload": json.dumps(
            {
                "terminal_key": "demo-terminal",
                "password": "super-secret",
            }
        ),
    }

    r = await client.post(
        f"/api/v1/admin/clinics/{clinic_id}/payment-gateway/credentials",
        json=payload,
        headers=headers,
    )
    assert r.status_code == 204, r.text

    async with db_base.AsyncSessionLocal() as session:
        result = await session.execute(
            select(ClinicPaymentGateway).where(
                ClinicPaymentGateway.clinic_id == clinic_id,
                ClinicPaymentGateway.gateway == "tinkoff",
            )
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.credentials_encrypted is not None
        assert "super-secret" not in (row.credentials_encrypted or "")
        assert row.status == "PENDING"


@pytest.mark.regression_payments
@pytest.mark.security
@pytest.mark.asyncio
async def test_admin_cannot_store_credentials_for_foreign_clinic(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """Admin gets 404 when trying to save credentials for another clinic."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    # Use a UUID that definitely does not belong to current admin clinic.
    import uuid

    other_clinic_id = uuid.uuid4()

    r = await client.post(
        f"/api/v1/admin/clinics/{other_clinic_id}/payment-gateway/credentials",
        json={"gateway": "tinkoff", "payload": "{}"},
        headers=headers,
    )
    assert r.status_code == 404

