from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from src.application.dto.lead_lifecycle_dto import (
    LeadEventBookingCancelled,
    LeadEventBookingCreated,
    LeadEventContactCreated,
    LeadEventNoShow,
    LeadEventStale,
    LeadEventVisitCompleted,
)
from src.application.services.lead_lifecycle_service import LeadLifecycleService
from src.core.context import RequestContext
from src.domain.entities.booking import Booking, BookingStatus
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.patient import Patient
from src.domain.entities.service import Service
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage
from tests.booking_slot import unique_booking_slot


def _unique_slot(base_day: date, hour: int) -> tuple[date, time]:
    return unique_booking_slot(base_day, hour=hour)


@pytest.mark.asyncio
async def test_lead_lifecycle_contact_created_creates_lead(seed_data):
    clinic_id = seed_data["clinic_id"]
    contact_id = uuid.uuid4()

    pipeline_id = uuid.uuid4()
    stage_start_id = uuid.uuid4()

    from src.infrastructure.database import base as db_base

    async with db_base.AsyncSessionLocal() as session:
        from src.domain.entities.omnichannel_contact import Contact

        session.add(
            Contact(
                id=contact_id,
                business_account_id=clinic_id,
                full_name=None,
                primary_phone=None,
                external_ids=None,
            )
        )
        session.add(
            LeadPipeline(
                id=pipeline_id,
                clinic_id=clinic_id,
                name="Default",
                description=None,
                is_default=True,
            )
        )
        session.add(
            LeadStage(
                id=stage_start_id,
                clinic_id=clinic_id,
                pipeline_id=pipeline_id,
                order=1,
                code="new",
                name="New",
                probability=10,
                color="#999999",
            )
        )
        await session.commit()

        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_contact_created(
            LeadEventContactCreated(
                clinic_id=clinic_id,
                contact_id=contact_id,
                patient_id=None,
                trace_id="tc1",
                source="omnichannel",
            )
        )
        await session.commit()

        lead = await lifecycle.leads.repository.find_open_lead_for_contact_or_patient(
            clinic_id=clinic_id,
            omnichannel_contact_id=contact_id,
            patient_id=None,
        )
        assert lead is not None
        assert lead.omnichannel_contact_id == contact_id
        assert lead.status == "open"


@pytest.mark.asyncio
async def test_lead_lifecycle_booking_cancelled_moves_lead_to_lost(seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]

    pipeline_id = uuid.uuid4()
    stage_start_id = uuid.uuid4()
    stage_scheduled_id = uuid.uuid4()
    stage_lost_id = uuid.uuid4()

    from src.infrastructure.database import base as db_base

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            LeadPipeline(
                id=pipeline_id,
                clinic_id=clinic_id,
                name="Default",
                description=None,
                is_default=True,
            )
        )
        session.add_all(
            [
                LeadStage(
                    id=stage_start_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=1,
                    code="new",
                    name="New",
                    probability=10,
                    color="#999999",
                ),
                LeadStage(
                    id=stage_scheduled_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=2,
                    code="scheduled",
                    name="Scheduled",
                    probability=50,
                    color="#3366ff",
                ),
                LeadStage(
                    id=stage_lost_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=99,
                    code="lost",
                    name="Lost",
                    probability=0,
                    color="#ff3333",
                ),
            ]
        )
        await session.commit()

        booking_id = uuid.uuid4()
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                service_id=service_id,
                appointment_date=date.today(),
                appointment_time=time(10, 0),
                status=BookingStatus.CANCELLED,
                prepayment_amount=Decimal("0.00"),
                notes=None,
            )
        )

        lead_id = uuid.uuid4()
        session.add(
            LeadCard(
                id=lead_id,
                clinic_id=clinic_id,
                pipeline_id=pipeline_id,
                stage_id=stage_scheduled_id,
                omnichannel_contact_id=None,
                visit_attribution_id=None,
                patient_id=patient_id,
                primary_booking_id=booking_id,
                title="Lead",
                source="booking",
                estimated_value=Decimal("0.00"),
                actual_value=Decimal("0.00"),
                status="open",
            )
        )
        await session.commit()

        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_booking_cancelled(
            LeadEventBookingCancelled(
                clinic_id=clinic_id,
                booking_id=booking_id,
                trace_id="t1",
                source="booking",
            )
        )
        await session.commit()

        updated = await lifecycle.leads.repository.get_lead_by_id(clinic_id, lead_id)
        assert updated is not None
        assert updated.stage_id == stage_lost_id
        assert updated.status == "lost"


