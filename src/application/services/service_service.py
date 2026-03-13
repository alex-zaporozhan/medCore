"""Service service."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.service_dto import ServiceCreate, ServiceUpdate, ServiceRead
from src.application.services.pricing_service import PricingResult, PricingService
from src.domain.entities.service import Service
from src.domain.interfaces.repositories.service_repository import ServiceRepository
from src.infrastructure.database.service_repo_impl import ServiceRepositoryImpl

logger = logging.getLogger(__name__)


class ServiceService:
    """Service for service operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self._session: AsyncSession = session
        self.repository: ServiceRepository = ServiceRepositoryImpl(session)

    @staticmethod
    def _with_pricing_fields(
        dto: ServiceRead,
        pricing: PricingResult | None = None,
    ) -> ServiceRead:
        """Populate pricing-related fields on ServiceRead."""
        base_price = dto.price
        if pricing is None:
            data = dto.model_dump()
            data["base_price"] = base_price
            data["effective_price"] = base_price
            data["has_active_discount"] = False
            data["discount_id"] = None
            data["discount_type"] = None
            data["discount_label"] = None
            return ServiceRead(**data)

        data = dto.model_dump()
        data["base_price"] = base_price
        data["effective_price"] = pricing.effective_price
        data["has_active_discount"] = pricing.discount_amount > 0
        data["discount_id"] = pricing.discount_id
        data["discount_type"] = pricing.discount_type
        data["discount_label"] = pricing.discount_name
        return ServiceRead(**data)

    async def create_service(self, data: ServiceCreate) -> ServiceRead:
        """Create a new service."""
        service = Service(**data.model_dump())
        service = await self.repository.create(service)
        logger.info("Service created via service", extra={"service_id": str(service.id)})
        dto = ServiceRead.model_validate(service)
        # Создание услуги не зависит от скидок: effective_price == base_price
        return self._with_pricing_fields(dto, pricing=None)

    async def get_service(self, service_id: UUID) -> ServiceRead | None:
        """Get service by ID."""
        service = await self.repository.get_by_id(service_id)
        if not service:
            return None
        dto = ServiceRead.model_validate(service)
        return self._with_pricing_fields(dto, pricing=None)

    async def get_services(
        self,
        clinic_id: UUID | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ServiceRead]:
        """Get all services with optional filters."""
        services = await self.repository.get_all(
            clinic_id=clinic_id, category=category, is_active=is_active, skip=skip, limit=limit
        )
        dtos = [ServiceRead.model_validate(service) for service in services]

        # На этом уровне пока не считаем скидки: base_price == price, effective_price == base_price.
        return [self._with_pricing_fields(dto, pricing=None) for dto in dtos]

    async def update_service(self, service_id: UUID, data: ServiceUpdate) -> ServiceRead | None:
        """Update service."""
        service = await self.repository.get_by_id(service_id)
        if not service:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(service, key, value)

        service = await self.repository.update(service)
        logger.info("Service updated via service", extra={"service_id": str(service_id)})
        dto = ServiceRead.model_validate(service)
        return self._with_pricing_fields(dto, pricing=None)

    async def delete_service(self, service_id: UUID) -> bool:
        """Delete service (soft delete)."""
        service = await self.repository.get_by_id(service_id)
        if not service:
            return False

        await self.repository.delete(service_id)
        logger.info("Service deleted via service", extra={"service_id": str(service_id)})
        return True
