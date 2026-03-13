"""Booking repository interface."""

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from src.domain.entities.booking import Booking


class BookingRepository(ABC):
    """Repository interface for Booking entity."""

    @abstractmethod
    async def create(self, booking: Booking) -> Booking:
        """Create a new booking."""
        ...

    @abstractmethod
    async def get_by_id(self, booking_id: UUID) -> Booking | None:
        """Get booking by ID."""
        ...

    @abstractmethod
    async def get_for_doctor_on_date(
        self,
        doctor_id: UUID,
        day: date,
    ) -> list[Booking]:
        """Get all non-deleted bookings for doctor on specific date."""
        ...

    @abstractmethod
    async def get_for_doctor_between(
        self,
        doctor_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[Booking]:
        """Get all non-deleted bookings for doctor between dates (inclusive)."""
        ...

    @abstractmethod
    async def get_for_patient(
        self,
        patient_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Booking]:
        """Get bookings for specific patient ordered by date desc."""
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def update(self, booking: Booking) -> Booking:
        """Update booking."""
        ...

    @abstractmethod
    async def delete(self, booking_id: UUID) -> None:
        """Soft delete booking."""
        ...

