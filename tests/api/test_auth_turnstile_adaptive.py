"""Adaptive Turnstile captcha tests (backend-only)."""

import uuid

import pytest
import redis as sync_redis
from httpx import AsyncClient

from src.core.config import settings


@pytest.fixture(autouse=True)
def _reset_auth_send_code_captcha_soft_buckets() -> None:
    """Full suite shares test client IP; Redis keys survive across tests."""
    r = sync_redis.Redis.from_url(settings.redis_url)
    try:
        for k in r.scan_iter("rate:auth_send_code:captcha_soft:ip:*"):
            r.delete(k)
    finally:
        r.close()
    yield


def _unique_phone() -> str:
    """Avoid cross-test Redis rate keys (full suite shares test client IP)."""
    return f"+7900{uuid.uuid4().int % 10_000_000:07d}"


@pytest.mark.asyncio
async def test_auth_send_code_requires_captcha_after_soft_limit(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "turnstile_enabled", True, raising=False)
    monkeypatch.setattr(settings, "turnstile_site_key", "site-key", raising=False)
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret", raising=False)
    monkeypatch.setattr(settings, "rate_auth_send_code_ip_limit", 0, raising=False)
    monkeypatch.setattr(settings, "rate_auth_send_code_phone_limit", 0, raising=False)
    monkeypatch.setattr(settings, "rate_auth_send_code_captcha_soft_ip_limit", 1, raising=False)
    monkeypatch.setattr(settings, "rate_auth_captcha_soft_window_seconds", 600, raising=False)

    phone = _unique_phone()
    r1 = await client.post("/api/v1/auth/send-code", json={"phone": phone})
    assert r1.status_code == 204, r1.text

    r2 = await client.post("/api/v1/auth/send-code", json={"phone": phone})
    assert r2.status_code == 403, r2.text
    data = r2.json()
    assert data["code"] == "captcha_required"
    assert data["details"]["site_key"] == "site-key"


@pytest.mark.asyncio
async def test_auth_send_code_allows_with_valid_captcha_after_soft_limit(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "turnstile_enabled", True, raising=False)
    monkeypatch.setattr(settings, "turnstile_site_key", "site-key", raising=False)
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret", raising=False)
    monkeypatch.setattr(settings, "rate_auth_send_code_ip_limit", 0, raising=False)
    monkeypatch.setattr(settings, "rate_auth_send_code_phone_limit", 0, raising=False)
    monkeypatch.setattr(settings, "rate_auth_send_code_captcha_soft_ip_limit", 1, raising=False)
    monkeypatch.setattr(settings, "rate_auth_captcha_soft_window_seconds", 600, raising=False)

    async def _ok(*args, **kwargs):  # noqa: ANN001,ANN002,ANN003
        class R:
            ok = True

        return R()

    monkeypatch.setattr("src.api.v1.routers.auth.verify_turnstile", _ok)

    phone = _unique_phone()
    r1 = await client.post("/api/v1/auth/send-code", json={"phone": phone})
    assert r1.status_code == 204, r1.text
    r2 = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": phone, "turnstile_token": "dummy"},
    )
    assert r2.status_code == 204, r2.text

