"""Production defaults for platform signup safety knobs (LEAD A2/A1)."""

import pytest

from src.core.config import Settings


def _minimal_settings(**kwargs: object) -> Settings:
    base: dict[str, object] = {
        "secret_key": "x" * 32,
        "jwt_secret_key": "y" * 32,
        "database_url": "postgresql+asyncpg://u:p@127.0.0.1:5432/db",
    }
    base.update(kwargs)
    return Settings(**base)


@pytest.mark.critical_path
def test_production_derives_return_url_allowlist_and_owner_invite_base(monkeypatch) -> None:
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("PLATFORM_CHECKOUT_RETURN_URL_ALLOWLIST", raising=False)
    monkeypatch.delenv("PLATFORM_OWNER_INVITE_PUBLIC_BASE_URL", raising=False)
    s = _minimal_settings(
        app_env="production",
        platform_saas_checkout_return_url="https://app.example.com/booking/success",
        yookassa_return_url="https://fallback.example.net/app/booking/success",
    )
    assert "app.example.com" in s.platform_checkout_return_url_allowlist
    assert "fallback.example.net" in s.platform_checkout_return_url_allowlist
    assert s.platform_owner_invite_public_base_url == "https://app.example.com"

