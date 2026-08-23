"""Public read-only SaaS catalog (landing / signup)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.platform_billing_dto import PlatformCatalogOptionPublic, PlatformCatalogPlanPublic
from src.core.config import settings
from src.core.request_ip import client_ip_for_public_rate_limit
from src.domain.entities.platform_catalog_option import PlatformCatalogOption
from src.domain.entities.platform_catalog_plan import PlatformCatalogPlan
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter

router = APIRouter(prefix="/public/platform/catalog", tags=["public-platform-catalog"])


async def _enforce_public_catalog_rate_limit(
    request: Request,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    if settings.rate_public_platform_catalog_ip_limit <= 0:
        return
    trace_id = getattr(request.state, "trace_id", None)
    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:public_platform_catalog:ip:{client_ip}",
            limit=settings.rate_public_platform_catalog_ip_limit,
            window=settings.rate_public_platform_catalog_ip_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": "Слишком много запросов к каталогу. Попробуйте позже.",
                "trace_id": trace_id,
            },
        ) from None


@router.get("/plans", response_model=list[PlatformCatalogPlanPublic])
async def list_public_catalog_plans(
    session: AsyncSession = Depends(get_session),
    _rate: None = Depends(_enforce_public_catalog_rate_limit),
) -> list[PlatformCatalogPlanPublic]:
    res = await session.execute(
        select(PlatformCatalogPlan)
        .where(PlatformCatalogPlan.is_active.is_(True))
        .order_by(PlatformCatalogPlan.sort_order.asc(), PlatformCatalogPlan.slug.asc())
    )
    rows = list(res.scalars().all())
    out: list[PlatformCatalogPlanPublic] = []
    for p in rows:
        keys = p.option_keys if isinstance(p.option_keys, list) else []
        pm = format(p.price_monthly_rub, "f") if p.price_monthly_rub is not None else None
        pa = format(p.price_annual_rub, "f") if p.price_annual_rub is not None else None
        out.append(
            PlatformCatalogPlanPublic(
                slug=p.slug,
                display_name=p.display_name,
                description=p.description,
                option_keys=[str(x) for x in keys],
                price_monthly_rub=pm,
                price_annual_rub=pa,
                currency="USD",
            )
        )
    return out


@router.get("/options", response_model=list[PlatformCatalogOptionPublic])
async def list_public_catalog_options(
    session: AsyncSession = Depends(get_session),
    _rate: None = Depends(_enforce_public_catalog_rate_limit),
) -> list[PlatformCatalogOptionPublic]:
    res = await session.execute(
        select(PlatformCatalogOption)
        .where(PlatformCatalogOption.is_active.is_(True))
        .order_by(PlatformCatalogOption.sort_order.asc(), PlatformCatalogOption.entitlement_key.asc())
    )
    rows = list(res.scalars().all())
    out: list[PlatformCatalogOptionPublic] = []
    for o in rows:
        price: str | None = None
        if o.list_price_rub is not None:
            price = format(o.list_price_rub, "f")
        out.append(
            PlatformCatalogOptionPublic(
                entitlement_key=o.entitlement_key,
                display_name=o.display_name,
                description=o.description,
                list_price_rub=price,
                currency="USD",
            )
        )
    return out
