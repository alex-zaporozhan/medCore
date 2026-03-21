"""Tracing helpers for propagating trace_id across HTTP, Celery and domain flows.

This module centralizes how we:
- read trace_id from FastAPI RequestContext or raw headers;
- attach trace_id into Celery task payloads;
- extract trace_id inside Celery workers and expose it for logging/metrics.

To keep contracts stable, trace_id is always optional and added in a backwards-compatible way.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from src.core.context import RequestContext


TRACE_ID_KEY = "trace_id"


def with_trace_id(payload: MutableMapping[str, Any], context: RequestContext | None) -> MutableMapping[str, Any]:
    """Return payload augmented with trace_id from RequestContext if present.

    The function mutates and returns the same mapping for convenience.
    """
    if context and context.trace_id:
        # Do not overwrite explicit caller-provided trace_id if already set.
        payload.setdefault(TRACE_ID_KEY, context.trace_id)
    return payload


def extract_trace_id_from_payload(payload: Mapping[str, Any] | None) -> str | None:
    """Best-effort extraction of trace_id from Celery task payload/kwargs."""
    if not payload:
        return None
    value = payload.get(TRACE_ID_KEY)
    if isinstance(value, str) and value:
        return value
    return None


