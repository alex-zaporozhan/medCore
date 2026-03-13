"""Patient notification settings: GET/PUT (respect clinic policy)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_current_patient, get_default_clinic_id, get_session
from src.application.dto.notification_policy_dto import (
    PatientNotificationSettingsRead,
    PatientNotificationSettingsUpdate,
)
from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient

router = APIRouter(prefix="/patient", tags=["patient-notification-settings"])


@router.get("/notification-settings", response_model=PatientNotificationSettingsRead)
async def get_patient_notification_settings(
    patient_id: UUID | None = Query(
        default=None,
        description="Patient ID (ignored; current patient is taken from auth token)",
    ),
    session: AsyncSession = Depends(get_session),
    clinic_id: UUID = Depends(get_default_clinic_id),
    current_patient: Patient = Depends(get_current_patient),
) -> PatientNotificationSettingsRead:
    result = await session.execute(
        select(Patient).where(
            Patient.id == current_patient.id,
            Patient.clinic_id == clinic_id,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return PatientNotificationSettingsRead(
        disable_discount_notifications=patient.disable_discount_notifications,
        disable_reminders=patient.disable_reminders,
        disable_all_notifications=patient.disable_all_notifications,
    )


@router.put("/notification-settings", response_model=PatientNotificationSettingsRead)
async def update_patient_notification_settings(
    data: PatientNotificationSettingsUpdate,
    patient_id: UUID | None = Query(
        default=None,
        description="Patient ID (ignored; current patient is taken from auth token)",
    ),
    session: AsyncSession = Depends(get_session),
    clinic_id: UUID = Depends(get_default_clinic_id),
    current_patient: Patient = Depends(get_current_patient),
) -> PatientNotificationSettingsRead:
    result = await session.execute(
        select(Patient).where(
            Patient.id == current_patient.id,
            Patient.clinic_id == clinic_id,
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    clinic_result = await session.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = clinic_result.scalar_one_or_none()
    if clinic:
        if data.disable_discount_notifications is not None and not clinic.allow_patient_disable_discount_notifications:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Клиника не разрешает отключать оповещения о скидках. Обратитесь в клинику.",
            )
        if data.disable_reminders is not None and not clinic.allow_patient_disable_reminders:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Клиника не разрешает отключать напоминания о приёме. Обратитесь в клинику.",
            )
        if data.disable_all_notifications is not None and not clinic.allow_patient_disable_all_notifications:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Клиника не разрешает отключать все уведомления. Обратитесь в клинику.",
            )

    if data.disable_discount_notifications is not None:
        patient.disable_discount_notifications = data.disable_discount_notifications
    if data.disable_reminders is not None:
        patient.disable_reminders = data.disable_reminders
    if data.disable_all_notifications is not None:
        patient.disable_all_notifications = data.disable_all_notifications
    await session.commit()
    await session.refresh(patient)
    return PatientNotificationSettingsRead(
        disable_discount_notifications=patient.disable_discount_notifications,
        disable_reminders=patient.disable_reminders,
        disable_all_notifications=patient.disable_all_notifications,
    )
