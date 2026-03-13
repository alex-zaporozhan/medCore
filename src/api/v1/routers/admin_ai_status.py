"""Admin API: global AI status metadata."""

from fastapi import APIRouter
from pydantic import BaseModel

from src.infrastructure.external_apis.ai_client import AiClient
from src.infrastructure.external_apis.safe_ai_client import SafeAiClient


router = APIRouter(prefix="/admin/ai-status", tags=["admin-ai-status"])


class AiStatusResponse(BaseModel):
    ai_mode: str
    features: dict[str, bool]


@router.get("", response_model=AiStatusResponse)
async def get_ai_status() -> AiStatusResponse:
    safe_client = SafeAiClient(AiClient())
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