@pytest.mark.asyncio
async def test_lead_lifecycle_booking_no_show_moves_lead_to_lost(seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]

    pipeline_id = uuid.uuid4()
    stage_start_id = uuid.uuid4()
    stage_scheduled_id = uuid.uuid4()
    stage_lost_id = uuid.uuid4()

    from src.infrastructure.database import base as db_base

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            LeadPipeline(
                id=pipeline_id,
                clinic_id=clinic_id,
                name="Default",
                description=None,
                is_default=True,
            )
        )
        session.add_all(
            [
                LeadStage(
                    id=stage_start_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=1,
                    code="new",
                    name="New",
                    probability=10,
                    color="#999999",
                ),
                LeadStage(
                    id=stage_scheduled_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=2,
                    code="scheduled",
                    name="Scheduled",
                    probability=50,
                    color="#3366ff",
                ),
                LeadStage(
                    id=stage_lost_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=99,
                    code="lost",
                    name="Lost",
                    probability=0,
                    color="#ff3333",
                ),
            ]
        )
        await session.commit()

        booking_id = uuid.uuid4()
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                service_id=service_id,
                appointment_date=date.today(),
                appointment_time=time(11, 0),
                status=BookingStatus.NO_SHOW,
                prepayment_amount=Decimal("0.00"),
                notes=None,
            )
        )

        lead_id = uuid.uuid4()
        session.add(
            LeadCard(
                id=lead_id,
                clinic_id=clinic_id,
                pipeline_id=pipeline_id,
                stage_id=stage_scheduled_id,
                omnichannel_contact_id=None,
                visit_attribution_id=None,
                patient_id=patient_id,
                primary_booking_id=booking_id,
                title="Lead",
                source="booking",
                estimated_value=Decimal("0.00"),
                actual_value=Decimal("0.00"),
                status="open",
            )
        )
        await session.commit()

        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_no_show(
            LeadEventNoShow(
                clinic_id=clinic_id,
                booking_id=booking_id,
                trace_id="t2",
                source="booking",
            )
        )
        await session.commit()

        updated = await lifecycle.leads.repository.get_lead_by_id(clinic_id, lead_id)
        assert updated is not None
        assert updated.stage_id == stage_lost_id
        assert updated.status == "lost"


@pytest.mark.asyncio
async def test_lead_lifecycle_booking_created_attaches_booking_and_moves_stage(seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = uuid.uuid4()
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]

    pipeline_id = uuid.uuid4()
    stage_start_id = uuid.uuid4()
    stage_scheduled_id = uuid.uuid4()

    booking_id = uuid.uuid4()
    lead_id = uuid.uuid4()

    from src.infrastructure.database import base as db_base

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            LeadPipeline(
                id=pipeline_id,
                clinic_id=clinic_id,
                name="Default",
                description=None,
                is_default=True,
            )
        )
        session.add_all(
            [
                LeadStage(
                    id=stage_start_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=1,
                    code="new",
                    name="New",
                    probability=10,
                    color="#999999",
                ),
                LeadStage(
                    id=stage_scheduled_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=2,
                    code="scheduled",
                    name="Scheduled",
                    probability=50,
                    color="#3366ff",
                ),
            ]
        )
        session.add(
            Patient(
                id=patient_id,
                clinic_id=clinic_id,
                phone=f"+79{str(patient_id.int)[:9]}",
                full_name="Lead lifecycle patient",
            )
        )
        await session.commit()

        booking_day, booking_time = _unique_slot(seed_data["date"], 12)
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                service_id=service_id,
                appointment_date=booking_day,
                appointment_time=booking_time,
                status=BookingStatus.PENDING,
                prepayment_amount=Decimal("0.00"),
                notes=None,
            )
        )
        session.add(
            LeadCard(
                id=lead_id,
                clinic_id=clinic_id,
                pipeline_id=pipeline_id,
                stage_id=stage_start_id,
                omnichannel_contact_id=None,
                visit_attribution_id=None,
                patient_id=patient_id,
                primary_booking_id=None,
                title="Lead",
                source="booking",
                estimated_value=Decimal("0.00"),
                actual_value=Decimal("0.00"),
                status="open",
            )
        )
        await session.commit()

        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_booking_created(
            LeadEventBookingCreated(
                clinic_id=clinic_id,
                patient_id=patient_id,
                booking_id=booking_id,
                trace_id="tb1",
                source="booking",
            )
        )
        await session.commit()

        updated = await lifecycle.leads.repository.get_lead_by_id(clinic_id, lead_id)
        assert updated is not None
        assert updated.primary_booking_id == booking_id
        assert updated.stage_id == stage_scheduled_id


