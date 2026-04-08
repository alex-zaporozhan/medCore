"""Settings: production defaults for patient auth (LEAD / QA_ARCH)."""

import pytest

from src.core.config import Settings


def _minimal_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-" + "x" * 16)
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-" + "x" * 16)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")


def test_production_applies_patient_auth_defaults_when_vars_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TESTING", raising=False)
    _minimal_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("PATIENT_AUTH_REQUIRE_CLINIC_SLUG", raising=False)
    monkeypatch.delenv("RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_LIMIT", raising=False)
    monkeypatch.delenv("RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_WINDOW_SECONDS", raising=False)

    s = Settings()
    assert s.patient_auth_require_clinic_slug is True
    assert s.rate_auth_unknown_clinic_slug_ip_limit == 90
    assert s.rate_auth_unknown_clinic_slug_ip_window_seconds == 600


def test_production_respects_explicit_patient_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TESTING", raising=False)
    _minimal_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PATIENT_AUTH_REQUIRE_CLINIC_SLUG", "false")
    monkeypatch.setenv("RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_LIMIT", "60")
    monkeypatch.setenv("RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_WINDOW_SECONDS", "300")

    s = Settings()
    assert s.patient_auth_require_clinic_slug is False
    assert s.rate_auth_unknown_clinic_slug_ip_limit == 60
    assert s.rate_auth_unknown_clinic_slug_ip_window_seconds == 300


def test_development_keeps_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TESTING", raising=False)
    _minimal_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("PATIENT_AUTH_REQUIRE_CLINIC_SLUG", raising=False)

    s = Settings()
    assert s.patient_auth_require_clinic_slug is False
    assert s.rate_auth_unknown_clinic_slug_ip_limit == 0
