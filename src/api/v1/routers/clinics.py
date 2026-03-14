"""Clinics API router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.clinic_dto import ClinicCreate, ClinicRead, ClinicUpdate
from src.application.services.clinic_service import ClinicService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clinics", tags=["clinics"])


@router.get("", response_model=list[ClinicRead])
async def get_clinics(
    include_deleted: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> list[ClinicRead]:
    """Get list of clinics."""
    service = ClinicService(session)
    clinics = await service.get_clinics(include_deleted=include_deleted)
    return clinics


@router.get("/{clinic_id}", response_model=ClinicRead)
async def get_clinic(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ClinicRead:
    """Get clinic by ID."""
    service = ClinicService(session)
    clinic = await service.get_clinic(clinic_id)
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return clinic


@router.post("", response_model=ClinicRead, status_code=status.HTTP_201_CREATED)
async def create_clinic(
    data: ClinicCreate,
    session: AsyncSession = Depends(get_session),
) -> ClinicRead:
    """Create a new clinic."""
    service = ClinicService(session)
    clinic = await service.create_clinic(data)
    logger.info("Clinic created via API", extra={"clinic_id": str(clinic.id)})
    return clinic


@router.put("/{clinic_id}", response_model=ClinicRead)
async def update_clinic(
    clinic_id: UUID,
    data: ClinicUpdate,
    session: AsyncSession = Depends(get_session),
) -> ClinicRead:
    """Update clinic."""
    service = ClinicService(session)
    clinic = await service.update_clinic(clinic_id, data)
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    logger.info("Clinic updated via API", extra={"clinic_id": str(clinic_id)})
    return clinic


@router.delete("/{clinic_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_clinic(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Soft delete clinic."""
    service = ClinicService(session)
    deleted = await service.delete_clinic(clinic_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    logger.info("Clinic deleted via API", extra={"clinic_id": str(clinic_id)})

