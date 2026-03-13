"""Patients API router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_default_clinic_id, get_session
from src.application.dto.patient_dto import PatientCreate, PatientUpdate, PatientRead
from src.application.services.patient_service import PatientService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientRead])
async def get_patients(
    clinic_id: UUID | None = None,
    phone: str | None = None,
    full_name: str | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    """Get list of patients."""
    service = PatientService(session)
    patients = await service.get_patients(
        clinic_id=clinic_id, phone=phone, full_name=full_name, skip=skip, limit=limit
    )
    return patients


@router.get("/{patient_id}", response_model=PatientRead)
async def get_patient(
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get patient by ID."""
    service = PatientService(session)
    patient = await service.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
async def create_patient(
    data: PatientCreate,
    session: AsyncSession = Depends(get_session),
    default_clinic_id: UUID = Depends(get_default_clinic_id),
):
    """Create a new patient. Uses default clinic when clinic_id is not provided."""
    if data.clinic_id is None:
        data = data.model_copy(update={"clinic_id": default_clinic_id})
    service = PatientService(session)
    patient = await service.create_patient(data)
    masked_phone = f"...{patient.phone[-4:]}" if patient.phone and len(patient.phone) >= 4 else None
    logger.info(
        "Patient created via API",
        extra={"patient_id": str(patient.id), "phone_last4": masked_phone},
    )
    return patient


@router.put("/{patient_id}", response_model=PatientRead)
async def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update patient."""
    service = PatientService(session)
    patient = await service.update_patient(patient_id, data)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    logger.info("Patient updated via API", extra={"patient_id": str(patient_id)})
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete patient (soft delete)."""
    service = PatientService(session)
    deleted = await service.delete_patient(patient_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    logger.info("Patient deleted via API", extra={"patient_id": str(patient_id)})
