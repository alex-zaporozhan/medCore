"""Unit tests for AI booking tools: GetAvailableSlotsTool and CreateBookingTool."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from src.application.ai.tools_base import ToolContext
from src.application.ai.tools_booking import (
    AvailableSlot,
    CreateBookingArgs,
    CreateBookingResult,
    CreateBookingTool,
    GetAvailableSlotsArgs,
    GetAvailableSlotsTool,
    ToolError,
)
from src.application.services.booking_service import BookingService
from src.application.services.schedule_service import ScheduleService
from src.application.services.patient_service import PatientService
from src.core.context import RequestContext
from src.domain.entities.booking import Booking
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_get_available_slots_happy_path(init_db, seed_data, redis_client):
    """Tool should return at least one available slot for seeded doctor/day."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        tool = GetAvailableSlotsTool()
        ctx = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=None,
                user_type="system",
                roles=set(),
                permissions=set(),
            ),
            booking_service=BookingService(session),
            schedule_service=ScheduleService(session),
            patient_service=PatientService(session),
        )

        args = GetAvailableSlotsArgs(
            clinic_id=clinic_id,
            service_id=service_id,
            doctor_id=doctor_id,
            date_from=day,
            date_to=day,
        )

        result = await tool(ctx, args)

        assert not isinstance(result, ToolError)
        assert isinstance(result, list)
        assert result, "Expected at least one available slot"
        assert all(isinstance(slot, AvailableSlot) for slot in result)
        assert all(slot.doctor_id == doctor_id for slot in result)


@pytest.mark.asyncio
async def test_get_available_slots_invalid_date_range(init_db, seed_data, redis_client):
    """Tool should return ToolError for invalid date range."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        tool = GetAvailableSlotsTool()
        ctx = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=None,
                user_type="system",
                roles=set(),
                permissions=set(),
            ),
            booking_service=BookingService(session),
            schedule_service=ScheduleService(session),
            patient_service=PatientService(session),
        )

        args = GetAvailableSlotsArgs(
            clinic_id=clinic_id,
            service_id=service_id,
            doctor_id=doctor_id,
            date_from=day + timedelta(days=1),
            date_to=day,
        )

        result = await tool(ctx, args)

        assert isinstance(result, ToolError)
        assert result.code == "invalid_date_range"


@pytest.mark.asyncio
async def test_get_available_slots_clinic_mismatch(init_db, seed_data, redis_client):
    """Tool should enforce clinic_id boundary and return clinic_mismatch error."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        tool = GetAvailableSlotsTool()
        ctx = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=None,
                user_type="system",
                roles=set(),
                permissions=set(),
            ),
            booking_service=BookingService(session),
            schedule_service=ScheduleService(session),
            patient_service=PatientService(session),
        )

        args = GetAvailableSlotsArgs(
            clinic_id=uuid.uuid4(),  # different clinic
            service_id=service_id,
            doctor_id=doctor_id,
            date_from=day,
            date_to=day,
        )

        result = await tool(ctx, args)

        assert isinstance(result, ToolError)
        assert result.code == "clinic_mismatch"


@pytest.mark.asyncio
async def test_get_available_slots_doctor_required(init_db, seed_data, redis_client):
    """Tool should return doctor_required error when doctor_id is missing."""
    clinic_id = seed_data["clinic_id"]
    service_id = seed_data["service_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        tool = GetAvailableSlotsTool()
        ctx = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=None,
                user_type="system",
                roles=set(),
                permissions=set(),
            ),
            booking_service=BookingService(session),
            schedule_service=ScheduleService(session),
            patient_service=PatientService(session),
        )

        args = GetAvailableSlotsArgs(
            clinic_id=clinic_id,
            service_id=service_id,
            doctor_id=None,
            date_from=day,
            date_to=day,
        )

        result = await tool(ctx, args)

        assert isinstance(result, ToolError)
        assert result.code == "doctor_required"


