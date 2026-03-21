"""Sample parity check: visit_revenue vitrine totals vs raw ERP (QA_ARCH W2 follow-up)."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.erp_aggregate_service import ErpAggregateService
from src.application.services.erp_reports_repository import ErpReportsRepository
from src.core.config import settings
from src.core.metrics import erp_aggregate_parity_sample_total
from src.core.prometheus_labels import clinic_bucket_label
from src.domain.entities.clinic import Clinic

logger = logging.getLogger(__name__)


def pick_clinic_for_day(clinic_ids: list[UUID], day: date) -> UUID | None:
    """Deterministic rotation: one clinic index per calendar day (stable across workers)."""
    if not clinic_ids:
        return None
    ordered = sorted(clinic_ids, key=lambda x: str(x))
    return ordered[day.toordinal() % len(ordered)]


async def compare_visit_revenue_totals(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    date_from: date,
    date_to: date,
) -> tuple[Decimal, Decimal]:
    """Sum(raw) vs sum(vitrine) for visit_revenue over [date_from, date_to]."""
    erp = ErpReportsRepository(session)
    svc = ErpAggregateService(session)
    raw_rows = await erp.get_visit_revenue_by_period(
        clinic_id=clinic_id, date_from=date_from, date_to=date_to
    )
    agg_rows = await svc.fetch_visit_revenue_aggregate(
        clinic_id=clinic_id, date_from=date_from, date_to=date_to
    )
    s_raw = sum((r.total_revenue for r in raw_rows), Decimal("0"))
    s_agg = sum((r.total_revenue for r in agg_rows), Decimal("0"))
    return s_raw, s_agg


async def run_daily_visit_revenue_parity_sample_async() -> None:
    """Compare raw vs aggregate for one clinic × yesterday (UTC). Off unless ERP_AGGREGATE_PARITY_SAMPLE_ENABLED."""
    if not settings.erp_aggregate_parity_sample_enabled:
        return

    from src.infrastructure.database.base import AsyncSessionLocal

    yesterday = date.today() - timedelta(days=1)

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Clinic.id).order_by(Clinic.id))
        clinic_ids = [row[0] for row in res.all()]
        cid = pick_clinic_for_day(clinic_ids, yesterday)
        if cid is None:
            erp_aggregate_parity_sample_total.labels(result="skipped_no_clinics").inc()
            return

        s_raw, s_agg = await compare_visit_revenue_totals(
            session, clinic_id=cid, date_from=yesterday, date_to=yesterday
        )
        bucket = clinic_bucket_label(cid)

        if s_raw == s_agg:
            erp_aggregate_parity_sample_total.labels(result="match").inc()
            logger.info(
                "erp_parity_sample_visit_revenue_ok",
                extra={
                    "clinic_id": str(cid),
                    "clinic_bucket": bucket,
                    "day": yesterday.isoformat(),
                    "sum_raw": str(s_raw),
                    "sum_agg": str(s_agg),
                },
            )
            return

        erp_aggregate_parity_sample_total.labels(result="mismatch").inc()
        logger.warning(
            "erp_parity_sample_visit_revenue_mismatch",
            extra={
                "clinic_id": str(cid),
                "clinic_bucket": bucket,
                "day": yesterday.isoformat(),
                "sum_raw": str(s_raw),
                "sum_agg": str(s_agg),
            },
        )
