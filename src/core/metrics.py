"""Metrics and observability primitives for the application.

This module provides Prometheus-compatible counters for the omnichannel
assistant while remaining safe to import when `prometheus_client` is not
installed. In that case, all metric operations become no-ops.
"""

from __future__ import annotations

from typing import Any

from src.core.config import settings

try:  # pragma: no cover - import guard
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

    _PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - graceful fallback when prometheus_client is missing
    _PROMETHEUS_AVAILABLE = False

    class _NoopMetric:
        def labels(self, *args: Any, **kwargs: Any) -> "._NoopMetric":  # type: ignore[name-match]
            return self

        def inc(self, *args: Any, **kwargs: Any) -> None:
            return None

    def Counter(*args: Any, **kwargs: Any) -> _NoopMetric:  # type: ignore[no-redef]
        return _NoopMetric()

    def generate_latest(*args: Any, **kwargs: Any) -> bytes:  # type: ignore[no-redef]
        return b""

    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"  # type: ignore[assignment]


# ------------------------------------------------------------------------------
# Core omnichannel metrics
# ------------------------------------------------------------------------------

# Total omnichannel messages by direction, actor type and channel.
# This allows:
# - counting inbound/outbound messages per channel;
# - computing share of AI vs human replies by filtering actor_type.
omni_messages_total = Counter(  # type: ignore[call-arg]
    "omni_messages_total",
    "Total omnichannel messages by direction, actor type and channel.",
    ["direction", "actor_type", "channel_id", "business_account_id"],
)

# Total AI auto replies that were actually sent to clients.
omni_ai_auto_replies_total = Counter(  # type: ignore[call-arg]
    "omni_ai_auto_replies_total",
    "Total AI auto replies sent to clients.",
    ["business_account_id"],
)

# Total AI suggestions (SUGGEST_ONLY mode) stored for admins.
omni_ai_suggestions_total = Counter(  # type: ignore[call-arg]
    "omni_ai_suggestions_total",
    "Total AI suggestions stored as drafts for admins.",
    ["business_account_id"],
)

# Escalations to human operators from the AI pipeline.
# reason examples: "low_confidence", "provider_not_configured", "explicit_request".
omni_ai_escalations_total = Counter(  # type: ignore[call-arg]
    "omni_ai_escalations_total",
    "Total AI escalations that require human operators.",
    ["reason"],
)

# Errors when talking to external AI provider (network, rate-limit, timeouts, 5xx, etc.).
omni_ai_provider_errors_total = Counter(  # type: ignore[call-arg]
    "omni_ai_provider_errors_total",
    "Errors from external AI provider in omnichannel pipeline.",
    ["source", "error_type"],
)


def render_prometheus_metrics() -> tuple[bytes, str]:
    """Return serialized metrics payload and content type.

    If Prometheus client is not available or metrics are disabled via settings,
    returns an empty payload with text/plain content type.
    """
    if not _PROMETHEUS_AVAILABLE or getattr(settings, "metrics_enabled", True) is False:
        # Minimal safe response so that /metrics endpoint is always callable.
        return b"", "text/plain; charset=utf-8"

    data = generate_latest()
    return data, CONTENT_TYPE_LATEST

