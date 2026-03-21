"""HTTP detail payloads for multi-tenant boundary errors."""

from __future__ import annotations

from src.application.multitenancy import ClinicForbiddenError
from src.core.context import RequestContext


def clinic_forbidden_admin_detail(
    exc: ClinicForbiddenError,
    ctx: RequestContext | None = None,
) -> dict:
    """JSON-serializable body for HTTP 403 on admin routes."""
    trace_id = getattr(ctx, "trace_id", None) if ctx is not None else None
    return {
        "code": "clinic_forbidden",
        "message": exc.message,
        "entity_label": exc.entity_label,
        "expected_clinic_id": str(exc.expected_clinic_id),
        "entity_clinic_id": str(exc.entity_clinic_id) if exc.entity_clinic_id else None,
        "entity_id": str(exc.entity_id) if exc.entity_id else None,
        "trace_id": trace_id,
    }
