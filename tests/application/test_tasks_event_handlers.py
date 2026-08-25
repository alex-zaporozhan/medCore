"""System task templates for booking cancel / no-show events (Q7 A1)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.events.domain_event import DomainEvent
from src.application.events.tasks_event_handlers import (
    create_system_task_for_cancelled_booking,
    create_system_task_for_no_show,
)


def _mock_session_with_booking(booking: MagicMock) -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock(return_value=booking)
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=scalar_result)
    return session


def _booking_stub() -> MagicMock:
    booking = MagicMock()
    booking.id = uuid4()
    booking.clinic_id = uuid4()
    booking.patient_id = uuid4()
    return booking


@pytest.mark.asyncio
async def test_cancelled_booking_creates_en_task_without_trace_in_description():
    booking = _booking_stub()
    trace_id = str(uuid4())
    event = DomainEvent(
        name="BOOKING_CANCELLED",
        payload={"booking_id": str(booking.id), "trace_id": trace_id},
    )
    session = _mock_session_with_booking(booking)
    create_task_mock = AsyncMock()

    with (
        patch(
            "src.application.events.tasks_event_handlers._has_open_task_for_source_event",
            AsyncMock(return_value=False),
        ),
        patch("src.application.events.tasks_event_handlers.LeadRepositoryImpl") as lead_repo_cls,
        patch("src.application.events.tasks_event_handlers.TaskRepositoryImpl"),
        patch("src.application.events.tasks_event_handlers.TaskService") as task_service_cls,
    ):
        lead_repo_cls.return_value.get_lead_by_primary_booking_id = AsyncMock(return_value=None)
        task_service_cls.return_value.create_task = create_task_mock

        await create_system_task_for_cancelled_booking(event, session)

    create_task_mock.assert_awaited_once()
    kwargs = create_task_mock.await_args.kwargs
    assert kwargs["title"] == "Follow up on a cancelled booking"
    assert kwargs["description"] == (
        "The booking was cancelled. Contact the patient to reschedule "
        "or offer the slot to others."
    )
    assert "trace_id=" not in kwargs["description"]
    assert "event_id=" not in kwargs["description"]
    assert kwargs["trace_id"] == trace_id
    assert kwargs["source"] == "system"
    assert kwargs["booking_id"] == booking.id


@pytest.mark.asyncio
async def test_cancelled_booking_skips_when_open_task_already_exists():
    booking = _booking_stub()
    event = DomainEvent(
        name="BOOKING_CANCELLED",
        payload={"booking_id": str(booking.id), "trace_id": str(uuid4())},
    )
    session = _mock_session_with_booking(booking)
    create_task_mock = AsyncMock()

    with (
        patch(
            "src.application.events.tasks_event_handlers._has_open_task_for_source_event",
            AsyncMock(return_value=True),
        ),
        patch("src.application.events.tasks_event_handlers.LeadRepositoryImpl"),
        patch("src.application.events.tasks_event_handlers.TaskRepositoryImpl"),
        patch("src.application.events.tasks_event_handlers.TaskService") as task_service_cls,
    ):
        task_service_cls.return_value.create_task = create_task_mock
        await create_system_task_for_cancelled_booking(event, session)

    create_task_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_show_creates_en_task_without_trace_in_description():
    booking = _booking_stub()
    trace_id = str(uuid4())
    event = DomainEvent(
        name="BOOKING_NO_SHOW",
        payload={"booking_id": str(booking.id), "trace_id": trace_id},
    )
    session = _mock_session_with_booking(booking)
    create_task_mock = AsyncMock()

    with (
        patch(
            "src.application.events.tasks_event_handlers._has_open_task_for_source_event",
            AsyncMock(return_value=False),
        ),
        patch("src.application.events.tasks_event_handlers.LeadRepositoryImpl") as lead_repo_cls,
        patch("src.application.events.tasks_event_handlers.TaskRepositoryImpl"),
        patch("src.application.events.tasks_event_handlers.TaskService") as task_service_cls,
    ):
        lead_repo_cls.return_value.get_lead_by_primary_booking_id = AsyncMock(return_value=None)
        task_service_cls.return_value.create_task = create_task_mock

        await create_system_task_for_no_show(event, session)

    create_task_mock.assert_awaited_once()
    kwargs = create_task_mock.await_args.kwargs
    assert kwargs["title"] == "Follow up on a patient no-show"
    assert kwargs["description"] == (
        "The patient did not attend. Contact them, find out why, "
        "and offer a new date and time."
    )
    assert "trace_id=" not in kwargs["description"]
    assert "event_id=" not in kwargs["description"]
    assert kwargs["trace_id"] == trace_id
    assert kwargs["source"] == "system"
    assert kwargs["booking_id"] == booking.id
