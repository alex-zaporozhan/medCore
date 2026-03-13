"""Clinic repository interface."""

from abc import ABC, abstractmethod
from typing import Sequence
from uuid import UUID

from src.domain.entities.clinic import Clinic


class ClinicRepository(ABC):
    """Abstract repository interface for Clinic entity."""

    @abstractmethod
    async def create(self, clinic: Clinic) -> Clinic:
        """Create a new clinic."""

    @abstractmethod
    async def get_by_id(self, clinic_id: UUID) -> Clinic | None:
        """Get clinic by ID."""

    @abstractmethod
    async def get_all(self, include_deleted: bool = False) -> Sequence[Clinic]:
        """Get all clinics."""

    @abstractmethod
    async def update(self, clinic: Clinic) -> Clinic:
        """Update clinic."""

    @abstractmethod
    async def delete(self, clinic_id: UUID) -> None:
        """Soft delete clinic."""

