"""Low-cardinality classification for §27–§28 SOC metrics (SAAS master plan).

Heuristics are intentionally conservative: false negatives preferred over noisy labels.
"""

from __future__ import annotations

from urllib.parse import unquote


def metrics_path_class(path: str) -> str:
    """Bucket path for `security_suspicious_request_total` labels (no raw paths)."""
    p = path or ""
    if p.startswith("/api/v1/admin"):
        return "admin_api"
    if p.startswith("/api/v1/public/embed"):
        return "embed_api"
    if p.startswith("/api/v1/platform"):
        return "platform_api"
    if p.startswith("/api/v1"):
        return "public_api"
    return "root"


def spam_blocked_channel(path: str) -> str:
    """Channel label for HTTP 429 (rate limit / anti-abuse), §27."""
    p = (path or "").lower()
    if "/public/embed" in p:
        return "embed"
    if "/platform/billing/webhooks" in p:
        return "platform_billing_webhook"
    if "/platform/internal" in p:
        return "platform_founder"
    if "/public/platform" in p:
        return "public_platform"
    if "/admin/auth" in p:
        return "admin_auth"
    if p.startswith("/api/v1/auth"):
        if "/send-code" in p or "/verify-code" in p:
            return "public_signup"
        return "public_auth"
    if (
        "/patient/chat" in p
        or "/admin/chat" in p
        or "/staff-collab" in p
        or "/admin/omni" in p
    ):
        return "chat"
    if "/integrations" in p and "/api/v1" in p:
        return "integration_gateway"
    if "/clinics" in p and p.startswith("/api/v1"):
        return "patient_portal_clinics"
    return "other"


def security_auth_failure_reason(path: str, status_code: int) -> str | None:
    """Map 401/403 to a small `reason` set for `security_auth_failure_total`, §28."""
    if status_code not in (401, 403):
        return None
    p = path or ""
    if p in ("/metrics", "/health", "/health/replica", "/health/s3"):
        return None
    if status_code == 403:
        if p.startswith("/api/v1/admin") or p.startswith("/api/v1/platform/internal"):
            return "forbidden_privileged"
        return "forbidden"
    if p.startswith("/api/v1/platform/internal"):
        return "platform_founder_unauthorized"
    if p.startswith("/api/v1/admin"):
        return "admin_unauthorized"
    if p.startswith("/api/v1/platform/"):
        return "platform_unauthorized"
    return "public_unauthorized"


def suspicious_request_signal(path: str, query: str) -> tuple[str, str] | None:
    """
    If the request looks like a trivial probe, return (path_class, reason).
    Never blocks the request — counting only.
    """
    pc = metrics_path_class(path)
    raw_path = unquote((path or "").lower())
    q = (query or "").lower()
    if ".." in raw_path or "%2e%2e" in (path or "").lower():
        return pc, "path_traversal_probe"
    probes = (
        "/.env",
        "/.git",
        "/wp-admin",
        "/wp-login",
        "/phpmyadmin",
        "/actuator/",
        "/server-status",
        "/web.config",
        "/config.json",
        "/.aws/",
        "shell.jsp",
    )
    for needle in probes:
        if needle in raw_path:
            return pc, "known_probe_path"
    if "union+select" in q or "union%20select" in q:
        return pc, "sql_injection_probe"
    return None
