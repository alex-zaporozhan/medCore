from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.application.ai.tools_base import ToolContext, ToolError
from src.application.ai.tools_booking import (
    CancelBookingArgs,
    CancelBookingTool,
    CreateBookingArgs,
    CreateBookingTool,
    GetAvailableSlotsArgs,
    GetAvailableSlotsTool,
)
from src.core.config import settings
from src.core.context import RequestContext
from src.core.patient_messages import (
    BOOKING_CANNOT_CANCEL_PAST,
    BOOKING_CANNOT_CANCEL_STATUS,
    BOOKING_NOT_FOUND,
)


class _FakeScheduleService:
    async def get_daily_schedule(self, doctor_id: UUID, day: date):  # pragma: no cover
        raise AssertionError("Schedule service should not be called in these tests")


class _FakeBookingService:
    def __init__(self, behavior: str) -> None:
        self.behavior = behavior

    async def cancel_booking(self, clinic_id: UUID, booking_id: UUID, *, context=None):
        if self.behavior == "not_found":
            raise LookupError(BOOKING_NOT_FOUND)
        if self.behavior == "cannot_cancel_past":
            raise ValueError(BOOKING_CANNOT_CANCEL_PAST)
        if self.behavior == "cannot_cancel_status":
            raise ValueError(BOOKING_CANNOT_CANCEL_STATUS)
        raise AssertionError("Unexpected behavior value")


def _ctx(clinic_id: UUID, booking_service, schedule_service) -> ToolContext:
    return ToolContext(
        db=None,  # type: ignore[arg-type]
        clinic_id=clinic_id,
        request_context=RequestContext(
            clinic_id=clinic_id,
            user_id=None,
            user_type="system",
            trace_id="test-trace",
            roles=set(),
            permissions=set(),
        ),
        source="unit_test",
        booking_service=booking_service,  # type: ignore[arg-type]
        schedule_service=schedule_service,  # type: ignore[arg-type]
        patient_service=None,
    )


@pytest.mark.asyncio
async def test_get_available_slots_date_range_too_large_is_tool_error():
    clinic_id = uuid4()
    tool = GetAvailableSlotsTool()
    ctx = _ctx(clinic_id, booking_service=None, schedule_service=_FakeScheduleService())
    args = GetAvailableSlotsArgs(
        clinic_id=clinic_id,
        doctor_id=uuid4(),
        service_id=None,
        date_from=date.today(),
        date_to=date.today() + timedelta(days=settings.booking_ai_tools_max_range_days + 1),
    )

    res = await tool(ctx, args)
    assert isinstance(res, ToolError)
    assert res.code == "date_range_too_large"


@pytest.mark.asyncio
async def test_create_booking_requires_patient_token_or_patient_id():
    clinic_id = uuid4()
    tool = CreateBookingTool()
    ctx = _ctx(clinic_id, booking_service=None, schedule_service=None)
    args = CreateBookingArgs(
        clinic_id=clinic_id,
        patient_token=None,
        patient_id=None,
        doctor_id=uuid4(),
        service_id=uuid4(),
        appointment_start=datetime.utcnow(),
        notes=None,
        source="ai_agent",
    )

    res = await tool(ctx, args)
    assert isinstance(res, ToolError)
    assert res.code == "validation_error"


@pytest.mark.asyncio
async def test_cancel_booking_invalid_token_returns_tool_error():
    clinic_id = uuid4()
    tool = CancelBookingTool()
    ctx = _ctx(clinic_id, booking_service=_FakeBookingService("not_found"), schedule_service=None)
    args = CancelBookingArgs(
        clinic_id=clinic_id,
        booking_token="BOOKING#not-a-uuid",
        reason=None,
    )

    res = await tool(ctx, args)
    assert isinstance(res, ToolError)
    assert res.code == "validation_error"


@pytest.mark.asyncio
async def test_cancel_booking_not_found_returns_tool_error():
    clinic_id = uuid4()
    tool = CancelBookingTool()
    ctx = _ctx(clinic_id, booking_service=_FakeBookingService("not_found"), schedule_service=None)
    args = CancelBookingArgs(
        clinic_id=clinic_id,
        booking_token=f"BOOKING#{uuid4()}",
        reason=None,
    )

    res = await tool(ctx, args)
    assert isinstance(res, ToolError)
    assert res.code == "booking_not_found"
    assert res.message == BOOKING_NOT_FOUND


@pytest.mark.asyncio
async def test_cancel_booking_cannot_cancel_past_returns_tool_error():
    clinic_id = uuid4()
    tool = CancelBookingTool()
    ctx = _ctx(clinic_id, booking_service=_FakeBookingService("cannot_cancel_past"), schedule_service=None)
    args = CancelBookingArgs(
        clinic_id=clinic_id,
        booking_token=f"BOOKING#{uuid4()}",
        reason=None,
    )

    res = await tool(ctx, args)
    assert isinstance(res, ToolError)
    assert res.code == "validation_error"


@pytest.mark.asyncio
async def test_cancel_booking_cannot_cancel_status_returns_tool_error():
    clinic_id = uuid4()
    tool = CancelBookingTool()
    ctx = _ctx(clinic_id, booking_service=_FakeBookingService("cannot_cancel_status"), schedule_service=None)
    args = CancelBookingArgs(
        clinic_id=clinic_id,
        booking_token=f"BOOKING#{uuid4()}",
        reason=None,
    )

    res = await tool(ctx, args)
    assert isinstance(res, ToolError)
    assert res.code == "booking_status_invalid"

