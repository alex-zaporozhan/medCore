"""LeadService CRM money: ERP-sourced actual_value and estimated forecast (CRM_MONEY_008)."""

from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal

import pytest

from src.application.services.lead_service import LeadService
from src.domain.entities.booking import Booking
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage


@pytest.mark.asyncio
async def test_update_actual_value_from_erp_sums_income(init_db, seed_data) -> None:
    from src.infrastructure.database import base as db_base

    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking = Booking(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_date=day,
            appointment_time=time(11, 0),
            status="completed",
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
        stage = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=0,
            code="new",
            name="Новое",
            probability=10,
            color="#888",
        )
        session.add(stage)
        await session.flush()

        lead = LeadCard(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            stage_id=stage.id,
            omnichannel_contact_id=None,
            patient_id=patient_id,
            primary_booking_id=booking_id,
            title="Money lead",
            source="test",
            estimated_value=Decimal("0.00"),
            actual_value=Decimal("0.00"),
            status="open",
        )
        session.add(lead)
        await session.flush()
        lead_id = lead.id

        cashbox = Cashbox(
            clinic_id=clinic_id,
            name="Lead CRM test",
            type="cash",
            currency="RUB",
            is_default=False,
            is_active=True,
        )
        session.add(cashbox)
        await session.flush()
        cashbox_id = cashbox.id

        happened = datetime.now(timezone.utc)
        session.add_all(
            [
                FinancialTransaction(
                    clinic_id=clinic_id,
                    cashbox_id=cashbox_id,
                    type="income",
                    amount=Decimal("40.00"),
                    currency="RUB",
                    happened_at=happened,
                    description="a",
                    booking_id=booking_id,
                    payment_id=None,
                    lead_id=None,
                    source="test",
                ),
                FinancialTransaction(
                    clinic_id=clinic_id,
                    cashbox_id=cashbox_id,
                    type="income",
                    amount=Decimal("35.00"),
                    currency="RUB",
                    happened_at=happened,
                    description="b",
                    booking_id=None,
                    payment_id=None,
                    lead_id=lead_id,
                    source="test",
                ),
            ]
        )
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        svc = LeadService(session)
        updated = await svc.update_actual_value_from_erp(
            clinic_id=clinic_id,
            lead_id=lead_id,
            trace_id="t1",
            source="test",
            extra_booking_ids=[booking_id],
        )
        assert updated.actual_value == Decimal("75.00")


@pytest.mark.asyncio
async def test_recalculate_estimated_value_from_primary_booking_service_price(init_db, seed_data) -> None:
    from src.infrastructure.database import base as db_base

    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking = Booking(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_date=day,
            appointment_time=time(11, 30),
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
        stage = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=0,
            code="new",
            name="Новое",
            probability=10,
            color="#888",
        )
        session.add(stage)
        await session.flush()

        lead = LeadCard(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            stage_id=stage.id,
            omnichannel_contact_id=None,
            patient_id=patient_id,
            primary_booking_id=booking_id,
            title="Est lead",
            source="test",
            estimated_value=Decimal("0.00"),
            actual_value=Decimal("0.00"),
            status="open",
        )
        session.add(lead)
        await session.flush()
        lead_id = lead.id
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        svc = LeadService(session)
        updated = await svc.recalculate_estimated_value(clinic_id=clinic_id, lead_id=lead_id)
        assert updated.estimated_value == Decimal("1000.00")
