"""GET /v1/admin/auth/session — RBAC для UI (P1 лента)."""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from src.core.config import settings
from src.core.security import create_access_token


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
    assert data.get("entitlement_enforced") is False
    assert data.get("entitlement_keys") == []
    assert data.get("industry_profile") == "industry_dental"


@pytest.mark.asyncio
async def test_admin_session_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/admin/auth/session")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_session_rejects_jwt_wrong_audience_when_strict(
    client: AsyncClient, seed_data: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """1a-E6 / QA_ARCH: admin token with patient audience must not pass admin verify."""
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    token = create_access_token(
        {"type": "admin", "sub": str(seed_data["admin_id"])},
        expires_delta=timedelta(minutes=5),
        audience=settings.jwt_audience_patient,
    )
    r = await client.get(
        "/api/v1/admin/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    assert r.json().get("code") == "invalid_token_audience"