@pytest.mark.asyncio
async def test_lead_lifecycle_booking_completed_moves_to_won_and_closes_success(seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]

    pipeline_id = uuid.uuid4()
    stage_scheduled_id = uuid.uuid4()
    stage_won_id = uuid.uuid4()

    booking_id = uuid.uuid4()
    lead_id = uuid.uuid4()

    from src.infrastructure.database import base as db_base

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            LeadPipeline(
                id=pipeline_id,
                clinic_id=clinic_id,
                name="Default",
                description=None,
                is_default=True,
            )
        )
        session.add_all(
            [
                LeadStage(
                    id=stage_scheduled_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=2,
                    code="scheduled",
                    name="Scheduled",
                    probability=50,
                    color="#3366ff",
                ),
                LeadStage(
                    id=stage_won_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=99,
                    code="won",
                    name="Won",
                    probability=100,
                    color="#22aa22",
                ),
            ]
        )
        await session.commit()

        booking_day, booking_time = _unique_slot(seed_data["date"], 13)
        cashbox_id = await session.scalar(
            select(Cashbox.id).where(Cashbox.clinic_id == clinic_id).order_by(Cashbox.is_default.desc())
        )
        assert cashbox_id is not None
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                service_id=service_id,
                appointment_date=booking_day,
                appointment_time=booking_time,
                status=BookingStatus.COMPLETED,
                prepayment_amount=Decimal("0.00"),
                notes=None,
            )
        )
        session.add(
            LeadCard(
                id=lead_id,
                clinic_id=clinic_id,
                pipeline_id=pipeline_id,
                stage_id=stage_scheduled_id,
                omnichannel_contact_id=None,
                visit_attribution_id=None,
                patient_id=patient_id,
                primary_booking_id=booking_id,
                title="Lead",
                source="booking",
                estimated_value=Decimal("0.00"),
                actual_value=Decimal("0.00"),
                status="open",
            )
        )
        session.add(
            FinancialTransaction(
                clinic_id=clinic_id,
                cashbox_id=cashbox_id,
                type="income",
                amount=Decimal("150.00"),
                currency="RUB",
                happened_at=datetime.now(timezone.utc),
                description="visit erp income",
                booking_id=booking_id,
                payment_id=None,
                lead_id=lead_id,
                source="test",
            )
        )
        await session.commit()

        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_visit_completed(
            LeadEventVisitCompleted(
                clinic_id=clinic_id,
                booking_id=booking_id,
                trace_id="tc2",
                source="booking",
                visit_revenue=None,
            )
        )
        await session.commit()

        updated = await lifecycle.leads.repository.get_lead_by_id(clinic_id, lead_id)
        assert updated is not None
        assert updated.stage_id == stage_won_id
        assert updated.status == "success"
        assert updated.closed_at is not None
        assert updated.actual_value == Decimal("150.00")


