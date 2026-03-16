"""AI Command Line for Spotlight. B5.2."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from uuid import UUID

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.domain.entities.admin_user import AdminUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai-agent"])

# In-memory rate limit: clinic_id -> list of request timestamps (sliding window 1 min, max 60/min)
_agent_rate: dict[UUID, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60.0
RATE_LIMIT_MAX = 60


def _check_rate_limit(clinic_id: UUID) -> None:
    now = time.monotonic()
    key = clinic_id
    if key not in _agent_rate:
        _agent_rate[key] = []
    times = _agent_rate[key]
    # Drop older than window
    times[:] = [t for t in times if now - t < RATE_LIMIT_WINDOW]
    if len(times) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for AI agent",
        )
    times.append(now)


class AiAgentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class AiAgentActionItem(BaseModel):
    tool: str
    result: str


class AiAgentResponse(BaseModel):
    reply: str
    actions: list[AiAgentActionItem] = []


@router.post("/agent", response_model=AiAgentResponse)
async def ai_agent_command(
    body: AiAgentRequest,
    session=Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AiAgentResponse:
    """AI Command Line for Spotlight. Context: clinic_id, admin_id from token. Rate limit per clinic. Stub when AI not wired."""
    clinic_id = current_admin.clinic_id
    if not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clinic context required",
        )
    _check_rate_limit(clinic_id)

    # Stub: return static reply and empty actions. Later wire OmnichannelAIOrchestrator or dedicated command flow.
    logger.info(
        "ai_agent_command",
        extra={
            "clinic_id": str(clinic_id),
            "admin_id": str(current_admin.id) if current_admin.id else None,
            "text_len": len(body.text),
        },
    )
    return AiAgentResponse(
        reply="Команда принята. Функция AI-агента будет подключена в следующей версии.",
        actions=[],
    )


# --- B5.4 generate-offers ---
class GenerateOffersRequest(BaseModel):
    segment_id: UUID | None = None
    cohort: str | None = None


class OfferItem(BaseModel):
    patient_id: UUID
    offer_text: str


class GenerateOffersResponse(BaseModel):
    offers: list[OfferItem]


@router.post("/generate-offers", response_model=GenerateOffersResponse)
async def generate_offers(
    body: GenerateOffersRequest,
    session=Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> GenerateOffersResponse:
    """Generate personalised offers for segment/cohort. Stub: empty list until AI wired."""
    if not current_admin.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clinic context required",
        )
    return GenerateOffersResponse(offers=[])
