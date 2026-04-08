"""Structured audit for sensitive `/platform/*` actions (1a-E4) — no email/phone in payload."""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger("platform_audit")

# Keys we never merge into audit `extra` (1a-E4 / PRC-A5) — callers must not smuggle PII.
_SENSITIVE_EXTRA_KEYS = frozenset(
    {
        "email",
        "phone",
        "password",
        "password_hash",
        "totp_code",
        "mfa_token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "otpauth_uri",
        "recovery_code",
        "secret",
        "webhook_secret",
    }
)


def _scrub_audit_extra(extra: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in extra.items():
        kl = k.lower()
        if kl in _SENSITIVE_EXTRA_KEYS:
            continue
        if "password" in kl or kl.endswith("_secret") or kl.endswith("_token"):
            continue
        if kl == "email" or kl.endswith("_email"):
            continue
        out[k] = v
    return out


def log_platform_audit(
    *,
    action: str,
    actor_founder_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "platform_audit",
        "action": action,
        "actor_founder_id": str(actor_founder_id) if actor_founder_id else None,
        "resource_type": resource_type,
        "resource_id": resource_id,
    }
    if extra:
        for k, v in _scrub_audit_extra(extra).items():
            if k in payload:
                continue
            payload[k] = v
    logger.info("platform_audit %s", action, extra=payload)
