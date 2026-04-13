"""Public commerce vitrine: active nomenclature for patient PWA when clinic enables storefront."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.core.config import settings
from src.core.request_ip import client_ip_for_public_rate_limit
from src.domain.entities.clinic import Clinic
from src.domain.entities.commerce_nomenclature_item import CommerceNomenclatureItem
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter

router = APIRouter(prefix="/public/clinics", tags=["public-commerce"])


class PublicCommerceVitrineItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    sku: str | None
    unit: str


class PublicCommerceVitrineResponse(BaseModel):
    enabled: bool
    section_title: str | None
    section_subtitle: str | None
    items: list[PublicCommerceVitrineItem]


async def _enforce_public_commerce_vitrine_rate_limit(
    request: Request,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    if settings.rate_public_commerce_vitrine_ip_limit <= 0:
        return
    trace_id = getattr(request.state, "trace_id", None)
    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:public_commerce_vitrine:ip:{client_ip}",
            limit=settings.rate_public_commerce_vitrine_ip_limit,
            window=settings.rate_public_commerce_vitrine_ip_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": "Слишком много запросов к витрине. Попробуйте позже.",
                "trace_id": trace_id,
            },
        ) from None


@router.get("/{clinic_id}/commerce/vitrine", response_model=PublicCommerceVitrineResponse)
async def get_public_commerce_vitrine(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    _rate: None = Depends(_enforce_public_commerce_vitrine_rate_limit),
) -> PublicCommerceVitrineResponse:
    """
    Read-only витрина для PWA: только если клиника включила `patient_store_visible`.
    Без цен и остатков (MVP карточек); заказ/оплата — отдельные эпики.
    """
    clinic_res = await session.execute(
        select(Clinic).where(Clinic.id == clinic_id, Clinic.deleted_at.is_(None))
    )
    clinic = clinic_res.scalar_one_or_none()
    if clinic is None or not getattr(clinic, "patient_store_visible", False):
        return PublicCommerceVitrineResponse(
            enabled=False,
            section_title=None,
            section_subtitle=None,
            items=[],
        )

    nom_res = await session.execute(
        select(CommerceNomenclatureItem)
        .where(
            CommerceNomenclatureItem.clinic_id == clinic_id,
            CommerceNomenclatureItem.is_active.is_(True),
        )
        .order_by(CommerceNomenclatureItem.name.asc())
        .limit(200)
    )
    rows = list(nom_res.scalars().all())
    items = [
        PublicCommerceVitrineItem(
            id=r.id,
            name=r.name,
            sku=r.sku,
            unit=r.unit,
        )
        for r in rows
    ]
    return PublicCommerceVitrineResponse(
        enabled=True,
        section_title=getattr(clinic, "patient_store_title", None),
        section_subtitle=getattr(clinic, "patient_store_subtitle", None),
        items=items,
    )
