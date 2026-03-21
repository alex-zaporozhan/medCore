"""Admin API: lightweight UI telemetry events (non-PII)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.v1.dependencies import require_permissions


router = APIRouter(prefix="/admin/ui-events", tags=["admin-ui-events"])
logger = logging.getLogger(__name__)


class UiEventRequest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=64)
    clinic_id: str | None = None
    feature_id: str | None = None
    feature_status: str | None = None
    trace_id: str | None = None
    meta: dict[str, Any] | None = None


@router.post("", dependencies=[Depends(require_permissions("view_dashboard"))])
async def post_ui_event(body: UiEventRequest) -> dict[str, str]:
    # IMPORTANT: Do not log PII. This endpoint is for feature readiness/UX monitoring only.
    logger.info(
        "ui_event",
        extra={
            "event_name": body.event_name,
            "clinic_id": body.clinic_id,
            "feature_id": body.feature_id,
            "feature_status": body.feature_status,
            "trace_id": body.trace_id,
            "meta": body.meta,
            "source": "admin_ui_events",
        },
    )
    return {"status": "ok"}

