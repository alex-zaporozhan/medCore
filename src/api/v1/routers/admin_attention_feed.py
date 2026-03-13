"""Admin attention feed API router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.attention_feed_dto import AttentionFeedRead
from src.application.services.attention_feed_service import AttentionFeedService
from src.domain.entities.admin_user import AdminUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/clinics", tags=["admin-attention-feed"])


@router.get(
    "/{clinic_id}/attention-feed",
    response_model=AttentionFeedRead,
)
async def get_attention_feed(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AttentionFeedRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = AttentionFeedService(session)
    return await service.get_feed(clinic_id)


@router.post(
    "/{clinic_id}/attention-feed/follow-up/{message_id}/close",
    status_code=status.HTTP_200_OK,
)
async def close_follow_up_item(
    clinic_id: UUID,
    message_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service = AttentionFeedService(session)
    ok = await service.close_follow_up(clinic_id, message_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    return {"ok": True}

