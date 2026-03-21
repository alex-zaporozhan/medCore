"""Canonical booking / payment error codes (BKG_ERRORS_005, QA_ARCH W7 BE1).

API responses use :class:`BookingErrorCode` in ``booking_dto``.
AI tools historically returned overlapping string codes; normalize tool strings to the
same enum values for metrics, analytics, and UI.
"""

from __future__ import annotations

from src.application.dto.booking_dto import BookingErrorCode

# Tool / legacy string → API enum (single source of truth for BE1 / J1 alignment).
_TOOL_AND_LEGACY_CODE_TO_BOOKING: dict[str, BookingErrorCode] = {
    # API
    "slot_unavailable": BookingErrorCode.SLOT_UNAVAILABLE,
    "patient_not_found": BookingErrorCode.PATIENT_NOT_FOUND,
    "payment_failed": BookingErrorCode.PAYMENT_FAILED,
    "prepayment_required": BookingErrorCode.PREPAYMENT_REQUIRED,
    "validation_error": BookingErrorCode.VALIDATION_ERROR,
    "service_unavailable": BookingErrorCode.SERVICE_UNAVAILABLE,
    "booking_not_found": BookingErrorCode.BOOKING_NOT_FOUND,
    "clinic_mismatch": BookingErrorCode.CLINIC_MISMATCH,
    "booking_status_invalid": BookingErrorCode.BOOKING_STATUS_INVALID,
    "payment_not_allowed": BookingErrorCode.PAYMENT_NOT_ALLOWED,
    # AI tools (tools_booking.py) — aligned names
    "slot_conflict": BookingErrorCode.SLOT_UNAVAILABLE,
    "invalid_args": BookingErrorCode.VALIDATION_ERROR,
    "invalid_patient_token": BookingErrorCode.VALIDATION_ERROR,
    "invalid_booking_token": BookingErrorCode.VALIDATION_ERROR,
    "patient_required": BookingErrorCode.VALIDATION_ERROR,
    "unexpected_error": BookingErrorCode.SERVICE_UNAVAILABLE,
    "invalid_status_for_cancel": BookingErrorCode.BOOKING_STATUS_INVALID,
    "cannot_cancel_past": BookingErrorCode.VALIDATION_ERROR,
    "invalid_status_for_reschedule": BookingErrorCode.BOOKING_STATUS_INVALID,
}


def normalize_booking_error_code(raw: str) -> BookingErrorCode:
    """Map tool or legacy string to :class:`BookingErrorCode` (default: validation)."""
    key = (raw or "").strip().lower()
    return _TOOL_AND_LEGACY_CODE_TO_BOOKING.get(key, BookingErrorCode.VALIDATION_ERROR)


def all_canonical_code_values() -> list[str]:
    """Stable list for OpenAPI enum / docs."""
    return sorted({c.value for c in BookingErrorCode})
