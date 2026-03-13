"""Admin services API router with ServiceDoctor links."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.service_dto import (
    AdminServiceCreate,
    AdminServiceRead,
    AdminServiceUpdate,
    ServiceDoctorLink,
    ServiceRead,
)
from src.application.services.pricing_service import PricingService
from src.application.services.service_service import ServiceService
from src.domain.entities.service_doctor import ServiceDoctor
from src.api.v1.routers.admin_auth import get_current_admin
from src.domain.entities.admin_user import AdminUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/clinics", tags=["admin-services"])


async def _get_service_doctors_map(
    session: AsyncSession, service_ids: list[UUID]
) -> dict[UUID, list[ServiceDoctorLink]]:
    if not service_ids:
        return {}

    result = await session.execute(
        select(ServiceDoctor).where(ServiceDoctor.service_id.in_(service_ids))
    )
    rows = list(result.scalars().all())
    mapping: dict[UUID, list[ServiceDoctorLink]] = {}
    for row in rows:
        link = ServiceDoctorLink(
            doctor_id=row.doctor_id,
            custom_price=row.custom_price,
            is_active=row.is_active,
        )
        mapping.setdefault(row.service_id, []).append(link)
    return mapping


@router.get(
    "/{clinic_id}/services",
    response_model=list[AdminServiceRead],
)
async def get_clinic_services(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[AdminServiceRead]:
    """Get services for clinic with linked doctors."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service_service = ServiceService(session)
    services = await service_service.get_services(
        clinic_id=clinic_id,
        category=None,
        is_active=None,
        skip=0,
        limit=1000,
    )
    ids = [s.id for s in services]
    pricing_svc = PricingService(session)
    # Для админского списка считаем только базовую цену: скидки можно добавить позднее при необходимости.
    # Здесь effective_price == base_price (price), чтобы не ломать текущие ожидания.
    doctors_map = await _get_service_doctors_map(session, ids)
    return [
        AdminServiceRead(
            service=ServiceRead.model_validate(s),
            doctors=doctors_map.get(s.id, []),
        )
        for s in services
    ]


@router.post(
    "/{clinic_id}/services",
    response_model=AdminServiceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_clinic_service(
    clinic_id: UUID,
    payload: AdminServiceCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminServiceRead:
    """Create service for clinic with doctor links."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    service_service = ServiceService(session)
    service_data = payload.service.model_copy(update={"clinic_id": clinic_id})
    service = await service_service.create_service(service_data)

    for link in payload.doctors:
        session.add(
            ServiceDoctor(
                service_id=service.id,
                doctor_id=link.doctor_id,
                custom_price=link.custom_price,
                is_active=link.is_active,
            )
        )
    await session.commit()

    doctors_map = await _get_service_doctors_map(session, [service.id])
    return AdminServiceRead(
        service=ServiceRead.model_validate(service),
        doctors=doctors_map.get(service.id, []),
    )


@router.put(
    "/{clinic_id}/services/{service_id}",
    response_model=AdminServiceRead,
)
async def update_clinic_service(
    clinic_id: UUID,
    service_id: UUID,
    payload: AdminServiceUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminServiceRead:
    """Update clinic service and doctor links."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    service_service = ServiceService(session)

    service = await service_service.get_service(service_id)
    if not service or service.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    updated = await service_service.update_service(service_id, payload.service)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    # Replace all existing links with new set
    await session.execute(
        delete(ServiceDoctor).where(ServiceDoctor.service_id == service_id)
    )
    for link in payload.doctors:
        session.add(
            ServiceDoctor(
                service_id=service_id,
                doctor_id=link.doctor_id,
                custom_price=link.custom_price,
                is_active=link.is_active,
            )
        )
    await session.commit()

    doctors_map = await _get_service_doctors_map(session, [service_id])
    return AdminServiceRead(
        service=ServiceRead.model_validate(updated),
        doctors=doctors_map.get(service_id, []),
    )


@router.delete(
    "/{clinic_id}/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_clinic_service(
    clinic_id: UUID,
    service_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    """Delete clinic service and all doctor links."""
    if clinic_id != current_admin.clinic_id:
        # Hide presence of services in other clinics
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    service_service = ServiceService(session)
    service = await service_service.get_service(service_id)
    if not service or service.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    await session.execute(
        delete(ServiceDoctor).where(ServiceDoctor.service_id == service_id)
    )
    deleted = await service_service.delete_service(service_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

