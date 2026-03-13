"""Admin notification policy."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.notification_policy_dto import (
    ClinicNotificationPolicyRead,
    ClinicNotificationPolicyUpdate,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic

router = APIRouter(prefix="/admin/clinics", tags=["admin-notification-policy"])


@router.get("/{clinic_id}/notification-policy", response_model=ClinicNotificationPolicyRead)
async def get_notification_policy(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> ClinicNotificationPolicyRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    result = await session.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return ClinicNotificationPolicyRead(
        allow_patient_disable_discount_notifications=clinic.allow_patient_disable_discount_notifications,
        allow_patient_disable_reminders=clinic.allow_patient_disable_reminders,
        allow_patient_disable_all_notifications=clinic.allow_patient_disable_all_notifications,
    )


@router.put("/{clinic_id}/notification-policy", response_model=ClinicNotificationPolicyRead)
async def update_notification_policy(
    clinic_id: UUID,
    data: ClinicNotificationPolicyUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> ClinicNotificationPolicyRead:
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    result = await session.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    if data.allow_patient_disable_discount_notifications is not None:
        clinic.allow_patient_disable_discount_notifications = data.allow_patient_disable_discount_notifications
    if data.allow_patient_disable_reminders is not None:
        clinic.allow_patient_disable_reminders = data.allow_patient_disable_reminders
    if data.allow_patient_disable_all_notifications is not None:
        clinic.allow_patient_disable_all_notifications = data.allow_patient_disable_all_notifications
    await session.commit()
    await session.refresh(clinic)
    return ClinicNotificationPolicyRead(
        allow_patient_disable_discount_notifications=clinic.allow_patient_disable_discount_notifications,
        allow_patient_disable_reminders=clinic.allow_patient_disable_reminders,
        allow_patient_disable_all_notifications=clinic.allow_patient_disable_all_notifications,
    )
