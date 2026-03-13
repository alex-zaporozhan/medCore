"""Patient repository interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.patient import Patient


class PatientRepository(ABC):
    """Repository interface for Patient entity."""

    @abstractmethod
    async def create(self, patient: Patient) -> Patient:
        """Create a new patient."""
        ...

    @abstractmethod
    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        """Get patient by ID."""
        ...

    @abstractmethod
    async def get_by_phone(self, clinic_id: UUID, phone: str) -> Patient | None:
        """Get patient by phone number."""
        ...

    @abstractmethod
    async def get_all(
        self,
        clinic_id: UUID | None = None,
        phone: str | None = None,
        full_name: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        """Get all patients with optional filters."""
        ...

    @abstractmethod
    async def update(self, patient: Patient) -> Patient:
        """Update patient."""
        ...

    @abstractmethod
    async def delete(self, patient_id: UUID) -> None:
        """Soft delete patient."""
        ...
