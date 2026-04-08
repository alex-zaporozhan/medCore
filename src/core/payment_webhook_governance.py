"""
Contour A (tenant booking payments) vs contour B (platform SaaS billing) — Phase 0 / U-006.

Contour A: POST /api/v1/payments/webhook
Contour B: POST /api/v1/platform/billing/webhooks/{provider}

Separate URLs, separate optional secrets, and a hard fail if both secrets are set but identical.
"""

from __future__ import annotations

import logging
import secrets

from src.core.config import settings

logger = logging.getLogger(__name__)

PATIENT_PAYMENT_WEBHOOK_SECRET_HEADER = "X-Patient-Payment-Webhook-Secret"


def verify_patient_payment_webhook_secret(header_value: str | None) -> bool:
    """If PATIENT_PAYMENT_WEBHOOK_SECRET is unset, accept any request (legacy MVP)."""
    expected = (settings.patient_payment_webhook_secret or "").strip()
    if not expected:
        return True
    if not header_value:
        return False
    return secrets.compare_digest(header_value.strip(), expected)


def validate_distinct_webhook_secrets(patient_secret: str, platform_secret: str) -> None:
    """
    When both optional secrets are configured, they must not match (PRC-B1 / U-006).

    Raises:
        RuntimeError: same non-empty value for contour A and B secrets.
    """
    a = (patient_secret or "").strip()
    b = (platform_secret or "").strip()
    if a and b and secrets.compare_digest(a, b):
        raise RuntimeError(
            "PATIENT_PAYMENT_WEBHOOK_SECRET and PLATFORM_BILLING_WEBHOOK_SECRET must "
            "differ when both are set (contour A vs B; U-006 / PRC-B1)."
        )


def assert_distinct_payment_webhook_secrets() -> None:
    validate_distinct_webhook_secrets(
        settings.patient_payment_webhook_secret,
        settings.platform_billing_webhook_secret,
    )


def assert_enforced_patient_payment_webhook_secret_in_production() -> None:
    """
    LEAD / Phase 0-Q1: optional fail-fast when contour A must not run without a shared secret.

    When ``enforce_patient_payment_webhook_secret_in_production`` is true and ``app_env`` is
    production, ``PATIENT_PAYMENT_WEBHOOK_SECRET`` must be non-empty.
    """
    env = str(settings.app_env).lower()
    if env not in ("production", "prod"):
        return
    if not settings.enforce_patient_payment_webhook_secret_in_production:
        return
    if (settings.patient_payment_webhook_secret or "").strip():
        return
    raise RuntimeError(
        "ENFORCE_PATIENT_PAYMENT_WEBHOOK_SECRET_IN_PRODUCTION=true but "
        "PATIENT_PAYMENT_WEBHOOK_SECRET is empty. Set the secret for contour A or turn off "
        "enforcement (document SEC waiver). See docs/artifacts/LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md §0-Q1."
    )


def assert_required_security_secrets_in_production() -> None:
    """
    Phase 1 / PRC-A3: fail-closed startup in production when critical secrets are empty.

    Required (non-empty) in APP_ENV=production:
    - PATIENT_PAYMENT_WEBHOOK_SECRET
    - PLATFORM_BILLING_WEBHOOK_SECRET
    - PLATFORM_FOUNDER_JWT_SECRET
    - JWT_SECRET_KEY
    """
    env = str(settings.app_env).lower().strip()
    if env not in ("production", "prod"):
        return

    required = {
        "PATIENT_PAYMENT_WEBHOOK_SECRET": (settings.patient_payment_webhook_secret or "").strip(),
        "PLATFORM_BILLING_WEBHOOK_SECRET": (settings.platform_billing_webhook_secret or "").strip(),
        "PLATFORM_FOUNDER_JWT_SECRET": (settings.platform_founder_jwt_secret or "").strip(),
        "JWT_SECRET_KEY": (settings.jwt_secret_key or "").strip(),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        missing_csv = ", ".join(missing)
        raise RuntimeError(
            "Production startup blocked: required security secrets are missing: "
            f"{missing_csv}. Configure runtime secrets (e.g. AWS Secrets Manager) "
            "before starting API."
        )


def log_payment_webhook_governance_on_startup() -> None:
    """Non-fatal hints for production operators."""
    env = str(settings.app_env).lower()
    if env != "production":
        return
    patient_on = bool((settings.patient_payment_webhook_secret or "").strip())
    platform_on = bool((settings.platform_billing_webhook_secret or "").strip())
    if not patient_on and (settings.yookassa_shop_id or "").strip():
        logger.warning(
            "[dental-booking] PATIENT_PAYMENT_WEBHOOK_SECRET unset in production while "
            "YooKassa is configured: contour A webhook has no shared-secret gate (set header "
            f"{PATIENT_PAYMENT_WEBHOOK_SECRET_HEADER}).",
            extra={"component": "payment_webhook_governance"},
        )
    if not platform_on:
        logger.warning(
            "[dental-booking] PLATFORM_BILLING_WEBHOOK_SECRET unset in production: "
            "contour B SaaS webhook returns 503 until configured.",
            extra={"component": "payment_webhook_governance"},
        )
