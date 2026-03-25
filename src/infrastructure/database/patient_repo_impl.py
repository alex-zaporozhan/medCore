"""Patient repository implementation."""

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.patient import Patient
from src.domain.interfaces.repositories.patient_repository import PatientRepository

logger = logging.getLogger(__name__)


class PatientRepositoryImpl(PatientRepository):
    """SQLAlchemy implementation of PatientRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(self, patient: Patient) -> Patient:
        """Create a new patient."""
        self.session.add(patient)
        await self.session.flush()
        await self.session.refresh(patient)
        logger.info(
            "Patient created",
            extra={
                "patient_id": str(patient.id),
                "clinic_id": str(patient.clinic_id),
                "phone_last4": (patient.phone[-4:] if patient.phone else ""),
            },
        )
        return patient

    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        """Get patient by ID."""
        result = await self.session.execute(
            select(Patient).where(Patient.id == patient_id, Patient.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, clinic_id: UUID, phone: str) -> Patient | None:
        """Get patient by phone number."""
        result = await self.session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic_id,
                Patient.phone == phone,
                Patient.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        clinic_id: UUID | None = None,
        phone: str | None = None,
        full_name: str | None = None,
        visited_from: date | None = None,
        visited_to: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        """Get all patients with optional filters."""
        query = select(Patient).where(Patient.deleted_at.is_(None))

        if clinic_id:
            query = query.where(Patient.clinic_id == clinic_id)
        if phone:
            query = query.where(Patient.phone.ilike(f"%{phone}%"))
        if full_name:
            query = query.where(Patient.full_name.ilike(f"%{full_name}%"))

        if visited_from is not None or visited_to is not None:
            cancelled = (
                BookingStatus.CANCELLED.value,
                BookingStatus.CANCELED_BY_PATIENT.value,
                BookingStatus.CANCELED_BY_CLINIC.value,
            )
            visit_parts = [
                Booking.patient_id == Patient.id,
                Booking.clinic_id == Patient.clinic_id,
                Booking.deleted_at.is_(None),
                Booking.status.notin_(cancelled),
            ]
            if visited_from is not None:
                visit_parts.append(Booking.appointment_date >= visited_from)
            if visited_to is not None:
                visit_parts.append(Booking.appointment_date <= visited_to)
            query = query.where(exists().where(and_(*visit_parts)))

        query = query.offset(skip).limit(limit).order_by(Patient.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, patient: Patient) -> Patient:
        """Update patient."""
        await self.session.flush()
        await self.session.refresh(patient)
        logger.info("Patient updated", extra={"patient_id": str(patient.id)})
        return patient

    async def delete(self, patient_id: UUID) -> None:
        """Soft delete patient."""
        patient = await self.get_by_id(patient_id)
        if patient:
            from src.core.datetime_utils import utc_now

            patient.deleted_at = utc_now()
            await self.session.flush()
            logger.info("Patient deleted", extra={"patient_id": str(patient_id)})
