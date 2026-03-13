"""Doctor repository interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.doctor import Doctor


class DoctorRepository(ABC):
    """Repository interface for Doctor entity."""

    @abstractmethod
    async def create(self, doctor: Doctor) -> Doctor:
        """Create a new doctor."""
        ...

    @abstractmethod
    async def get_by_id(self, doctor_id: UUID) -> Doctor | None:
        """Get doctor by ID."""
        ...

    @abstractmethod
    async def get_all(
        self, clinic_id: UUID | None = None, is_active: bool | None = None, skip: int = 0, limit: int = 100
    ) -> list[Doctor]:
        """Get all doctors with optional filters."""
        ...

    @abstractmethod
    async def update(self, doctor: Doctor) -> Doctor:
        """Update doctor."""
        ...

    @abstractmethod
    async def delete(self, doctor_id: UUID) -> None:
        """Soft delete doctor."""
        ...