@pytest.mark.asyncio
async def test_lead_lifecycle_visit_completed_without_erp_income_keeps_actual_zero(seed_data):
    """Closed-won with no financial_transactions: actual_value stays 0 (CRM_MONEY_008)."""
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]

    pipeline_id = uuid.uuid4()
    stage_scheduled_id = uuid.uuid4()
    stage_won_id = uuid.uuid4()
    booking_id = uuid.uuid4()
    lead_id = uuid.uuid4()

    from src.infrastructure.database import base as db_base

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            LeadPipeline(
                id=pipeline_id,
                clinic_id=clinic_id,
                name="Default",
                description=None,
                is_default=True,
            )
        )
        session.add_all(
            [
                LeadStage(
                    id=stage_scheduled_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=2,
                    code="scheduled",
                    name="Scheduled",
                    probability=50,
                    color="#3366ff",
                ),
                LeadStage(
                    id=stage_won_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=99,
                    code="won",
                    name="Won",
                    probability=100,
                    color="#22aa22",
                ),
            ]
        )
        await session.commit()
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                service_id=service_id,
                appointment_date=date.today(),
                appointment_time=time(14, 0),
                status=BookingStatus.COMPLETED,
                prepayment_amount=Decimal("0.00"),
                notes=None,
            )
        )
        session.add(
            LeadCard(
                id=lead_id,
                clinic_id=clinic_id,
                pipeline_id=pipeline_id,
                stage_id=stage_scheduled_id,
                omnichannel_contact_id=None,
                visit_attribution_id=None,
                patient_id=patient_id,
                primary_booking_id=booking_id,
                title="Lead",
                source="booking",
                estimated_value=Decimal("0.00"),
                actual_value=Decimal("0.00"),
                status="open",
            )
        )
        await session.commit()

        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_visit_completed(
            LeadEventVisitCompleted(
                clinic_id=clinic_id,
                booking_id=booking_id,
                trace_id="tc-zero",
                source="booking",
                visit_revenue=None,
            )
        )
        await session.commit()

        updated = await lifecycle.leads.repository.get_lead_by_id(clinic_id, lead_id)
        assert updated is not None
        assert updated.status == "success"
        assert updated.actual_value == Decimal("0.00")


@pytest.mark.asyncio
async def test_lead_lifecycle_booking_created_creates_lead_when_none(seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = uuid.uuid4()
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]

    pipeline_id = uuid.uuid4()
    stage_start_id = uuid.uuid4()
    stage_scheduled_id = uuid.uuid4()
    booking_id = uuid.uuid4()
    contact_id = uuid.uuid4()

    from src.infrastructure.database import base as db_base

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            LeadPipeline(
                id=pipeline_id,
                clinic_id=clinic_id,
                name="Default",
                description=None,
                is_default=True,
            )
        )
        session.add_all(
            [
                LeadStage(
                    id=stage_start_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=1,
                    code="new",
                    name="New",
                    probability=10,
                    color="#999999",
                ),
                LeadStage(
                    id=stage_scheduled_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=2,
                    code="scheduled",
                    name="Scheduled",
                    probability=50,
                    color="#3366ff",
                ),
            ]
        )
        from src.domain.entities.omnichannel_contact import Contact

        session.add(
            Contact(
                id=contact_id,
                business_account_id=clinic_id,
                full_name=None,
                primary_phone=None,
                external_ids=None,
            )
        )
        session.add(
            Patient(
                id=patient_id,
                clinic_id=clinic_id,
                phone=f"+79{str(patient_id.int)[:9]}",
                full_name="Lead lifecycle new patient",
            )
        )
        await session.commit()

        booking_day, booking_time = _unique_slot(seed_data["date"], 14)
        session.add(
            Booking(
                id=booking_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                service_id=service_id,
                appointment_date=booking_day,
                appointment_time=booking_time,
                status=BookingStatus.PENDING,
                prepayment_amount=Decimal("0.00"),
                notes=None,
            )
        )
        await session.commit()

        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_booking_created(
            LeadEventBookingCreated(
                clinic_id=clinic_id,
                patient_id=patient_id,
                booking_id=booking_id,
                contact_id=contact_id,
                trace_id="tb_new",
                source="booking",
            )
        )
        await session.commit()

        lead = await lifecycle.leads.repository.find_open_lead_for_contact_or_patient(
            clinic_id=clinic_id,
            omnichannel_contact_id=contact_id,
            patient_id=patient_id,
        )
        assert lead is not None
        assert lead.primary_booking_id == booking_id
        assert lead.patient_id == patient_id
        assert lead.omnichannel_contact_id == contact_id
        assert lead.stage_id is not None
        service = await session.get(Service, service_id)
        assert service is not None
        assert lead.estimated_value == Decimal(str(service.price))


