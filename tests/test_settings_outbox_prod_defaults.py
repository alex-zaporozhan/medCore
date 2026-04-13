"""Settings: production default for outbox dispatch cap (QA_ARCH / ADR-009)."""

import pytest

from src.core.config import Settings


def _minimal_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-" + "x" * 16)
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-" + "x" * 16)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")


def test_production_applies_outbox_cap_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TESTING", raising=False)
    _minimal_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS", raising=False)

    s = Settings()
    assert s.domain_outbox_max_dispatch_attempts == 50


def test_production_respects_explicit_zero_unlimited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TESTING", raising=False)
    _minimal_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS", "0")

    s = Settings()
    assert s.domain_outbox_max_dispatch_attempts == 0


def test_development_keeps_zero_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TESTING", raising=False)
    _minimal_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS", raising=False)

    s = Settings()
    assert s.domain_outbox_max_dispatch_attempts == 0
