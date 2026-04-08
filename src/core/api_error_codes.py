"""Stable machine-readable API error codes: lowercase snake_case (1c-Q2 / §28)."""

from __future__ import annotations

import re

# Keys only used for message extraction / code — everything else goes to JSON ``details``.
# ``trace_id`` is promoted to the top-level body (prefer ``request.state``; else from detail).
HTTP_EXCEPTION_STANDARD_KEYS = frozenset({"code", "message", "detail", "trace_id"})

HTTP_STATUS_DEFAULT_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
}


def normalize_api_error_code(raw: str | None) -> str:
    """
    Normalize to lowercase snake_case for JSON ``code`` (public contract).

    Accepts camelCase, SCREAMING_SNAKE, kebab-case, or already-normal values.
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    s = s.replace("-", "_").replace(" ", "_")
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"__+", "_", s)
    return s.lower()
