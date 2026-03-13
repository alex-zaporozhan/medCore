"""Smoke tests: auth send-code and verify-code."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_send_code(client: AsyncClient):
    """POST /api/v1/auth/send-code returns 204."""
    response = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": "+79001234567"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_auth_verify_code(client: AsyncClient, seed_data: dict, redis_client):
    """POST /api/v1/auth/verify-code returns 200 with access_token, token_type, patient_id."""
    clinic_id = seed_data["clinic_id"]
    phone = "+79001234567"
    code = "123456"
    key = f"auth:code:{clinic_id}:{phone}"
    await redis_client.setex(key, 300, code)

    response = await client.post(
        "/api/v1/auth/verify-code",
        json={"phone": phone, "code": code},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"
    assert "patient_id" in data