@pytest.mark.asyncio
async def test_get_available_slots_invalid_service_doctor(init_db, seed_data, redis_client):
    """Tool should return invalid_service_doctor when doctor does not provide given service."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        tool = GetAvailableSlotsTool()
        ctx = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=None,
                user_type="system",
                roles=set(),
                permissions=set(),
            ),
            booking_service=BookingService(session),
            schedule_service=ScheduleService(session),
            patient_service=PatientService(session),
        )

        # Use random UUID as non‑linked service_id to trigger _ensure_service_doctor error
        from uuid import uuid4

        bad_service_id = uuid4()

        args = GetAvailableSlotsArgs(
            clinic_id=clinic_id,
            service_id=bad_service_id,
            doctor_id=doctor_id,
            date_from=day,
            date_to=day,
        )

        result = await tool(ctx, args)

        assert isinstance(result, ToolError)
        assert result.code == "invalid_service_doctor"


@pytest.mark.asyncio
async def test_create_booking_success(init_db, seed_data, redis_client):
    """CreateBookingTool should create booking and mark notes with source=ai_agent."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        schedule_service = ScheduleService(session)
        patient_service = PatientService(session)
        tool = CreateBookingTool()

        ctx = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=None,
                user_type="system",
                roles=set(),
                permissions=set(),
            ),
            booking_service=booking_service,
            schedule_service=schedule_service,
            patient_service=patient_service,
        )

        # Find first available slot via schedule service
        daily = await schedule_service.get_daily_schedule(doctor_id=doctor_id, day=day)
        slot = next(s for s in daily.slots if s.is_available)

        from datetime import datetime

        appointment_start = datetime.combine(day, slot.start_time)

        args = CreateBookingArgs(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_start=appointment_start,
            notes="Initial via AI",
            source="ai_agent",
        )

        result = await tool(ctx, args)

        assert not isinstance(result, ToolError)
        assert isinstance(result, CreateBookingResult)
        booking = result.booking
        assert booking.clinic_id == clinic_id
        assert booking.patient_id == patient_id
        assert booking.doctor_id == doctor_id
        assert booking.service_id == service_id
        assert booking.notes is not None and "[source=ai_agent]" in booking.notes

        # Ensure booking is actually persisted
        db_result = await session.execute(select(Booking).where(Booking.id == booking.id))
        persisted = db_result.scalar_one_or_none()
        assert persisted is not None


@pytest.mark.asyncio
async def test_create_booking_slot_conflict(init_db, seed_data, redis_client):
    """CreateBookingTool should return slot_conflict when slot already booked."""
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        schedule_service = ScheduleService(session)
        patient_service = PatientService(session)
        tool = CreateBookingTool()

        ctx = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=None,
                user_type="system",
                roles=set(),
                permissions=set(),
            ),
            booking_service=booking_service,
            schedule_service=schedule_service,
            patient_service=patient_service,
        )

        daily = await schedule_service.get_daily_schedule(doctor_id=doctor_id, day=day)
        slot = next(s for s in daily.slots if s.is_available)

        from datetime import datetime

        appointment_start = datetime.combine(day, slot.start_time)

        # First call – successful booking
        args_ok = CreateBookingArgs(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_start=appointment_start,
            notes="First booking",
            source="ai_agent",
        )
        res1 = await tool(ctx, args_ok)
        assert not isinstance(res1, ToolError)

        # Second call with same slot – expect slot_conflict
        args_conflict = CreateBookingArgs(
            clinic_id=clinic_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_start=appointment_start,
            notes="Second booking",
            source="ai_agent",
        )
        res2 = await tool(ctx, args_conflict)

        assert isinstance(res2, ToolError)
        assert res2.code == "slot_conflict"


@pytest.mark.asyncio
async def test_create_booking_clinic_mismatch(init_db, seed_data, redis_client):
    """CreateBookingTool should return clinic_mismatch when args.clinic_id differs from context."""
    from uuid import uuid4

    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    patient_id = seed_data["patient_id"]
    day = seed_data["date"]

    async with db_base.AsyncSessionLocal() as session:
        booking_service = BookingService(session)
        schedule_service = ScheduleService(session)
        patient_service = PatientService(session)
        tool = CreateBookingTool()

        ctx = ToolContext(
            db=session,
            clinic_id=clinic_id,
            request_context=RequestContext(
                clinic_id=clinic_id,
                user_id=None,
                user_type="system",
                roles=set(),
                permissions=set(),
            ),
            booking_service=booking_service,
            schedule_service=schedule_service,
            patient_service=patient_service,
        )

        daily = await schedule_service.get_daily_schedule(doctor_id=doctor_id, day=day)
        slot = next(s for s in daily.slots if s.is_available)

        from datetime import datetime

        appointment_start = datetime.combine(day, slot.start_time)

        args = CreateBookingArgs(
            clinic_id=uuid4(),  # mismatch
            patient_id=patient_id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_start=appointment_start,
            notes=None,
            source="ai_agent",
        )

        result = await tool(ctx, args)

        assert isinstance(result, ToolError)
        assert result.code == "clinic_mismatch"

