"""Admin API: owner integration settings (Morning Brief, AI Supervisor) per clinic. B5.6."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.owner_integration_settings import OwnerIntegrationSettings

router = APIRouter(prefix="/admin/clinics", tags=["admin-owner-settings"])


# --- Owner Morning Brief ---
class OwnerBriefSettingsRead(BaseModel):
    enabled: bool
    send_at_utc: str | None = None  # "09:00"
    telegram_chat_id: str | None = None


class OwnerBriefSettingsUpdate(BaseModel):
    enabled: bool | None = None
    send_at_utc: str | None = Field(None, max_length=8, description="HH:MM UTC, e.g. 09:00")
    telegram_chat_id: str | None = Field(None, max_length=128)


async def _get_owner_settings(session: AsyncSession, clinic_id: UUID) -> OwnerIntegrationSettings | None:
    result = await session.execute(
        select(OwnerIntegrationSettings).where(OwnerIntegrationSettings.clinic_id == clinic_id).limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/{clinic_id}/settings/owner-brief", response_model=OwnerBriefSettingsRead)
async def get_owner_brief_settings(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _=Depends(require_permissions("view_crm")),
) -> OwnerBriefSettingsRead:
    """Get owner morning brief settings. Returns defaults if not configured."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    row = await _get_owner_settings(session, clinic_id)
    if not row:
        return OwnerBriefSettingsRead(enabled=False, send_at_utc="09:00", telegram_chat_id=None)
    return OwnerBriefSettingsRead(
        enabled=row.owner_morning_brief_enabled,
        send_at_utc=row.morning_brief_send_at_utc or "09:00",
        telegram_chat_id=row.owner_telegram_chat_id,
    )


@router.patch("/{clinic_id}/settings/owner-brief", response_model=OwnerBriefSettingsRead)
async def update_owner_brief_settings(
    clinic_id: UUID,
    data: OwnerBriefSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _=Depends(require_permissions("manage_ai_settings")),
) -> OwnerBriefSettingsRead:
    """Update owner morning brief settings."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    row = await _get_owner_settings(session, clinic_id)
    if not row:
        row = OwnerIntegrationSettings(clinic_id=clinic_id)
        session.add(row)
        await session.flush()
    if data.enabled is not None:
        row.owner_morning_brief_enabled = data.enabled
    if data.send_at_utc is not None:
        row.morning_brief_send_at_utc = (data.send_at_utc.strip() or None) if data.send_at_utc else None
    if data.telegram_chat_id is not None:
        row.owner_telegram_chat_id = (data.telegram_chat_id.strip() or None) if data.telegram_chat_id else None
    await session.flush()
    await session.refresh(row)
    return OwnerBriefSettingsRead(
        enabled=row.owner_morning_brief_enabled,
        send_at_utc=row.morning_brief_send_at_utc or "09:00",
        telegram_chat_id=row.owner_telegram_chat_id,
    )


# --- AI Supervisor ---
class AiSupervisorSettingsRead(BaseModel):
    enabled: bool
    send_at_utc: str | None = None  # "20:00"
    recipient_chat_ids: list[str] = Field(default_factory=list)


class AiSupervisorSettingsUpdate(BaseModel):
    enabled: bool | None = None
    send_at_utc: str | None = Field(None, max_length=8)
    recipient_chat_ids: list[str] | None = None


@router.get("/{clinic_id}/settings/ai-supervisor", response_model=AiSupervisorSettingsRead)
async def get_ai_supervisor_settings(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _=Depends(require_permissions("view_crm")),
) -> AiSupervisorSettingsRead:
    """Get AI supervisor summary settings."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    row = await _get_owner_settings(session, clinic_id)
    if not row:
        return AiSupervisorSettingsRead(enabled=False, send_at_utc="20:00", recipient_chat_ids=[])
    return AiSupervisorSettingsRead(
        enabled=row.ai_supervisor_enabled,
        send_at_utc=row.ai_supervisor_send_at_utc or "20:00",
        recipient_chat_ids=list(row.ai_supervisor_recipient_chat_ids or []),
    )


@router.patch("/{clinic_id}/settings/ai-supervisor", response_model=AiSupervisorSettingsRead)
async def update_ai_supervisor_settings(
    clinic_id: UUID,
    data: AiSupervisorSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _=Depends(require_permissions("manage_ai_settings")),
) -> AiSupervisorSettingsRead:
    """Update AI supervisor summary settings."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    row = await _get_owner_settings(session, clinic_id)
    if not row:
        row = OwnerIntegrationSettings(clinic_id=clinic_id)
        session.add(row)
        await session.flush()
    if data.enabled is not None:
        row.ai_supervisor_enabled = data.enabled
    if data.send_at_utc is not None:
        row.ai_supervisor_send_at_utc = (data.send_at_utc.strip() or None) if data.send_at_utc else None
    if data.recipient_chat_ids is not None:
        row.ai_supervisor_recipient_chat_ids = [s.strip() for s in data.recipient_chat_ids if s and s.strip()]
    await session.flush()
    await session.refresh(row)
    return AiSupervisorSettingsRead(
        enabled=row.ai_supervisor_enabled,
        send_at_utc=row.ai_supervisor_send_at_utc or "20:00",
        recipient_chat_ids=list(row.ai_supervisor_recipient_chat_ids or []),
    )
