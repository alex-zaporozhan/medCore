"""CRM maintenance tasks (CRM_MONEY E7 reconcile)."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from src.application.services.lead_service import LeadService
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.lead_card import LeadCard
from src.infrastructure.database.base import AsyncSessionLocal
from src.infrastructure.messaging.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _reconcile_lead_actual_values_async() -> None:
    """Refresh ``actual_value`` from ERP for success leads that still show 0 but have completed visits.

    One short session per lead to avoid one long transaction holding rows (QA_ARCH).
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            select(LeadCard.id, LeadCard.clinic_id)
            .where(
                LeadCard.status == "success",
                LeadCard.actual_value == 0,
            )
            .order_by(LeadCard.id)
            .limit(500)
        )
        result = await session.execute(stmt)
        todo = list(result.all())

    for lead_id, clinic_id in todo:
        async with AsyncSessionLocal() as session:
            svc = LeadService(session)
            lead = await svc.repository.get_lead_by_id(clinic_id, lead_id)
            if not lead:
                continue
            booking_ids = await svc._booking_ids_for_erp_actual(lead, None)
            if not booking_ids:
                continue
            st_row = await session.execute(
                select(Booking.status).where(
                    Booking.clinic_id == clinic_id,
                    Booking.id.in_(booking_ids),
                )
            )
            statuses = [r[0] for r in st_row.all()]
            if not any(s == BookingStatus.COMPLETED for s in statuses):
                continue
            try:
                await svc.update_actual_value_from_erp(
                    clinic_id=clinic_id,
                    lead_id=lead_id,
                    trace_id=None,
                    source="crm_reconcile_job",
                )
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception(
                    "crm_reconcile_lead_failed",
                    extra={"lead_id": str(lead_id), "clinic_id": str(clinic_id)},
                )


@celery_app.task(name="crm_tasks.reconcile_lead_actual_values")
def reconcile_lead_actual_values() -> None:
    try:
        asyncio.run(_reconcile_lead_actual_values_async())
    except Exception:
        logger.exception("reconcile_lead_actual_values failed")
        raise
