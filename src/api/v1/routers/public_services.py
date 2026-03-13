"""Public API: services by clinic for patient flow."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.services.pricing_service import PricingService
from src.domain.entities.service import Service
from src.domain.entities.service_doctor import ServiceDoctor

router = APIRouter(prefix="/public/clinics", tags=["public"])


@router.get("/{clinic_id}/services")
async def get_public_clinic_services(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """List active services for clinic (online booking). Returns services with doctor_ids from ServiceDoctor."""
    result = await session.execute(
        select(Service).where(
            Service.clinic_id == clinic_id,
            Service.deleted_at.is_(None),
            Service.is_active.is_(True),
        ).order_by(Service.name)
    )
    services = list(result.scalars().all())
    if not services:
        return []

    service_ids = [s.id for s in services]
    links_result = await session.execute(
        select(ServiceDoctor.service_id, ServiceDoctor.doctor_id).where(
            ServiceDoctor.service_id.in_(service_ids),
            ServiceDoctor.is_active.is_(True),
        )
    )
    links = list(links_result.all())
    by_service: dict[UUID, list[UUID]] = {}
    for sid, did in links:
        by_service.setdefault(sid, []).append(did)

    pricing_svc = PricingService(session)

    response: list[dict] = []
    for s in services:
        pricing = await pricing_svc.compute_effective_price(
            clinic_id=s.clinic_id,
            service_id=s.id,
            doctor_id=None,
            patient_id=None,
            on_date=date.today(),
            base_price=s.price,
        )
        response.append(
            {
                "id": str(s.id),
                "clinic_id": str(s.clinic_id),
                "name": s.name,
                "category": s.category,
                "description": s.description,
                "price": str(s.price),
                "duration_minutes": s.duration_minutes,
                "is_active": s.is_active,
                "doctor_ids": [str(d) for d in by_service.get(s.id, [])],
                "base_price": str(pricing.base_price),
                "effective_price": str(pricing.effective_price),
                "has_active_discount": pricing.discount_amount > 0,
                "discount_id": str(pricing.discount_id) if pricing.discount_id else None,
                "discount_type": pricing.discount_type,
                "discount_label": pricing.discount_name,
            }
        )

    return response
