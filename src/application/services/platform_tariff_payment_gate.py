"""Gate platform SaaS payment vs catalog plan + billing_period (contour B, QA_ARCH)."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.platform_catalog_option import PlatformCatalogOption
from src.domain.entities.platform_catalog_plan import PlatformCatalogPlan

logger = logging.getLogger(__name__)

BILLING_PERIOD_MONTHLY = "monthly"
BILLING_PERIOD_ANNUAL = "annual"
_VALID_PERIODS = frozenset({BILLING_PERIOD_MONTHLY, BILLING_PERIOD_ANNUAL})


def parse_billing_period_from_snapshot(raw: dict[str, Any] | None) -> str | None:
    """
    None = key absent or legacy snapshot (no period enforcement).
    monthly | annual = valid.
    Raises ValueError if key present but value invalid.
    """
    if not isinstance(raw, dict) or "billing_period" not in raw:
        return None
    v = raw.get("billing_period")
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    s = str(v).strip().lower()
    if s in _VALID_PERIODS:
        return s
    raise ValueError("invalid_billing_period")


async def resolve_platform_checkout_totals(
    session: AsyncSession,
    *,
    plan_slug: str,
    billing_period: str,
    extra_entitlement_keys: list[str],
) -> tuple[Decimal, list[str]]:
    """
    Catalog-backed total for public signup checkout (base plan + optional add-ons).

    Add-on prices in ``PlatformCatalogOption.list_price_rub`` are treated as **monthly** supplements:
    they are added once per month for ``monthly`` billing, and multiplied by 12 for ``annual``.

    Returns ``(total_rub, normalized_extra_keys)``. Raises ``ValueError`` with a stable machine code.
    """
    slug = (plan_slug or "").strip().lower()
    bp = (billing_period or "").strip().lower()
    if bp not in _VALID_PERIODS:
        raise ValueError("invalid_billing_period")

    res = await session.execute(
        select(PlatformCatalogPlan).where(
            PlatformCatalogPlan.slug == slug,
            PlatformCatalogPlan.is_active.is_(True),
        ).limit(1)
    )
    plan = res.scalar_one_or_none()
    if plan is None:
        raise ValueError("unknown_plan_slug")

    if bp == BILLING_PERIOD_MONTHLY:
        base = plan.price_monthly_rub
    else:
        base = plan.price_annual_rub
    if base is None:
        raise ValueError("plan_price_missing")

    seen: set[str] = set()
    ordered: list[str] = []
    for raw in extra_entitlement_keys:
        k = str(raw).strip()
        if not k or k in seen:
            continue
        seen.add(k)
        ordered.append(k)

    plan_included = {str(x).strip() for x in (plan.option_keys or []) if x and str(x).strip()}
    addon_monthly = Decimal("0")

    for key in ordered:
        if key in plan_included:
            raise ValueError("extra_entitlement_overlaps_plan")

        opt_res = await session.execute(
            select(PlatformCatalogOption).where(
                PlatformCatalogOption.entitlement_key == key,
                PlatformCatalogOption.is_active.is_(True),
            ).limit(1)
        )
        opt = opt_res.scalar_one_or_none()
        if opt is None:
            raise ValueError("extra_entitlement_unknown")
        price = opt.list_price_rub
        if price is None:
            raise ValueError("extra_entitlement_no_price")
        addon_monthly += price

    if bp == BILLING_PERIOD_MONTHLY:
        total = base + addon_monthly
    else:
        total = base + addon_monthly * Decimal(12)

    return total, ordered


async def evaluate_platform_payment_against_catalog(
    session: AsyncSession,
    tariff_snapshot: dict[str, Any] | list[Any] | None,
    paid_amount_rub: Decimal | None,
) -> str | None:
    """
    After YooKassa confirms succeeded amount: decide if auto-provision is allowed.

    Returns None = proceed (no rule hit or cannot verify).
    Returns machine code string = block marking intent paid / provisioning (money may still be captured).
    """
    if not isinstance(tariff_snapshot, dict):
        return None
    try:
        period = parse_billing_period_from_snapshot(tariff_snapshot)
    except ValueError:
        return "invalid_billing_period"

    if period is None:
        return None

    slug_raw = tariff_snapshot.get("plan_slug")
    slug = str(slug_raw).strip().lower() if slug_raw else ""
    if not slug:
        return "billing_period_requires_plan_slug"

    raw_ex = tariff_snapshot.get("extra_entitlement_keys")
    extras: list[str] = []
    if isinstance(raw_ex, list):
        extras = [str(x).strip() for x in raw_ex if x is not None and str(x).strip()]

    try:
        expected, _ = await resolve_platform_checkout_totals(
            session,
            plan_slug=slug,
            billing_period=period,
            extra_entitlement_keys=extras,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "unknown_plan_slug":
            return "unknown_plan_slug"
        if code == "plan_price_missing":
            logger.warning(
                "Platform billing: billing_period set but catalog price missing; skip amount gate",
                extra={"slug": slug, "period": period},
            )
            return None
        logger.warning(
            "Platform billing: tariff snapshot rejected for payment gate",
            extra={"slug": slug, "code": code},
        )
        return "tariff_snapshot_invalid"

    if paid_amount_rub is None:
        return "missing_payment_amount"

    q = Decimal("0.01")
    if paid_amount_rub.quantize(q) != expected.quantize(q):
        logger.error(
            "Platform billing: paid amount does not match catalog subscription price",
            extra={
                "slug": slug,
                "period": period,
                "expected_rub": str(expected),
                "paid_rub": str(paid_amount_rub),
            },
        )
        return "amount_mismatch_catalog"

    return None
