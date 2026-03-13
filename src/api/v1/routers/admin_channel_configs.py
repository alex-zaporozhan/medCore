"""Admin API: notification channel configs (Telegram, SMS, Email) per clinic."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.notification_channel_config_dto import (
    NotificationChannelConfigCreate,
    NotificationChannelConfigRead,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.notification_channel_config import NotificationChannelConfig

router = APIRouter(prefix="/admin/clinics", tags=["admin-channel-configs"])


@router.get(
    "/{clinic_id}/channel-configs",
    response_model=list[NotificationChannelConfigRead],
)
async def list_channel_configs(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    """List all channel configs for a clinic."""
    result = await session.execute(
        select(NotificationChannelConfig).where(
            NotificationChannelConfig.clinic_id == clinic_id
        )
    )
    rows = result.scalars().all()
    return [NotificationChannelConfigRead.model_validate(r) for r in rows]


@router.put(
    "/{clinic_id}/channel-configs/{channel}",
    response_model=NotificationChannelConfigRead,
)
async def upsert_channel_config(
    clinic_id: UUID,
    channel: str,
    body: NotificationChannelConfigCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    """Create or update config for one channel (telegram, sms, email)."""
    if channel not in ("telegram", "sms", "email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="channel must be telegram, sms, or email",
        )
    if body.channel != channel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="channel in path and body must match",
        )
    result = await session.execute(
        select(NotificationChannelConfig).where(
            NotificationChannelConfig.clinic_id == clinic_id,
            NotificationChannelConfig.channel == channel,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.enabled = body.enabled
        row.config_json = body.config_json or {}
        await session.flush()
        await session.refresh(row)
        return NotificationChannelConfigRead.model_validate(row)
    new_row = NotificationChannelConfig(
        clinic_id=clinic_id,
        channel=channel,
        enabled=body.enabled,
        config_json=body.config_json or {},
    )
    session.add(new_row)
    await session.flush()
    await session.refresh(new_row)
    return NotificationChannelConfigRead.model_validate(new_row)
