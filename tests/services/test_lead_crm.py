"""CRM lead repository and API: get_lead_by_primary_booking_id, list_leads filters."""

from __future__ import annotations

from datetime import time
from decimal import Decimal

import pytest

from src.application.services.lead_service import LeadService
from src.domain.entities.booking import Booking
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage
from src.infrastructure.database.base import AsyncSessionLocal


@pytest.mark.asyncio
async def test_get_lead_by_primary_booking_id_and_list_leads_filters(init_db, seed_data):
    """Repository get_lead_by_primary_booking_id and list_leads(patient_id, booking_id) work."""
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]

    async with AsyncSessionLocal() as session:
        booking = Booking(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_date=day,
            appointment_time=time(10, 0),
            status="confirmed",
            prepayment_amount=Decimal("0"),
        )
        session.add(booking)
        await session.flush()
        booking_id = booking.id

        pipeline = LeadPipeline(
            clinic_id=clinic_id,
            name="Default",
            description=None,
            is_default=True,
        )
        session.add(pipeline)
        await session.flush()

        stage_new = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=0,
            code="new",
            name="Новое",
            probability=10,
            color="#888",
        )
        stage_booked = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=1,
            code="booked",
            name="Записан",
            probability=50,
            color="#38a",
        )
        session.add(stage_new)
        session.add(stage_booked)
        await session.flush()

        lead = LeadCard(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            stage_id=stage_booked.id,
            omnichannel_contact_id=None,
            patient_id=patient_id,
            primary_booking_id=booking_id,
            title="Test lead",
            source="test",
            estimated_value=Decimal("1000.00"),
            actual_value=Decimal("0.00"),
            status="open",
        )
        session.add(lead)
        await session.commit()
        lead_id = lead.id

    async with AsyncSessionLocal() as session:
        service = LeadService(session)
        found = await service.repository.get_lead_by_primary_booking_id(
            clinic_id=clinic_id, booking_id=booking_id
        )
        assert found is not None
        assert found.id == lead_id
        assert found.primary_booking_id == booking_id
        assert found.patient_id == patient_id

        by_patient, total_p = await service.list_leads(
            clinic_id=clinic_id,
            patient_id=patient_id,
            limit=10,
        )
        assert len(by_patient) == 1
        assert total_p >= 1
        assert by_patient[0].id == lead_id

        by_booking, total_b = await service.list_leads(
            clinic_id=clinic_id,
            booking_id=booking_id,
            limit=10,
        )
        assert len(by_booking) == 1
        assert total_b >= 1
        assert by_booking[0].id == lead_id
