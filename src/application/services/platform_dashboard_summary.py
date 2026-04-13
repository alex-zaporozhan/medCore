"""Founder dashboard aggregates: active SaaS orgs and MRR from tariff snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.platform_signup_intent import PlatformSignupIntent
from src.application.services.platform_tariff_payment_gate import (
    monthly_recurring_rub_from_tariff_snapshot,
)


@dataclass(frozen=True, slots=True)
class PlatformFounderDashboardSummary:
    active_organizations: int
    mrr_rub_monthly: Decimal
    mrr_partial: bool


async def compute_platform_founder_dashboard_summary(session: AsyncSession) -> PlatformFounderDashboardSummary:
    """
    Active orgs: distinct organizations with a non-revoked ``active`` signup intent.

    MRR: sum of catalog-derived monthly equivalents per org (one intent per org, newest by ``updated_at``).
    """
    res = await session.execute(
        select(PlatformSignupIntent).where(
            PlatformSignupIntent.status == "active",
            PlatformSignupIntent.organization_id.is_not(None),
            PlatformSignupIntent.billing_revoked_at.is_(None),
        )
    )
    rows = list(res.scalars().all())

    by_org: dict[UUID, PlatformSignupIntent] = {}
    for row in rows:
        oid = row.organization_id
        if oid is None:
            continue
        prev = by_org.get(oid)
        if prev is None:
            by_org[oid] = row
            continue
        pu = prev.updated_at
        ru = row.updated_at
        if pu is None or (ru is not None and (pu is None or ru > pu)):
            by_org[oid] = row

    active_organizations = len(by_org)
    mrr_total = Decimal("0")
    mrr_partial = False

    for intent in by_org.values():
        snap = intent.tariff_snapshot
        if not isinstance(snap, dict):
            mrr_partial = True
            continue
        mrr = await monthly_recurring_rub_from_tariff_snapshot(
            session,
            snap,
            require_active_plan=False,
        )
        if mrr is None:
            mrr_partial = True
            continue
        mrr_total += mrr

    return PlatformFounderDashboardSummary(
        active_organizations=active_organizations,
        mrr_rub_monthly=mrr_total.quantize(Decimal("0.01")),
        mrr_partial=mrr_partial,
    )
