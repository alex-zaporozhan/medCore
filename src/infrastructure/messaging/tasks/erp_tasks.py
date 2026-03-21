"""Celery tasks for ERP report pre-aggregates (Engine L2)."""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from uuid import UUID

from src.application.services.erp_aggregate_service import (
    ErpAggregateService,
    refresh_all_clinics_erp_aggregates_nightly,
)
from src.application.services.erp_report_cache import invalidate_clinic_erp_report_cache
from src.application.services.erp_parity_sample_service import (
    run_daily_visit_revenue_parity_sample_async,
)
from src.infrastructure.database.base import AsyncSessionLocal
from src.infrastructure.messaging.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _refresh_erp_aggregates_nightly_async() -> None:
    await refresh_all_clinics_erp_aggregates_nightly()


async def _refresh_clinic_window_async(
    clinic_id: UUID,
    date_from: date,
    date_to: date,
) -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            svc = ErpAggregateService(session)
            await svc.refresh_clinic_erp_aggregates_window(
                clinic_id=clinic_id,
                date_from=date_from,
                date_to=date_to,
                job_type="event_window",
            )
    await invalidate_clinic_erp_report_cache(clinic_id)


@celery_app.task(name="erp_tasks.run_daily_visit_revenue_parity_sample")
def run_daily_visit_revenue_parity_sample() -> None:
    """Optional trust signal: one clinic × yesterday, raw vs visit_revenue vitrine (see NONFUNCTIONAL_AUDIT_NEXT §5.2)."""
    try:
        asyncio.run(run_daily_visit_revenue_parity_sample_async())
    except Exception:
        logger.exception("run_daily_visit_revenue_parity_sample failed")
        raise


@celery_app.task(name="erp_tasks.refresh_erp_aggregates_nightly")
def refresh_erp_aggregates_nightly() -> None:
    """Nightly roll-up of ERP report vitrines (visit revenue, payroll, materials, attribution)."""
    try:
        asyncio.run(_refresh_erp_aggregates_nightly_async())
    except Exception:
        logger.exception("refresh_erp_aggregates_nightly failed")
        raise


@celery_app.task(name="erp_tasks.refresh_clinic_erp_aggregates_window")
def refresh_clinic_erp_aggregates_window(
    clinic_id: str,
    date_from: str,
    date_to: str,
) -> None:
    """Refresh all four vitrines for [date_from, date_to] under per-clinic advisory lock (BOOKING_COMPLETED / ops)."""
    try:
        cid = UUID(clinic_id)
        df = date.fromisoformat(date_from)
        dt = date.fromisoformat(date_to)
        asyncio.run(_refresh_clinic_window_async(cid, df, dt))
    except Exception:
        logger.exception(
            "refresh_clinic_erp_aggregates_window failed",
            extra={"clinic_id": clinic_id, "date_from": date_from, "date_to": date_to},
        )
        raise
