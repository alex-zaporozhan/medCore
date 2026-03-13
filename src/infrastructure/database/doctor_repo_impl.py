"""Doctor repository implementation."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.doctor import Doctor
from src.domain.interfaces.repositories.doctor_repository import DoctorRepository

logger = logging.getLogger(__name__)


class DoctorRepositoryImpl(DoctorRepository):
    """SQLAlchemy implementation of DoctorRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(self, doctor: Doctor) -> Doctor:
        """Create a new doctor."""
        self.session.add(doctor)
        await self.session.flush()
        await self.session.refresh(doctor)
        logger.info(
            "Doctor created",
            extra={"doctor_id": str(doctor.id), "clinic_id": str(doctor.clinic_id)},
        )
        return doctor

    async def get_by_id(self, doctor_id: UUID) -> Doctor | None:
        """Get doctor by ID."""
        result = await self.session.execute(
            select(Doctor).where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, clinic_id: UUID | None = None, is_active: bool | None = None, skip: int = 0, limit: int = 100
    ) -> list[Doctor]:
        """Get all doctors with optional filters."""
        query = select(Doctor).where(Doctor.deleted_at.is_(None))

        if clinic_id:
            query = query.where(Doctor.clinic_id == clinic_id)
        if is_active is not None:
            query = query.where(Doctor.is_active == is_active)

        query = query.offset(skip).limit(limit).order_by(Doctor.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, doctor: Doctor) -> Doctor:
        """Update doctor."""
        await self.session.flush()
        await self.session.refresh(doctor)
        logger.info("Doctor updated", extra={"doctor_id": str(doctor.id)})
        return doctor

    async def delete(self, doctor_id: UUID) -> None:
        """Soft delete doctor."""
        doctor = await self.get_by_id(doctor_id)
        if doctor:
            from src.core.datetime_utils import utc_now

            doctor.deleted_at = utc_now()
            await self.session.flush()
            logger.info("Doctor deleted", extra={"doctor_id": str(doctor_id)})
