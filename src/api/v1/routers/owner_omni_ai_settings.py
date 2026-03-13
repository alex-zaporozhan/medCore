"""Owner API for omnichannel AI settings (Phase 6).

Endpoints:
- GET  /owner/omni-ai-settings
- PUT  /owner/omni-ai-settings

Scope:
- BUSINESS-level AI settings for omnichannel assistant;
- per-channel overrides (CHANNEL scope).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.omnichannel_ai_settings_service import (
    OmnichannelAISettingsService,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.omnichannel_ai_settings import AISettings as OmniAISettings
from src.domain.entities.omnichannel_channel import Channel as OmniChannel

router = APIRouter(prefix="/owner/omni-ai-settings", tags=["owner-omni-ai-settings"])

ALLOWED_OMNI_AI_MODES = {"AUTO_REPLY", "SUGGEST_ONLY", "DISABLED"}


class OmniChannelAiSettingsDto(BaseModel):
    channel_id: UUID
    channel_type: str
    channel_display_name: str
    ai_mode: str


class OmniBusinessAiSettingsDto(BaseModel):
    ai_mode: str
    working_hours_policy: dict | None = None
    confidence_thresholds: dict | None = None
    prompt_profile_id: str | None = None
    kb_profile_id: str | None = None


class OmniAiSettingsResponse(BaseModel):
    business: OmniBusinessAiSettingsDto
    channels: list[OmniChannelAiSettingsDto] = Field(default_factory=list)


class OmniBusinessAiSettingsUpdate(BaseModel):
    ai_mode: str | None = Field(default=None)
    working_hours_policy: dict | None = None
    confidence_thresholds: dict | None = None
    prompt_profile_id: str | None = None
    kb_profile_id: str | None = None


class OmniChannelAiSettingsUpdate(BaseModel):
    channel_id: UUID
    ai_mode: str


class OmniAiSettingsUpdateRequest(BaseModel):
    business: OmniBusinessAiSettingsUpdate | None = None
    channels: list[OmniChannelAiSettingsUpdate] | None = None


@router.get("", response_model=OmniAiSettingsResponse)
async def get_omni_ai_settings(
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OmniAiSettingsResponse:
    """Return BUSINESS and CHANNEL-level AI settings for omnichannel assistant."""
    business_account_id: UUID = current_admin.clinic_id
    svc = OmnichannelAISettingsService(session)

    effective_business = await svc.get_or_create_business_settings(business_account_id)

    # Load all channels for this business
    result = await session.execute(
        select(OmniChannel).where(OmniChannel.business_account_id == business_account_id)
    )
    channels: list[OmniChannel] = list(result.scalars().all())

    channel_items: list[OmniChannelAiSettingsDto] = []
    if channels:
        # Load channel-level overrides only when there are channels
        stmt = select(OmniAISettings).where(
            OmniAISettings.scope == "CHANNEL",
            OmniAISettings.scope_id.in_([c.id for c in channels]),
        )
        result_cfg = await session.execute(stmt)
        by_channel: dict[UUID, OmniAISettings] = {row.scope_id: row for row in result_cfg.scalars().all()}
    else:
        by_channel = {}

    for ch in channels:
        cfg = by_channel.get(ch.id)
        ai_mode = cfg.ai_mode if cfg and cfg.ai_mode else effective_business.ai_mode
        channel_items.append(
            OmniChannelAiSettingsDto(
                channel_id=ch.id,
                channel_type=ch.type,
                channel_display_name=ch.display_name,
                ai_mode=ai_mode,
            )
        )

    business_dto = OmniBusinessAiSettingsDto(
        ai_mode=effective_business.ai_mode,
        working_hours_policy=effective_business.working_hours_policy,
        confidence_thresholds=effective_business.confidence_thresholds,
        prompt_profile_id=effective_business.prompt_profile_id,
        kb_profile_id=effective_business.kb_profile_id,
    )

    return OmniAiSettingsResponse(business=business_dto, channels=channel_items)


@router.put("", response_model=OmniAiSettingsResponse)
async def update_omni_ai_settings(
    body: OmniAiSettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OmniAiSettingsResponse:
    """Update BUSINESS and CHANNEL-level AI settings for omnichannel assistant."""
    business_account_id: UUID = current_admin.clinic_id
    svc = OmnichannelAISettingsService(session)

    # Validate business-level mode if provided
    if body.business and body.business.ai_mode is not None:
        mode = body.business.ai_mode.upper()
        if mode not in ALLOWED_OMNI_AI_MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ai_mode for business",
            )

    # Validate channel-level modes
    channels_updates = body.channels or []
    for item in channels_updates:
        mode = item.ai_mode.upper()
        if mode not in ALLOWED_OMNI_AI_MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ai_mode for channel {item.channel_id}",
            )

    # Apply business-level update
    if body.business is not None:
        update_data = body.business.model_dump(exclude_unset=True)
        if "ai_mode" in update_data and update_data["ai_mode"] is not None:
            update_data["ai_mode"] = update_data["ai_mode"].upper()
        await svc.upsert_settings(
            scope="BUSINESS",
            scope_id=business_account_id,
            data=update_data,
        )

    # Apply channel-level updates
    for item in channels_updates:
        update_data = {"ai_mode": item.ai_mode.upper()}
        await svc.upsert_settings(
            scope="CHANNEL",
            scope_id=item.channel_id,
            data=update_data,
        )

    await session.flush()

    # Re-use GET handler logic for response
    return await get_omni_ai_settings(session=session, current_admin=current_admin)

