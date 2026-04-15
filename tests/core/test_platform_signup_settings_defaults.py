"""Production defaults for auth/outbox safety knobs."""

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
def test_production_applies_patient_auth_and_outbox_defaults(monkeypatch) -> None:
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("PATIENT_AUTH_REQUIRE_CLINIC_SLUG", raising=False)
    monkeypatch.delenv("RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_LIMIT", raising=False)
    monkeypatch.delenv("RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_WINDOW_SECONDS", raising=False)
    monkeypatch.delenv("DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS", raising=False)
    s = _minimal_settings(
        app_env="production",
    )
    assert s.patient_auth_require_clinic_slug is True
    assert s.rate_auth_unknown_clinic_slug_ip_limit == 90
    assert s.rate_auth_unknown_clinic_slug_ip_window_seconds == 600
    assert s.domain_outbox_max_dispatch_attempts == 50

