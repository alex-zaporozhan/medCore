"""Unit tests for §27–§28 path/query classification (no HTTP)."""

from src.core.security_observability import (
    metrics_path_class,
    security_auth_failure_reason,
    spam_blocked_channel,
    suspicious_request_signal,
)


def test_spam_blocked_channel_embed() -> None:
    assert spam_blocked_channel("/api/v1/public/embed/health") == "embed"


def test_spam_blocked_channel_platform_webhook() -> None:
    assert (
        spam_blocked_channel("/api/v1/platform/billing/webhooks/yookassa")
        == "platform_billing_webhook"
    )


def test_spam_blocked_channel_chat() -> None:
    assert spam_blocked_channel("/api/v1/admin/omni/foo") == "chat"


def test_security_auth_failure_skips_health() -> None:
    assert security_auth_failure_reason("/health", 401) is None


def test_security_auth_failure_admin_401() -> None:
    assert (
        security_auth_failure_reason("/api/v1/admin/foo", 401) == "admin_unauthorized"
    )


def test_security_auth_failure_admin_403_privileged() -> None:
    assert (
        security_auth_failure_reason("/api/v1/admin/auth/session", 403)
        == "forbidden_privileged"
    )


def test_suspicious_path_traversal() -> None:
    sig = suspicious_request_signal("/api/v1/admin/../../../etc/passwd", "")
    assert sig is not None
    assert sig[1] == "path_traversal_probe"


def test_suspicious_known_probe() -> None:
    sig = suspicious_request_signal("/api/v1/static/.env", "")
    assert sig is not None
    assert sig[1] == "known_probe_path"


def test_suspicious_sql_union_in_query() -> None:
    sig = suspicious_request_signal("/api/v1/foo", "x=union+select")
    assert sig is not None
    assert sig[1] == "sql_injection_probe"


def test_metrics_path_class() -> None:
    assert metrics_path_class("/api/v1/admin/x") == "admin_api"
    assert metrics_path_class("/api/v1/patient/x") == "public_api"
