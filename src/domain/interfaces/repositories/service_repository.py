"""Service repository interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.service import Service


class ServiceRepository(ABC):
    """Repository interface for Service entity."""

    @abstractmethod
    async def create(self, service: Service) -> Service:
        """Create a new service."""
        ...

    @abstractmethod
    async def get_by_id(self, service_id: UUID) -> Service | None:
        """Get service by ID."""
        ...

    @abstractmethod
    async def get_all(
        self,
        clinic_id: UUID | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Service]:
        """Get all services with optional filters."""
        ...

    @abstractmethod
    async def update(self, service: Service) -> Service:
        """Update service."""
        ...

    @abstractmethod
    async def delete(self, service_id: UUID) -> None:
        """Soft delete service."""
        ...
