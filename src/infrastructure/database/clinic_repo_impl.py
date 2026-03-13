"""Clinic repository implementation."""

import logging
from src.core.datetime_utils import utc_now
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.clinic import Clinic
from src.domain.interfaces.repositories.clinic_repository import ClinicRepository

logger = logging.getLogger(__name__)


class ClinicRepositoryImpl(ClinicRepository):
    """SQLAlchemy implementation of ClinicRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session

    async def create(self, clinic: Clinic) -> Clinic:
        """Create a new clinic."""
        self.session.add(clinic)
        await self.session.flush()
        await self.session.refresh(clinic)
        logger.info("Clinic created", extra={"clinic_id": str(clinic.id)})
        return clinic

    async def get_by_id(self, clinic_id: UUID) -> Clinic | None:
        """Get clinic by ID (excluding soft-deleted)."""
        result = await self.session.execute(
            select(Clinic).where(Clinic.id == clinic_id, Clinic.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_all(self, include_deleted: bool = False) -> Sequence[Clinic]:
        """Get all clinics."""
        query = select(Clinic)
        if not include_deleted:
            query = query.where(Clinic.deleted_at.is_(None))
        query = query.order_by(Clinic.created_at.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, clinic: Clinic) -> Clinic:
        """Update clinic."""
        await self.session.flush()
        await self.session.refresh(clinic)
        logger.info("Clinic updated", extra={"clinic_id": str(clinic.id)})
        return clinic

    async def delete(self, clinic_id: UUID) -> None:
        """Soft delete clinic."""
        clinic = await self.get_by_id(clinic_id)
        if clinic is None:
            return
        clinic.deleted_at = utc_now()
        await self.session.flush()
        logger.info("Clinic deleted", extra={"clinic_id": str(clinic_id)})

