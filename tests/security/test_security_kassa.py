"""Security tests: payment gateway (Kassa) — SEC-K1–K5.

No secrets in API responses; foreign clinic 404; credentials stored encrypted; webhook signature (skip).
"""

import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.clinic_payment_gateway_service import ClinicPaymentGatewayService
from src.domain.entities.clinic_payment_gateway import ClinicPaymentGateway
from src.infrastructure.database import base as db_base


# --- SEC-K1: Admin GET endpoints must not leak secret keys in response ---

# Substrings that must not appear as *values* in API responses (no decrypted secrets).
FORBIDDEN_VALUE_SUBSTRINGS = ("super-secret", "T1", "P1", "yookassa_secret_key")


@pytest.mark.security
@pytest.mark.asyncio
async def test_sec_k1_admin_get_endpoints_do_not_leak_secrets(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """SEC-K1: GET admin clinic/bookings responses must not contain secret keys or decrypted credentials."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    clinic_id = seed_data["clinic_id"]

    # GET admin clinic services
    r_services = await client.get(
        f"/api/v1/admin/clinics/{clinic_id}/services",
        headers=headers,
    )
    assert r_services.status_code == 200, r_services.text
    body_str = json.dumps(r_services.json())
    for forbidden in FORBIDDEN_VALUE_SUBSTRINGS:
        assert forbidden not in body_str, f"Response may leak secret-like: {forbidden}"

    # GET admin bookings
    r_bookings = await client.get("/api/v1/admin/bookings", headers=headers)
    assert r_bookings.status_code == 200, r_bookings.text
    bookings_str = json.dumps(r_bookings.json())
    for forbidden in FORBIDDEN_VALUE_SUBSTRINGS:
        assert forbidden not in bookings_str, f"Bookings response may leak: {forbidden}"


# --- SEC-K2: Admin cannot store credentials for another clinic ---

@pytest.mark.security
@pytest.mark.asyncio
async def test_sec_k2_admin_cannot_store_credentials_for_foreign_clinic(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
):
    """SEC-K2: POST credentials with admin token for clinic A and clinic_id=B must return 404 or 403."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    other_clinic_id = uuid.uuid4()

    r = await client.post(
        f"/api/v1/admin/clinics/{other_clinic_id}/payment-gateway/credentials",
        json={"gateway": "tinkoff", "payload": "{}"},
        headers=headers,
    )
    assert r.status_code in (403, 404), r.text


# --- SEC-K3: Credentials stored encrypted in DB ---

@pytest.mark.security
@pytest.mark.asyncio
async def test_sec_k3_credentials_stored_encrypted_in_db(init_db, seed_data):
    """SEC-K3: After upsert_credentials with known payload, DB must not contain plaintext."""
    raw_payload = '{"terminal_key":"T1","password":"P1"}'
    clinic_id = seed_data["clinic_id"]

    async with db_base.AsyncSessionLocal() as session:
        svc = ClinicPaymentGatewayService(session)
        await svc.upsert_credentials(
            clinic_id=clinic_id,
            gateway="tinkoff",
            raw_payload=raw_payload,
            actor_id=seed_data.get("admin_id"),
        )
        await session.commit()

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
        enc = row.credentials_encrypted
        assert "T1" not in enc
        assert "P1" not in enc
        assert "terminal_key" not in enc
        assert "password" not in enc


# --- SEC-K4: Webhook signature (not implemented) ---

@pytest.mark.security
@pytest.mark.skip(reason="Webhook signature not implemented yet")
@pytest.mark.asyncio
async def test_sec_k4_webhook_rejects_invalid_signature():
    """When webhook signature verification is implemented: invalid signature must return 401/400."""
    pass


# --- SEC-K5: No raw credentials in logs (review item; not implemented) ---
