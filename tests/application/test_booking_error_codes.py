"""BE1: canonical code normalization for tools vs API."""

from src.application.booking_error_codes import normalize_booking_error_code
from src.application.dto.booking_dto import BookingErrorCode


def test_normalize_slot_conflict_to_slot_unavailable():
    assert normalize_booking_error_code("slot_conflict") == BookingErrorCode.SLOT_UNAVAILABLE


def test_normalize_legacy_tool_codes():
    assert normalize_booking_error_code("unexpected_error") == BookingErrorCode.SERVICE_UNAVAILABLE
    assert normalize_booking_error_code("unknown_code_xyz") == BookingErrorCode.VALIDATION_ERROR
