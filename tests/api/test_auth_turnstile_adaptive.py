"""Adaptive Turnstile captcha tests (backend-only)."""

import pytest
from httpx import AsyncClient

from src.core.config import settings


@pytest.mark.asyncio
async def test_auth_send_code_requires_captcha_after_soft_limit(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "turnstile_enabled", True, raising=False)
    monkeypatch.setattr(settings, "turnstile_site_key", "site-key", raising=False)
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret", raising=False)
    monkeypatch.setattr(settings, "rate_auth_send_code_captcha_soft_ip_limit", 1, raising=False)
    monkeypatch.setattr(settings, "rate_auth_captcha_soft_window_seconds", 600, raising=False)

    r1 = await client.post("/api/v1/auth/send-code", json={"phone": "+79001234567"})
    assert r1.status_code == 204, r1.text

    r2 = await client.post("/api/v1/auth/send-code", json={"phone": "+79001234567"})
    assert r2.status_code == 403, r2.text
    data = r2.json()
    assert data["code"] == "captcha_required"
    assert data["details"]["site_key"] == "site-key"


@pytest.mark.asyncio
async def test_auth_send_code_allows_with_valid_captcha_after_soft_limit(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "turnstile_enabled", True, raising=False)
    monkeypatch.setattr(settings, "turnstile_site_key", "site-key", raising=False)
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret", raising=False)
    monkeypatch.setattr(settings, "rate_auth_send_code_captcha_soft_ip_limit", 1, raising=False)
    monkeypatch.setattr(settings, "rate_auth_captcha_soft_window_seconds", 600, raising=False)

    async def _ok(*args, **kwargs):  # noqa: ANN001,ANN002,ANN003
        class R:
            ok = True

        return R()

    monkeypatch.setattr("src.api.v1.routers.auth.verify_turnstile", _ok)

    r1 = await client.post("/api/v1/auth/send-code", json={"phone": "+79001234567"})
    assert r1.status_code == 204, r1.text
    r2 = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": "+79001234567", "turnstile_token": "dummy"},
    )
    assert r2.status_code == 204, r2.text

