"""Patients API router."""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_default_clinic_id, get_session, require_permissions
from src.application.dto.patient_dto import PatientCreate, PatientUpdate, PatientRead
from src.application.services.patient_service import PatientService
from sqlalchemy import select

from src.api.v1.multitenancy_http import clinic_forbidden_admin_detail
from src.application.multitenancy import (
    assert_entity_belongs_to_clinic,
    ClinicForbiddenError,
    EntityClinicMismatchError,
)
from src.application.domain_error_observability import record_domain_error
from src.domain.entities.patient import Patient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["patients"])


def _guard_patient_same_clinic(admin: AdminContext, entity: Patient) -> None:
    cid = admin.clinic_id
    try:
        assert_entity_belongs_to_clinic(entity, cid, entity_label="patient")
    except EntityClinicMismatchError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found") from None
    except ClinicForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=clinic_forbidden_admin_detail(exc, None),
        ) from exc


@router.get("", response_model=list[PatientRead])
async def get_patients(
    phone: str | None = None,
    full_name: str | None = None,
    visited_from: date | None = None,
    visited_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("patients.pii.read")),
):
    """Список пациентов: RBAC ``patients.pii.read``; клиника из JWT (врачи/без права — 403)."""
    service = PatientService(session)
    try:
        patients = await service.get_patients(
            clinic_id=admin_ctx.clinic_id,
            phone=phone,
            full_name=full_name,
            visited_from=visited_from,
            visited_to=visited_to,
            skip=skip,
            limit=limit,
        )
    except ValueError as exc:
        record_domain_error(domain="patients", code="validation_error", clinic_id=admin_ctx.clinic_id)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return patients


@router.get("/{patient_id}", response_model=PatientRead)
async def get_patient(
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("patients.pii.read")),
):
    """Get patient by ID (RBAC ``patients.pii.read``; та же клиника, что в JWT)."""
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.deleted_at.is_(None))
    )
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    _guard_patient_same_clinic(admin_ctx, entity)
    return PatientRead.model_validate(entity)


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
    admin_ctx: AdminContext = Depends(require_permissions("patients.pii.read")),
):
    """Update patient (RBAC ``patients.pii.read``; та же клиника)."""
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.deleted_at.is_(None))
    )
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    _guard_patient_same_clinic(admin_ctx, entity)
    service = PatientService(session)
    patient = await service.update_patient(patient_id, data)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    logger.info("Patient updated via API", extra={"patient_id": str(patient_id)})
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_patient(
    patient_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin_ctx: AdminContext = Depends(require_permissions("patients.pii.read")),
):
    """Delete patient (soft delete; RBAC ``patients.pii.read``; та же клиника)."""
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.deleted_at.is_(None))
    )
    entity = result.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    _guard_patient_same_clinic(admin_ctx, entity)
    service = PatientService(session)
    deleted = await service.delete_patient(patient_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    logger.info("Patient deleted via API", extra={"patient_id": str(patient_id)})
