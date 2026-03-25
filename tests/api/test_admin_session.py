"""GET /v1/admin/auth/session — RBAC для UI (P1 лента)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_session_returns_permissions(client: AsyncClient, admin_auth: dict) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/auth/session", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "clinic_id" in data
    assert data["clinic_id"]
    assert isinstance(data["permissions"], list)
    assert isinstance(data["roles"], list)
    assert len(data["permissions"]) >= 0


@pytest.mark.asyncio
async def test_admin_session_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/admin/auth/session")
    assert r.status_code == 403
