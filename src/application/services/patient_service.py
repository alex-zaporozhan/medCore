"""Patient service."""

import logging
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.patient_dto import PatientCreate, PatientUpdate, PatientRead
from src.domain.entities.patient import Patient
from src.domain.interfaces.repositories.patient_repository import PatientRepository
from src.infrastructure.database.patient_repo_impl import PatientRepositoryImpl

logger = logging.getLogger(__name__)


class PatientService:
    """Service for patient operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.repository: PatientRepository = PatientRepositoryImpl(session)

    async def create_patient(self, data: PatientCreate) -> PatientRead:
        """Create a new patient."""
        patient = Patient(**data.model_dump())
        patient = await self.repository.create(patient)
        logger.info(
            "Patient created via service",
            extra={
                "patient_id": str(patient.id),
                "phone_last4": (patient.phone[-4:] if patient.phone else ""),
            },
        )
        return PatientRead.model_validate(patient)

    async def get_patient(self, patient_id: UUID) -> PatientRead | None:
        """Get patient by ID."""
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            return None
        return PatientRead.model_validate(patient)

    async def get_patient_by_phone(self, clinic_id: UUID, phone: str) -> PatientRead | None:
        """Get patient by phone number."""
        patient = await self.repository.get_by_phone(clinic_id, phone)
        if not patient:
            return None
        return PatientRead.model_validate(patient)

    async def get_patients(
        self,
        clinic_id: UUID | None = None,
        phone: str | None = None,
        full_name: str | None = None,
        visited_from: date | None = None,
        visited_to: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PatientRead]:
        """Get all patients with optional filters."""
        if (visited_from is not None or visited_to is not None) and clinic_id is None:
            raise ValueError("clinic_id is required when filtering by visit dates")
        if (
            visited_from is not None
            and visited_to is not None
            and visited_from > visited_to
        ):
            raise ValueError("visited_from must be on or before visited_to")
        patients = await self.repository.get_all(
            clinic_id=clinic_id,
            phone=phone,
            full_name=full_name,
            visited_from=visited_from,
            visited_to=visited_to,
            skip=skip,
            limit=limit,
        )
        return [PatientRead.model_validate(patient) for patient in patients]

    async def update_patient(self, patient_id: UUID, data: PatientUpdate) -> PatientRead | None:
        """Update patient."""
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(patient, key, value)

        patient = await self.repository.update(patient)
        logger.info("Patient updated via service", extra={"patient_id": str(patient_id)})
        return PatientRead.model_validate(patient)

    async def delete_patient(self, patient_id: UUID) -> bool:
        """Delete patient (soft delete)."""
        patient = await self.repository.get_by_id(patient_id)
        if not patient:
            return False

        await self.repository.delete(patient_id)
        logger.info("Patient deleted via service", extra={"patient_id": str(patient_id)})
        return True
