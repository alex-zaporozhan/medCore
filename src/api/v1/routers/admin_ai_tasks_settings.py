"""Admin API: per-clinic AI Task Manager settings."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.ai_task_settings_service import (
    ALLOWED_CREATION_MODES,
    AiTaskSettingsService,
)
from src.domain.entities.admin_user import AdminUser


router = APIRouter(prefix="/admin/clinics", tags=["admin-ai-tasks"])


class AiTaskSettingsRead(BaseModel):
    ai_tasks_enabled: bool
    creation_mode: str
    allowed_task_classes: list[str] = Field(default_factory=list)
    daily_clinic_limit: int
    daily_patient_limit: int
    daily_doctor_limit: int
    analyzer_thresholds: dict | None = None


class AiTaskSettingsUpdate(BaseModel):
    ai_tasks_enabled: bool | None = None
    creation_mode: str | None = None
    allowed_task_classes: list[str] | None = None
    daily_clinic_limit: int | None = None
    daily_patient_limit: int | None = None
    daily_doctor_limit: int | None = None
    analyzer_thresholds: dict | None = None


@router.get(
    "/{clinic_id}/ai-task-settings",
    response_model=AiTaskSettingsRead,
    dependencies=[Depends(require_permissions("view_ai_settings"))],
)
async def get_ai_task_settings(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AiTaskSettingsRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    svc = AiTaskSettingsService(session)
    settings = await svc.get_or_create_default(clinic_id)
    return AiTaskSettingsRead(
        ai_tasks_enabled=settings.ai_tasks_enabled,
        creation_mode=settings.creation_mode,
        allowed_task_classes=settings.allowed_task_classes or [],
        daily_clinic_limit=settings.daily_clinic_limit,
        daily_patient_limit=settings.daily_patient_limit,
        daily_doctor_limit=settings.daily_doctor_limit,
        analyzer_thresholds=settings.analyzer_thresholds,
    )


@router.put(
    "/{clinic_id}/ai-task-settings",
    response_model=AiTaskSettingsRead,
    dependencies=[Depends(require_permissions("manage_ai_settings"))],
)
async def update_ai_task_settings(
    clinic_id: UUID,
    body: AiTaskSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AiTaskSettingsRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    data = body.model_dump(exclude_unset=True)
    if "creation_mode" in data and data["creation_mode"] is not None:
        if data["creation_mode"] not in ALLOWED_CREATION_MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid creation_mode",
            )

    svc = AiTaskSettingsService(session)
    try:
        settings = await svc.update_settings(clinic_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AiTaskSettingsRead(
        ai_tasks_enabled=settings.ai_tasks_enabled,
        creation_mode=settings.creation_mode,
        allowed_task_classes=settings.allowed_task_classes or [],
        daily_clinic_limit=settings.daily_clinic_limit,
        daily_patient_limit=settings.daily_patient_limit,
        daily_doctor_limit=settings.daily_doctor_limit,
        analyzer_thresholds=settings.analyzer_thresholds,
    )

