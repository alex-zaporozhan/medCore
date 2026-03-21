"""Admin API: global AI status metadata."""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.application.services.ai_client_factory import build_safe_ai_client
from src.api.v1.dependencies import require_permissions


router = APIRouter(prefix="/admin/ai-status", tags=["admin-ai-status"])
logger = logging.getLogger(__name__)


class AiStatusResponse(BaseModel):
    ai_mode: str
    features: dict[str, bool]


@router.get("", response_model=AiStatusResponse)
async def get_ai_status(
    _=Depends(require_permissions("view_ai_settings")),
) -> AiStatusResponse:
    # Global status: use strict external provider config without personal data.
    safe_client, ctx = await build_safe_ai_client(clinic_id=None, session=None)
    logger.info(
        "build_safe_ai_client used for admin_ai_status",
        extra={
            "source": "admin_ai_status",
            "clinic_id": None,
            "provider_type": ctx.provider_type,
            "allow_personal_data": ctx.allow_personal_data,
        },
    )
    if safe_client.is_configured():
        ai_mode = "external_active"
    else:
        ai_mode = "fallback_local"

    features: dict[str, bool] = {
        "chat_summary": True,
        "chat_suggest_reply": True,
        "patient_insight": True,
        "conflict_reports": True,
    }
    return AiStatusResponse(ai_mode=ai_mode, features=features)

