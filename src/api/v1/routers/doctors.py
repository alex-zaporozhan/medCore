"""Doctors API router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_default_clinic_id, get_session
from src.application.dto.doctor_dto import DoctorCreate, DoctorUpdate, DoctorRead
from src.application.services.doctor_service import DoctorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("", response_model=list[DoctorRead])
async def get_doctors(
    clinic_id: UUID | None = None,
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    """Get list of doctors."""
    service = DoctorService(session)
    doctors = await service.get_doctors(clinic_id=clinic_id, is_active=is_active, skip=skip, limit=limit)
    return doctors


@router.get("/{doctor_id}", response_model=DoctorRead)
async def get_doctor(
    doctor_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get doctor by ID."""
    service = DoctorService(session)
    doctor = await service.get_doctor(doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor


@router.post("", response_model=DoctorRead, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    data: DoctorCreate,
    session: AsyncSession = Depends(get_session),
    default_clinic_id: UUID = Depends(get_default_clinic_id),
):
    """Create a new doctor. Uses default clinic when clinic_id is not provided."""
    if data.clinic_id is None:
        data = data.model_copy(update={"clinic_id": default_clinic_id})
    service = DoctorService(session)
    doctor = await service.create_doctor(data)
    logger.info("Doctor created via API", extra={"doctor_id": str(doctor.id)})
    return doctor


@router.put("/{doctor_id}", response_model=DoctorRead)
async def update_doctor(
    doctor_id: UUID,
    data: DoctorUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update doctor."""
    service = DoctorService(session)
    doctor = await service.update_doctor(doctor_id, data)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    logger.info("Doctor updated via API", extra={"doctor_id": str(doctor_id)})
    return doctor


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(
    doctor_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete doctor (soft delete)."""
    service = DoctorService(session)
    deleted = await service.delete_doctor(doctor_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    logger.info("Doctor deleted via API", extra={"doctor_id": str(doctor_id)})
