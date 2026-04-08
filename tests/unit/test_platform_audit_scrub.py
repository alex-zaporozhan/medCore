"""1a-E4 / PRC-A5: platform audit must not merge PII keys from extra."""

import logging
import uuid

import pytest

from src.core.platform_audit import log_platform_audit


def test_platform_audit_drops_email_like_keys_from_extra(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="platform_audit")
    log_platform_audit(
        action="test_scrub",
        actor_founder_id=uuid.uuid4(),
        extra={"email": "leak@example.com", "totp_used": True},
    )
    assert "leak@example.com" not in caplog.text
    rec = caplog.records[-1]
    assert getattr(rec, "totp_used", None) is True


def test_platform_audit_drops_suffix_email_keys() -> None:
    from src.core.platform_audit import _scrub_audit_extra

    assert "owner_email" not in _scrub_audit_extra({"owner_email": "x@y.z", "step": 1})
    assert _scrub_audit_extra({"step": 1}) == {"step": 1}
