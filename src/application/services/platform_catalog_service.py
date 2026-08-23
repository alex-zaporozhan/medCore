"""SaaS platform catalog (plans/options) — founder CRUD and helpers."""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.platform_billing_dto import PlatformCatalogPlanInternal
from src.domain.entities.platform_catalog_option import PlatformCatalogOption
from src.domain.entities.platform_catalog_plan import PlatformCatalogPlan

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def assert_valid_plan_slug(slug: str) -> str:
    s = (slug or "").strip().lower()
    if not _SLUG_RE.match(s):
        raise ValueError("invalid_plan_slug")
    return s


def format_catalog_rub_amount(v: Decimal | None) -> str | None:
    if v is None:
        return None
    return format(v, "f")


async def assert_option_keys_exist_in_platform_catalog(
    session: AsyncSession,
    keys: list[str],
) -> None:
    """Every key must exist in platform_catalog_options (prevents typos in plan bundles)."""
    if not keys:
        return
    res = await session.execute(
        select(PlatformCatalogOption.entitlement_key).where(
            PlatformCatalogOption.entitlement_key.in_(keys),
        )
    )
    found = {row[0] for row in res.fetchall()}
    missing = [k for k in keys if k not in found]
    if missing:
        raise ValueError(f"unknown_option_keys:{missing[0]}")


async def list_catalog_plans_all(session: AsyncSession) -> list[PlatformCatalogPlan]:
    res = await session.execute(
        select(PlatformCatalogPlan).order_by(
            PlatformCatalogPlan.sort_order.asc(),
            PlatformCatalogPlan.slug.asc(),
        )
    )
    return list(res.scalars().all())


async def upsert_catalog_plan(
    session: AsyncSession,
    *,
    slug: str,
    display_name: str,
    description: str | None,
    option_keys: list[str],
    is_active: bool,
    sort_order: int,
    price_monthly_rub: Decimal | None,
    price_annual_rub: Decimal | None,
    audit_actor_id: UUID | None = None,
) -> PlatformCatalogPlan:
    slug_norm = assert_valid_plan_slug(slug)
    keys_clean = [str(x).strip() for x in option_keys if x is not None and str(x).strip()]
    await assert_option_keys_exist_in_platform_catalog(session, keys_clean)
    res = await session.execute(
        select(PlatformCatalogPlan).where(PlatformCatalogPlan.slug == slug_norm).limit(1)
    )
    row = res.scalar_one_or_none()
    prev_snapshot: dict[str, Any] | None = None
    if row is not None:
        prev_snapshot = {
            "display_name": row.display_name,
            "description": row.description,
            "option_keys": list(row.option_keys) if isinstance(row.option_keys, list) else [],
            "price_monthly_rub": format_catalog_rub_amount(row.price_monthly_rub),
            "price_annual_rub": format_catalog_rub_amount(row.price_annual_rub),
            "is_active": bool(row.is_active),
            "sort_order": int(row.sort_order or 0),
        }
    if row is None:
        row = PlatformCatalogPlan(
            id=uuid4(),
            slug=slug_norm,
            display_name=display_name.strip(),
            description=description,
            option_keys=keys_clean,
            price_monthly_rub=price_monthly_rub,
            price_annual_rub=price_annual_rub,
            is_active=is_active,
            sort_order=sort_order,
        )
        session.add(row)
    else:
        row.display_name = display_name.strip()
        row.description = description
        row.option_keys = keys_clean
        row.price_monthly_rub = price_monthly_rub
        row.price_annual_rub = price_annual_rub
        row.is_active = is_active
        row.sort_order = sort_order
    await session.flush()
    if audit_actor_id is not None:
        after = {
            "display_name": row.display_name,
            "description": row.description,
            "option_keys": list(row.option_keys) if isinstance(row.option_keys, list) else [],
            "price_monthly_rub": format_catalog_rub_amount(row.price_monthly_rub),
            "price_annual_rub": format_catalog_rub_amount(row.price_annual_rub),
            "is_active": bool(row.is_active),
            "sort_order": int(row.sort_order or 0),
        }
        logger.info(
            "platform_catalog_plan_upsert",
            extra={
                "event": "platform_catalog_plan_upsert",
                "slug": slug_norm,
                "platform_founder_id": str(audit_actor_id),
                "before": prev_snapshot,
                "after": after,
            },
        )
    return row


def plan_to_internal_dto(row: PlatformCatalogPlan) -> PlatformCatalogPlanInternal:
    keys = row.option_keys if isinstance(row.option_keys, list) else []
    return PlatformCatalogPlanInternal(
        id=str(row.id),
        slug=row.slug,
        display_name=row.display_name,
        description=row.description,
        option_keys=[str(x) for x in keys],
        price_monthly_rub=format_catalog_rub_amount(row.price_monthly_rub),
        price_annual_rub=format_catalog_rub_amount(row.price_annual_rub),
        is_active=bool(row.is_active),
        sort_order=int(row.sort_order or 0),
        currency="USD",
    )
