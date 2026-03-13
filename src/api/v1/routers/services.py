"""Services API router."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.service_dto import ServiceCreate, ServiceUpdate, ServiceRead
from src.application.services.service_service import ServiceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceRead])
async def get_services(
    clinic_id: UUID | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    """Get list of services."""
    service = ServiceService(session)
    services = await service.get_services(
        clinic_id=clinic_id, category=category, is_active=is_active, skip=skip, limit=limit
    )
    return services


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service(
    service_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get service by ID."""
    service_obj = ServiceService(session)
    service = await service_obj.get_service(service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(
    data: ServiceCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new service."""
    service_obj = ServiceService(session)
    service = await service_obj.create_service(data)
    logger.info("Service created via API", extra={"service_id": str(service.id)})
    return service


@router.put("/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: UUID,
    data: ServiceUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update service."""
    service_obj = ServiceService(session)
    service = await service_obj.update_service(service_id, data)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    logger.info("Service updated via API", extra={"service_id": str(service_id)})
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete service (soft delete)."""
    service_obj = ServiceService(session)
    deleted = await service_obj.delete_service(service_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    logger.info("Service deleted via API", extra={"service_id": str(service_id)})
