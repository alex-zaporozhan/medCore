"""Smoke tests: auth send-code and verify-code."""

import random
import pytest
from httpx import AsyncClient

from src.infrastructure.database.redis_client import get_redis


@pytest.mark.asyncio
async def test_auth_send_code(client: AsyncClient, seed_data: dict, redis_client):
    """POST /api/v1/auth/send-code returns 204."""
    rate_keys = []
    async for key in redis_client.scan_iter(match="rate:auth_send_code:*"):
        rate_keys.append(key)
    async for key in redis_client.scan_iter(match="rate:auth:unknown_clinic_slug:*"):
        rate_keys.append(key)
    if rate_keys:
        await redis_client.delete(*rate_keys)

    response = None
    for _ in range(6):
        phone = "+7900" + "".join(random.choices("0123456789", k=7))
        response = await client.post(
            "/api/v1/auth/send-code",
            json={"phone": phone, "clinic_slug": seed_data["clinic_slug"]},
        )
        if response.status_code == 204:
            break
        if response.status_code == 429:
            continue
        break
    assert response is not None
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_auth_send_code_after_soft_delete_returns_204(
    client: AsyncClient, seed_data: dict, admin_auth: dict
):
    """Soft-deleted seed phone still occupies ux_patients_clinic_phone; send-code must reuse, not 500."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    deleted = await client.delete(f"/api/v1/patients/{seed_data['patient_id']}", headers=headers)
    assert deleted.status_code == 204, deleted.text
    sent = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": "+79001234567", "clinic_slug": seed_data["clinic_slug"]},
    )
    assert sent.status_code == 204, sent.text


@pytest.mark.asyncio
async def test_auth_verify_code(client: AsyncClient, seed_data: dict):
    """POST /api/v1/auth/verify-code returns 200 with access_token, token_type, patient_id."""
    clinic_id = seed_data["clinic_id"]
    phone = "+7900" + "".join(random.choices("0123456789", k=7))
    send = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": phone, "clinic_slug": seed_data["clinic_slug"]},
    )
    if send.status_code == 429:
        # test environment may contain leftover rate counters from previous runs
        rate_keys = []
        redis = await get_redis()
        async for key in redis.scan_iter(match="rate:auth_send_code:*"):
            rate_keys.append(key)
        if rate_keys:
            await redis.delete(*rate_keys)
        send = await client.post(
            "/api/v1/auth/send-code",
            json={"phone": phone, "clinic_slug": seed_data["clinic_slug"]},
        )
    assert send.status_code == 204, send.text

    redis = await get_redis()
    key = f"auth:code:{clinic_id}:{phone}"
    raw = await redis.get(key)
    assert raw, f"Auth code not in Redis for key {key}"
    code = raw.decode() if isinstance(raw, bytes) else raw

    response = await client.post(
        "/api/v1/auth/verify-code",
        json={"phone": phone, "code": code, "clinic_slug": seed_data["clinic_slug"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"
    assert "patient_id" in data
