"""Smoke tests: minimal set after deploy — health, auth send-code (mocked), admin GET, payments webhook."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_smoke_health(client: AsyncClient):
    """GET /health returns 200."""
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_smoke_auth_send_code(client: AsyncClient):
    """POST send-code returns 204 (SMS mocked in TESTING=1)."""
    r = await client.post("/api/v1/auth/send-code", json={"phone": "+79001234567"})
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_smoke_admin_bookings_with_auth(client: AsyncClient, admin_auth: dict):
    """GET admin/bookings with Bearer token returns 200."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/bookings", headers=headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_smoke_payments_webhook(client: AsyncClient):
    """POST payments/webhook (e.g. YooKassa) accepts request without 500."""
    r = await client.post(
        "/api/v1/payments/webhook",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": "smoke-test"}},
    )
    # May be 200, 400, 422 depending on validation; we only check no 5xx
    assert r.status_code < 500, r.text
