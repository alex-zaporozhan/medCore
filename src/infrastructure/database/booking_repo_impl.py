"""Booking repository implementation."""

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.booking import Booking
from src.domain.entities.patient import Patient
from src.domain.interfaces.repositories.booking_repository import BookingRepository

logger = logging.getLogger(__name__)


class BookingRepositoryImpl(BookingRepository):
    """SQLAlchemy implementation of BookingRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(self, booking: Booking) -> Booking:
        """Create a new booking."""
        self.session.add(booking)
        await self.session.flush()
        await self.session.refresh(booking)
        logger.info(
            "Booking created",
            extra={
                "booking_id": str(booking.id),
                "clinic_id": str(booking.clinic_id),
                "doctor_id": str(booking.doctor_id),
                "patient_id": str(booking.patient_id),
            },
        )
        return booking

    async def get_by_id(self, booking_id: UUID) -> Booking | None:
        """Get booking by ID."""
        result = await self.session.execute(
            select(Booking).where(
                Booking.id == booking_id,
                Booking.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_for_doctor_on_date(
        self,
        doctor_id: UUID,
        day: date,
    ) -> list[Booking]:
        """Get all non-deleted bookings for doctor on specific date."""
        result = await self.session.execute(
            select(Booking).where(
                Booking.doctor_id == doctor_id,
                Booking.appointment_date == day,
                Booking.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def get_for_doctor_between(
        self,
        doctor_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[Booking]:
        """Get all non-deleted bookings for doctor between dates (inclusive)."""
        result = await self.session.execute(
            select(Booking).where(
                Booking.doctor_id == doctor_id,
                Booking.appointment_date >= start_date,
                Booking.appointment_date <= end_date,
                Booking.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def get_for_patient(
        self,
        patient_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        """Get bookings for specific patient ordered by date desc."""
        result = await self.session.execute(
            select(Booking)
            .where(
                Booking.patient_id == patient_id,
                Booking.deleted_at.is_(None),
            )
            .order_by(Booking.appointment_date.desc(), Booking.appointment_time.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_admin(
        self,
        clinic_id: UUID,
        doctor_id: UUID | None = None,
        date_filter: date | None = None,
        status: str | None = None,
        patient_phone: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        """Search bookings for admin with optional filters, scoped to clinic."""
        query = select(Booking).where(
            Booking.deleted_at.is_(None),
            Booking.clinic_id == clinic_id,
        )

        if doctor_id:
            query = query.where(Booking.doctor_id == doctor_id)
        if date_filter:
            query = query.where(Booking.appointment_date == date_filter)
        if status:
            query = query.where(Booking.status == status)
        if patient_phone:
            query = (
                query.join(Patient, Patient.id == Booking.patient_id)
                .where(Patient.phone.ilike(f"%{patient_phone}%"))
                .where(Patient.deleted_at.is_(None))
            )

        query = query.order_by(
            Booking.appointment_date.desc(),
            Booking.appointment_time.desc(),
        ).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, booking: Booking) -> Booking:
        """Update booking."""
        await self.session.flush()
        await self.session.refresh(booking)
        logger.info("Booking updated", extra={"booking_id": str(booking.id)})
        return booking

    async def delete(self, booking_id: UUID) -> None:
        """Soft delete booking."""
        booking = await self.get_by_id(booking_id)
        if booking:
            from src.core.datetime_utils import utc_now

            booking.deleted_at = utc_now()
            await self.session.flush()
            logger.info("Booking deleted", extra={"booking_id": str(booking_id)})

