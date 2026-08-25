"""Admin staff login errors: stable code + English canonical detail (UI localizes)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_login_wrong_password_returns_invalid_credentials_code(
    client: AsyncClient, seed_data: dict
) -> None:
    r = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": seed_data["admin_email"], "password": "wrong-password"},
    )
    assert r.status_code == 401, r.text
    body = r.json()
    assert body.get("code") == "invalid_credentials"
    assert "неверный" not in str(body.get("detail", "")).lower()
    assert "invalid email or password" in str(body.get("detail", "")).lower()
