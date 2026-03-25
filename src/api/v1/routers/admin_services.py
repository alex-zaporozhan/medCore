"""Admin services API router with ServiceDoctor links."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.card_dto import (
    ServiceCardConsumableItem,
    ServiceCardDoctorItem,
    ServiceCardResponse,
)
from src.application.dto.service_dto import (
    AdminServiceCreate,
    AdminServiceRead,
    AdminServiceUpdate,
    ServiceDoctorLink,
    ServiceRead,
)
from src.application.services.service_service import ServiceService
from src.api.v1.routers.admin_auth import get_current_admin
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.doctor import Doctor
from src.domain.entities.product import Product
from src.domain.entities.service import Service
from src.domain.entities.service_consumable import ServiceConsumable
from src.domain.entities.service_doctor import ServiceDoctor

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


@router.get(
    "/{clinic_id}/services/{service_id}/card",
    response_model=ServiceCardResponse,
)
async def get_service_card(
    clinic_id: UUID,
    service_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> ServiceCardResponse:
    """Rich service card for drawer: service, doctors, consumables, online_booking_enabled."""
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    result = await session.execute(
        select(Service).where(
            Service.id == service_id,
            Service.clinic_id == clinic_id,
            Service.deleted_at.is_(None),
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    service_dict = ServiceRead.model_validate(service).model_dump()

    # Doctors (service_doctor)
    sd_result = await session.execute(
        select(ServiceDoctor, Doctor.full_name).join(
            Doctor, Doctor.id == ServiceDoctor.doctor_id
        ).where(
            ServiceDoctor.service_id == service_id,
            Doctor.clinic_id == clinic_id,
        )
    )
    doctors = [
        ServiceCardDoctorItem(
            doctor_id=sd.doctor_id,
            doctor_name=dname or "",
            custom_price=sd.custom_price,
            is_active=sd.is_active,
        )
        for sd, dname in sd_result.all()
    ]

    # Consumables (technocard)
    sc_result = await session.execute(
        select(ServiceConsumable, Product.name).join(
            Product, Product.id == ServiceConsumable.product_id
        ).where(
            ServiceConsumable.service_id == service_id,
            ServiceConsumable.clinic_id == clinic_id,
        )
    )
    consumables = [
        ServiceCardConsumableItem(
            product_id=sc.product_id,
            product_name=pname,
            quantity_per_service=sc.quantity_per_service,
            unit=sc.unit,
        )
        for sc, pname in sc_result.all()
    ]

    return ServiceCardResponse(
        service=service_dict,
        doctors=doctors,
        consumables=consumables,
        online_booking_enabled=None,
    )


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
    response_model=None,
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

