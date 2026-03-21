"""CRM / attribution aggregates after a visit is posted to ERP (BKG_CORE G2, CRM_MONEY_008).

``BookingCompleted`` subscribers should refresh pipeline state and ``LeadCard.actual_value`` from
``ErpReportsRepository`` only — ERP financial rows are the source of truth for revenue facts.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.lead_lifecycle_dto import LeadEventVisitCompleted
from src.application.services.lead_lifecycle_service import LeadLifecycleService


class CrmAttributionSyncService:
    """Single entry for CRM money + stage updates driven by booking completion events."""

    def __init__(self, session: AsyncSession) -> None:
        self._lifecycle = LeadLifecycleService(session)

    async def on_booking_completed(
        self,
        *,
        clinic_id: UUID,
        booking_id: UUID,
        trace_id: str | None,
    ) -> None:
        await self._lifecycle.handle_visit_completed(
            LeadEventVisitCompleted(
                clinic_id=clinic_id,
                booking_id=booking_id,
                trace_id=trace_id,
                source="booking",
                visit_revenue=None,
            )
        )
