"""H4: after visit completion, CRM ``actual_value`` matches ERP income for the same booking/lead."""

from __future__ import annotations

from datetime import time
from decimal import Decimal

import pytest

from src.application.services.booking_completion_service import BookingCompletionService
from src.application.services.booking_service import BookingService
from src.application.services.erp_reports_repository import ErpReportsRepository
from src.application.services.lead_service import LeadService
from src.core.context import RequestContext
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_actual_value_matches_erp_sum_after_complete_and_sync(init_db, seed_data):
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        booking_read = await booking_service.create_admin_booking(
            clinic_id=clinic_id,
            data=type(
                "obj",
                (),
                {
                    "clinic_id": clinic_id,
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "service_id": service_id,
                    "appointment_date": day,
                    "appointment_time": time(15, 30),
                    "status": "confirmed",
                    "prepayment_amount": 0,
                    "notes": None,
                    "waitlist_entry_id": None,
                },
            )(),
        )
        await session.commit()

        completion = BookingCompletionService(session)
        actor = RequestContext(
            clinic_id=clinic_id,
            user_id=seed_data["admin_id"],
            user_type="admin",
        )
        result = await completion.complete_visit(booking_id=booking_read.id, actor=actor)
        assert result.success is True
        await session.commit()

        pipeline = LeadPipeline(
            clinic_id=clinic_id,
            name="Pipe",
            description=None,
            is_default=True,
        )
        session.add(pipeline)
        await session.flush()
        st = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=0,
            code="new",
            name="N",
            probability=10,
            color="#000",
        )
        session.add(st)
        await session.flush()
        lead = LeadCard(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            stage_id=st.id,
            omnichannel_contact_id=None,
            patient_id=patient_id,
            primary_booking_id=booking_read.id,
            title="L",
            source="test",
            estimated_value=Decimal("0.00"),
            actual_value=Decimal("0.00"),
            status="open",
        )
        session.add(lead)
        await session.commit()
        lead_id = lead.id

    async with db_base.AsyncSessionLocal() as session:
        leads = LeadService(session)
        erp = ErpReportsRepository(session)
        await leads.update_actual_value_from_erp(
            clinic_id=clinic_id,
            lead_id=lead_id,
            trace_id="test-h4",
            source="test_chain",
        )
        lead_row = await leads.repository.get_lead_by_id(clinic_id, lead_id)
        assert lead_row is not None
        erp_sum = await erp.sum_income_revenue_for_crm_lead(
            clinic_id=clinic_id,
            lead_id=lead_id,
            booking_ids=[booking_read.id],
        )
        assert lead_row.actual_value == erp_sum
