"""Doctor service."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.doctor_dto import DoctorCreate, DoctorUpdate, DoctorRead
from src.domain.entities.doctor import Doctor
from src.domain.interfaces.repositories.doctor_repository import DoctorRepository
from src.infrastructure.database.doctor_repo_impl import DoctorRepositoryImpl

logger = logging.getLogger(__name__)


class DoctorService:
    """Service for doctor operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.repository: DoctorRepository = DoctorRepositoryImpl(session)

    async def create_doctor(self, data: DoctorCreate) -> DoctorRead:
        """Create a new doctor."""
        doctor = Doctor(**data.model_dump())
        doctor = await self.repository.create(doctor)
        logger.info("Doctor created via service", extra={"doctor_id": str(doctor.id)})
        return DoctorRead.model_validate(doctor)

    async def get_doctor(self, doctor_id: UUID) -> DoctorRead | None:
        """Get doctor by ID."""
        doctor = await self.repository.get_by_id(doctor_id)
        if not doctor:
            return None
        return DoctorRead.model_validate(doctor)

    async def get_doctors(
        self, clinic_id: UUID | None = None, is_active: bool | None = None, skip: int = 0, limit: int = 100
    ) -> list[DoctorRead]:
        """Get all doctors with optional filters."""
        doctors = await self.repository.get_all(clinic_id=clinic_id, is_active=is_active, skip=skip, limit=limit)
        return [DoctorRead.model_validate(doctor) for doctor in doctors]

    async def update_doctor(self, doctor_id: UUID, data: DoctorUpdate) -> DoctorRead | None:
        """Update doctor."""
        doctor = await self.repository.get_by_id(doctor_id)
        if not doctor:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(doctor, key, value)

        doctor = await self.repository.update(doctor)
        logger.info("Doctor updated via service", extra={"doctor_id": str(doctor_id)})
        return DoctorRead.model_validate(doctor)

    async def delete_doctor(self, doctor_id: UUID) -> bool:
        """Delete doctor (soft delete)."""
        doctor = await self.repository.get_by_id(doctor_id)
        if not doctor:
            return False

        await self.repository.delete(doctor_id)
        logger.info("Doctor deleted via service", extra={"doctor_id": str(doctor_id)})
        return True
