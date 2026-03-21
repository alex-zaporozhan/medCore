"""Structured BookingErrorResponse mapping for completion facade."""

from uuid import uuid4

from src.application.dto.booking_dto import BookingCompletionResult, BookingErrorCode
from src.application.errors import booking_error_from_completion_result


def test_completion_booking_not_found_maps():
    r = BookingCompletionResult(
        success=False,
        booking_id=uuid4(),
        final_status="x",
        error_code="booking_not_found",
        error_message="gone",
    )
    err = booking_error_from_completion_result(r, None, trace_id="t1")
    assert err.code == BookingErrorCode.BOOKING_NOT_FOUND
    assert err.trace_id == "t1"


def test_completion_erp_like_code_maps_service_unavailable():
    r = BookingCompletionResult(
        success=False,
        booking_id=uuid4(),
        final_status="x",
        error_code="ERP_NO_CASHBOX",
        error_message="erp",
    )
    err = booking_error_from_completion_result(r, None, trace_id=None)
    assert err.code == BookingErrorCode.SERVICE_UNAVAILABLE
