"""Admin API: per-clinic AI settings."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.clinic_ai_settings_service import (
    ALLOWED_AI_MODES,
    ALLOWED_INTENTS,
    ClinicAiSettingsService,
)
from src.domain.entities.admin_user import AdminUser


router = APIRouter(prefix="/admin/clinics", tags=["admin-ai-settings"])


class AiSettingsRead(BaseModel):
    ai_enabled: bool
    ai_mode: str
    ai_business_prompt: str | None = None
    ai_allowed_intents: list[str] = Field(default_factory=list)
    ai_autoreply_enabled: bool
    ai_autoreply_hours: dict | None = None
    ai_provider_type: str


class AiSettingsUpdate(BaseModel):
    ai_enabled: bool | None = None
    ai_mode: str | None = Field(default=None)
    ai_business_prompt: str | None = None
    ai_allowed_intents: list[str] | None = None
    ai_autoreply_enabled: bool | None = None
    ai_autoreply_hours: dict | None = None
    ai_provider_type: str | None = None


@router.get(
    "/{clinic_id}/ai-settings",
    response_model=AiSettingsRead,
)
async def get_ai_settings(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AiSettingsRead:
    if clinic_id != current_admin.clinic_id:
        # Do not leak existence of other clinics
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    svc = ClinicAiSettingsService(session)
    settings = await svc.get_or_create_default(clinic_id)
    return AiSettingsRead(
        ai_enabled=settings.ai_enabled,
        ai_mode=settings.ai_mode,
        ai_business_prompt=settings.ai_business_prompt,
        ai_allowed_intents=settings.ai_allowed_intents,
        ai_autoreply_enabled=settings.ai_autoreply_enabled,
        ai_autoreply_hours=settings.ai_autoreply_hours,
        ai_provider_type=settings.ai_provider_type,
    )


@router.put(
    "/{clinic_id}/ai-settings",
    response_model=AiSettingsRead,
)
async def update_ai_settings(
    clinic_id: UUID,
    body: AiSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AiSettingsRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    data = body.model_dump(exclude_unset=True)
    if "ai_mode" in data and data["ai_mode"] not in ALLOWED_AI_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ai_mode",
        )
    if "ai_allowed_intents" in data:
        intents = list(data["ai_allowed_intents"] or [])
        for i in intents:
            if i not in ALLOWED_INTENTS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid intent: {i}",
                )
    svc = ClinicAiSettingsService(session)
    settings = await svc.update_settings(clinic_id, data)
    return AiSettingsRead(
        ai_enabled=settings.ai_enabled,
        ai_mode=settings.ai_mode,
        ai_business_prompt=settings.ai_business_prompt,
        ai_allowed_intents=settings.ai_allowed_intents,
        ai_autoreply_enabled=settings.ai_autoreply_enabled,
        ai_autoreply_hours=settings.ai_autoreply_hours,
        ai_provider_type=settings.ai_provider_type,
    )

