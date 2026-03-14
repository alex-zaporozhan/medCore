"""Owner API for managing omnichannel business channels and credentials (Phase 5).

Endpoints:
- GET  /owner/channels
- POST /owner/channels
- PUT  /owner/channels/{id}
- POST /owner/channels/{id}/credentials
"""

from uuid import UUID

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.omnichannel_integrations_config_service import (
    OmnichannelIntegrationsConfigService,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.omnichannel_channel import Channel as OmniChannel
from src.domain.entities.omnichannel_integration_config import (
    OmnichannelIntegrationConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/owner/channels", tags=["owner-omni-channels"])


class OwnerChannelDto(BaseModel):
    id: UUID
    type: str
    display_name: str
    status: str
    has_credentials: bool


class OwnerChannelsResponse(BaseModel):
    items: list[OwnerChannelDto]


class CreateChannelRequest(BaseModel):
    type: str = Field(..., max_length=32)
    display_name: str = Field(..., max_length=255)


class UpdateChannelRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=32)


class ChannelCredentialsRequest(BaseModel):
    provider_type: str = Field(..., max_length=64)
    scopes: str | None = Field(default=None, max_length=255)
    payload: str = Field(..., max_length=4000, description="Provider-specific secret/token JSON or string")


async def _load_integration_configs(
    session: AsyncSession,
    business_account_id: UUID,
    channel_ids: list[UUID],
) -> dict[UUID, OmnichannelIntegrationConfig]:
    if not channel_ids:
        return {}
    stmt = select(OmnichannelIntegrationConfig).where(
        OmnichannelIntegrationConfig.business_account_id == business_account_id,
        OmnichannelIntegrationConfig.channel_id.in_(channel_ids),
    )
    result = await session.execute(stmt)
    configs: dict[UUID, OmnichannelIntegrationConfig] = {}
    for row in result.scalars().all():
        configs[row.channel_id] = row
    return configs


@router.get("", response_model=OwnerChannelsResponse)
async def list_owner_channels(
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OwnerChannelsResponse:
    """List omnichannel channels for current clinic (Owner view)."""
    business_account_id: UUID = current_admin.clinic_id

    stmt = select(OmniChannel).where(OmniChannel.business_account_id == business_account_id)
    result = await session.execute(stmt)
    channels: list[OmniChannel] = list(result.scalars().all())

    configs = await _load_integration_configs(
        session=session,
        business_account_id=business_account_id,
        channel_ids=[c.id for c in channels],
    )

    items: list[OwnerChannelDto] = []
    for ch in channels:
        cfg = configs.get(ch.id)
        has_credentials = bool(cfg and cfg.credentials_encrypted and cfg.credentials_encrypted.strip())
        items.append(
            OwnerChannelDto(
                id=ch.id,
                type=ch.type,
                display_name=ch.display_name,
                status=ch.status,
                has_credentials=has_credentials,
            )
        )
    return OwnerChannelsResponse(items=items)


@router.post("", response_model=OwnerChannelDto, status_code=status.HTTP_201_CREATED)
async def create_owner_channel(
    body: CreateChannelRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OwnerChannelDto:
    """Create new omnichannel Channel for current clinic."""
    business_account_id: UUID = current_admin.clinic_id
    channel = OmniChannel(
        business_account_id=business_account_id,
        type=body.type.strip().upper(),
        display_name=body.display_name.strip(),
        status="PENDING_SETUP",
    )
    session.add(channel)
    await session.flush()
    await session.refresh(channel)

    logger.info(
        "Owner created omnichannel channel",
        extra={
            "business_account_id": str(business_account_id),
            "channel_id": str(channel.id),
            "type": channel.type,
        },
    )

    return OwnerChannelDto(
        id=channel.id,
        type=channel.type,
        display_name=channel.display_name,
        status=channel.status,
        has_credentials=False,
    )


@router.put("/{channel_id}", response_model=OwnerChannelDto)
async def update_owner_channel(
    channel_id: UUID,
    body: UpdateChannelRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> OwnerChannelDto:
    """Update channel display_name or status for current clinic."""
    business_account_id: UUID = current_admin.clinic_id
    stmt = select(OmniChannel).where(
        OmniChannel.id == channel_id,
        OmniChannel.business_account_id == business_account_id,
    ).limit(1)
    result = await session.execute(stmt)
    channel: OmniChannel | None = result.scalar_one_or_none()
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    data = body.model_dump(exclude_unset=True)
    if "display_name" in data and data["display_name"] is not None:
        channel.display_name = data["display_name"].strip()
    if "status" in data and data["status"] is not None:
        channel.status = data["status"].strip().upper()

    await session.flush()
    await session.refresh(channel)

    cfg_service = OmnichannelIntegrationsConfigService(session)
    cfg = await cfg_service.get_config_for_channel(
        business_account_id=business_account_id,
        channel_id=channel.id,
    )
    has_credentials = bool(cfg and cfg.credentials_encrypted and cfg.credentials_encrypted.strip())

    return OwnerChannelDto(
        id=channel.id,
        type=channel.type,
        display_name=channel.display_name,
        status=channel.status,
        has_credentials=has_credentials,
    )


@router.post(
    "/{channel_id}/credentials",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def set_channel_credentials(
    channel_id: UUID,
    body: ChannelCredentialsRequest,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    """Store encrypted provider credentials for channel and write AuditLog.

    Only current clinic owner/admin can call this endpoint. The raw payload
    is never returned back to clients; only has_credentials/status are exposed.
    """
    business_account_id: UUID = current_admin.clinic_id
    stmt = select(OmniChannel).where(
        OmniChannel.id == channel_id,
        OmniChannel.business_account_id == business_account_id,
    ).limit(1)
    result = await session.execute(stmt)
    channel: OmniChannel | None = result.scalar_one_or_none()
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    svc = OmnichannelIntegrationsConfigService(session)
    await svc.store_integration_secret(
        business_account_id=business_account_id,
        channel_id=channel_id,
        provider_type=body.provider_type.strip(),
        scopes=body.scopes.strip() if body.scopes else None,
        raw_secret=body.payload,
        actor_id=current_admin.id,
        actor_type="OWNER",
    )