@pytest.mark.asyncio
async def test_lead_lifecycle_stale_lead_moves_to_stale_stage(seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]

    pipeline_id = uuid.uuid4()
    stage_start_id = uuid.uuid4()
    stage_stale_id = uuid.uuid4()
    lead_id = uuid.uuid4()

    from src.infrastructure.database import base as db_base

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            LeadPipeline(
                id=pipeline_id,
                clinic_id=clinic_id,
                name="Default",
                description=None,
                is_default=True,
            )
        )
        session.add_all(
            [
                LeadStage(
                    id=stage_start_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=1,
                    code="new",
                    name="New",
                    probability=10,
                    color="#999999",
                ),
                LeadStage(
                    id=stage_stale_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=50,
                    code="stale",
                    name="Stale",
                    probability=5,
                    color="#ffaa00",
                ),
            ]
        )
        await session.commit()

        session.add(
            LeadCard(
                id=lead_id,
                clinic_id=clinic_id,
                pipeline_id=pipeline_id,
                stage_id=stage_start_id,
                omnichannel_contact_id=None,
                visit_attribution_id=None,
                patient_id=patient_id,
                primary_booking_id=None,
                title="Lead",
                source="omnichannel",
                estimated_value=Decimal("0.00"),
                actual_value=Decimal("0.00"),
                status="open",
            )
        )
        await session.commit()

        lifecycle = LeadLifecycleService(session)
        await lifecycle.handle_stale_lead(
            LeadEventStale(
                clinic_id=clinic_id,
                lead_id=lead_id,
                trace_id="ts1",
                source="scheduler",
            )
        )
        await session.commit()

        updated = await lifecycle.leads.repository.get_lead_by_id(clinic_id, lead_id)
        assert updated is not None
        assert updated.stage_id == stage_stale_id
        assert updated.status == "open"


@pytest.mark.asyncio
async def test_manual_change_lead_stage_uses_audited_path(seed_data):
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]

    pipeline_id = uuid.uuid4()
    stage_a_id = uuid.uuid4()
    stage_b_id = uuid.uuid4()
    lead_id = uuid.uuid4()

    from src.infrastructure.database import base as db_base
    from src.application.services.lead_service import LeadService

    async with db_base.AsyncSessionLocal() as session:
        session.add(
            LeadPipeline(
                id=pipeline_id,
                clinic_id=clinic_id,
                name="Default",
                description=None,
                is_default=True,
            )
        )
        session.add_all(
            [
                LeadStage(
                    id=stage_a_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=1,
                    code="new",
                    name="New",
                    probability=10,
                    color="#999999",
                ),
                LeadStage(
                    id=stage_b_id,
                    clinic_id=clinic_id,
                    pipeline_id=pipeline_id,
                    order=2,
                    code="scheduled",
                    name="Scheduled",
                    probability=50,
                    color="#3366ff",
                ),
            ]
        )
        await session.commit()

        session.add(
            LeadCard(
                id=lead_id,
                clinic_id=clinic_id,
                pipeline_id=pipeline_id,
                stage_id=stage_a_id,
                omnichannel_contact_id=None,
                visit_attribution_id=None,
                patient_id=patient_id,
                primary_booking_id=None,
                title="Lead",
                source="admin",
                estimated_value=Decimal("0.00"),
                actual_value=Decimal("0.00"),
                status="open",
            )
        )
        await session.commit()

        service = LeadService(session)
        ctx = RequestContext(
            clinic_id=clinic_id,
            user_id=uuid.uuid4(),
            user_type="admin",
            trace_id="tm1",
            roles=set(),
            permissions=set(),
        )
        updated = await service.change_lead_stage(
            clinic_id=clinic_id,
            lead_id=lead_id,
            new_stage_id=stage_b_id,
            request_context=ctx,
        )
        await session.commit()

        assert updated.stage_id == stage_b_id


