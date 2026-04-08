"""Phase 0 / U-006: contour A vs B webhook secret rules."""

import pytest

from src.core.config import settings
from src.core.payment_webhook_governance import (
    assert_enforced_patient_payment_webhook_secret_in_production,
    assert_required_security_secrets_in_production,
    validate_distinct_webhook_secrets,
)


def test_validate_distinct_webhook_secrets_ok_when_one_empty():
    validate_distinct_webhook_secrets("", "platform-only")
    validate_distinct_webhook_secrets("patient-only", "")
    validate_distinct_webhook_secrets("", "")


def test_validate_distinct_webhook_secrets_ok_when_different():
    validate_distinct_webhook_secrets("secret-a", "secret-b")


def test_validate_distinct_webhook_secrets_rejects_identical_non_empty():
    with pytest.raises(RuntimeError, match="must differ"):
        validate_distinct_webhook_secrets("same-value", "same-value")


def test_assert_enforced_patient_secret_noop_when_not_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "enforce_patient_payment_webhook_secret_in_production", True)
    monkeypatch.setattr(settings, "patient_payment_webhook_secret", "")
    assert_enforced_patient_payment_webhook_secret_in_production()


def test_assert_enforced_patient_secret_noop_when_flag_off(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "enforce_patient_payment_webhook_secret_in_production", False)
    monkeypatch.setattr(settings, "patient_payment_webhook_secret", "")
    assert_enforced_patient_payment_webhook_secret_in_production()


def test_assert_enforced_patient_secret_ok_when_secret_set(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "enforce_patient_payment_webhook_secret_in_production", True)
    monkeypatch.setattr(settings, "patient_payment_webhook_secret", "whsec-ok")
    assert_enforced_patient_payment_webhook_secret_in_production()


def test_assert_enforced_patient_secret_raises_when_prod_empty_and_enforced(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "enforce_patient_payment_webhook_secret_in_production", True)
    monkeypatch.setattr(settings, "patient_payment_webhook_secret", "")
    with pytest.raises(RuntimeError, match="ENFORCE_PATIENT_PAYMENT_WEBHOOK_SECRET"):
        assert_enforced_patient_payment_webhook_secret_in_production()


def test_assert_required_security_secrets_noop_when_not_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "patient_payment_webhook_secret", "")
    monkeypatch.setattr(settings, "platform_billing_webhook_secret", "")
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "")
    monkeypatch.setattr(settings, "jwt_secret_key", "")
    assert_required_security_secrets_in_production()


def test_assert_required_security_secrets_raises_with_missing_list(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "patient_payment_webhook_secret", "")
    monkeypatch.setattr(settings, "platform_billing_webhook_secret", "whsec-platform")
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "")
    monkeypatch.setattr(settings, "jwt_secret_key", "")
    with pytest.raises(
        RuntimeError,
        match="PATIENT_PAYMENT_WEBHOOK_SECRET.*PLATFORM_FOUNDER_JWT_SECRET.*JWT_SECRET_KEY",
    ):
        assert_required_security_secrets_in_production()


def test_assert_required_security_secrets_ok_when_all_set(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "patient_payment_webhook_secret", "whsec-patient")
    monkeypatch.setattr(settings, "platform_billing_webhook_secret", "whsec-platform")
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", "whsec-founder-jwt")
    monkeypatch.setattr(settings, "jwt_secret_key", "jwt-secret")
    assert_required_security_secrets_in_production()
