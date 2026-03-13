"""Service repository implementation."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.service import Service
from src.domain.interfaces.repositories.service_repository import ServiceRepository

logger = logging.getLogger(__name__)


class ServiceRepositoryImpl(ServiceRepository):
    """SQLAlchemy implementation of ServiceRepository."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(self, service: Service) -> Service:
        """Create a new service."""
        self.session.add(service)
        await self.session.flush()
        await self.session.refresh(service)
        logger.info(
            "Service created",
            extra={"service_id": str(service.id), "clinic_id": str(service.clinic_id)},
        )
        return service

    async def get_by_id(self, service_id: UUID) -> Service | None:
        """Get service by ID."""
        result = await self.session.execute(
            select(Service).where(Service.id == service_id, Service.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        clinic_id: UUID | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Service]:
        """Get all services with optional filters."""
        query = select(Service).where(Service.deleted_at.is_(None))

        if clinic_id:
            query = query.where(Service.clinic_id == clinic_id)
        if category:
            query = query.where(Service.category == category)
        if is_active is not None:
            query = query.where(Service.is_active == is_active)

        query = query.offset(skip).limit(limit).order_by(Service.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, service: Service) -> Service:
        """Update service."""
        await self.session.flush()
        await self.session.refresh(service)
        logger.info("Service updated", extra={"service_id": str(service.id)})
        return service

    async def delete(self, service_id: UUID) -> None:
        """Soft delete service."""
        service = await self.get_by_id(service_id)
        if service:
            from src.core.datetime_utils import utc_now

            service.deleted_at = utc_now()
            await self.session.flush()
            logger.info("Service deleted", extra={"service_id": str(service_id)})
