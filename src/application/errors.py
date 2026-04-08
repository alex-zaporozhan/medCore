from __future__ import annotations

from typing import Any

from src.application.dto.booking_dto import (
    BookingCompletionResult,
    BookingErrorCode,
    BookingErrorResponse,
)
from src.core.context import RequestContext
from src.core.patient_messages import (
    BOOKING_CLINIC_MISMATCH_PATIENT,
    BOOKING_ENTITY_CLINIC_MISMATCH,
    BOOKING_SLOT_ALREADY_BOOKED,
    BOOKING_DOCTOR_DOES_NOT_PROVIDE_SERVICE,
    BOOKING_INVALID_STATUS,
    BOOKING_STATUS_PATCH_NOT_ALLOWED,
    BOOKING_STATUS_REQUIRES_NARROW_ENDPOINT,
    BOOKING_CANNOT_CANCEL_STATUS,
    BOOKING_CANNOT_CANCEL_PAST,
    BOOKING_CANNOT_RESCHEDULE_CANCELLED,
    BOOKING_WAITLIST_CONVERSION_FAILED,
    PAYMENT_CANCELLED_BOOKING,
    PAYMENT_ALREADY_CONFIRMED,
    PAYMENT_BOOKING_NOT_FOUND,
)


def booking_error_from_value_error(
    exc: ValueError,
    ctx: RequestContext | None,
) -> BookingErrorResponse:
    """Map booking-related ValueError to BookingErrorResponse."""
    message = str(exc)
    details: dict[str, Any] | None = None
    code = BookingErrorCode.VALIDATION_ERROR

    if message == BOOKING_SLOT_ALREADY_BOOKED:
        code = BookingErrorCode.SLOT_UNAVAILABLE
    elif message in {BOOKING_CLINIC_MISMATCH_PATIENT, BOOKING_ENTITY_CLINIC_MISMATCH}:
        code = BookingErrorCode.CLINIC_MISMATCH
        details = {"reason": "clinic_mismatch"}
    elif message == BOOKING_DOCTOR_DOES_NOT_PROVIDE_SERVICE:
        code = BookingErrorCode.VALIDATION_ERROR
        details = {"reason": "doctor_not_provides_service"}
    elif message == BOOKING_STATUS_PATCH_NOT_ALLOWED:
        code = BookingErrorCode.VALIDATION_ERROR
        details = {"reason": "booking_status_patch_deprecated", "use": "PUT /api/v1/admin/bookings/{id}/status"}
    elif message == BOOKING_STATUS_REQUIRES_NARROW_ENDPOINT:
        code = BookingErrorCode.VALIDATION_ERROR
        details = {"reason": "booking_status_narrow_endpoint_required"}
    elif message in {BOOKING_INVALID_STATUS, BOOKING_CANNOT_CANCEL_STATUS}:
        code = BookingErrorCode.BOOKING_STATUS_INVALID
    elif message in {BOOKING_CANNOT_CANCEL_PAST, BOOKING_CANNOT_RESCHEDULE_CANCELLED}:
        code = BookingErrorCode.VALIDATION_ERROR
    elif message == BOOKING_WAITLIST_CONVERSION_FAILED:
        code = BookingErrorCode.VALIDATION_ERROR
        details = {"reason": "waitlist_conversion_failed"}

    return BookingErrorResponse(
        code=code,
        message=message,
        details=details,
        trace_id=getattr(ctx, "trace_id", None) if ctx is not None else None,
    )


def payment_error_from_lookup_error(
    exc: LookupError,
    ctx: RequestContext | None,
) -> BookingErrorResponse:
    """Map payment-related LookupError to BookingErrorResponse."""
    message = str(exc) or PAYMENT_BOOKING_NOT_FOUND
    return BookingErrorResponse(
        code=BookingErrorCode.BOOKING_NOT_FOUND,
        message=message,
        trace_id=getattr(ctx, "trace_id", None) if ctx is not None else None,
    )


def payment_error_from_value_error(
    exc: ValueError,
    ctx: RequestContext | None,
) -> BookingErrorResponse:
    """Map payment-related ValueError to BookingErrorResponse."""
    msg = str(exc)
    if msg in {PAYMENT_CANCELLED_BOOKING, PAYMENT_ALREADY_CONFIRMED}:
        code = BookingErrorCode.PAYMENT_NOT_ALLOWED
    elif msg == PAYMENT_BOOKING_NOT_FOUND:
        code = BookingErrorCode.BOOKING_NOT_FOUND
    else:
        code = BookingErrorCode.PAYMENT_FAILED

    return BookingErrorResponse(
        code=code,
        message=msg,
        trace_id=getattr(ctx, "trace_id", None) if ctx is not None else None,
    )


def booking_error_from_completion_result(
    result: BookingCompletionResult,
    ctx: RequestContext | None,
    *,
    trace_id: str | None = None,
) -> BookingErrorResponse:
    """Map BookingCompletionService failure to BookingErrorResponse (admin complete / retry)."""
    raw = (result.error_code or "validation_error").strip()
    message = result.error_message or "Cannot complete booking"
    details: dict[str, Any] | None = {"completion_error_code": raw}

    if raw == "booking_not_found":
        code = BookingErrorCode.BOOKING_NOT_FOUND
    elif raw == "invalid_status":
        code = BookingErrorCode.BOOKING_STATUS_INVALID
    elif raw in {"missing_required_forms", "loyalty_apply_failed"}:
        code = BookingErrorCode.VALIDATION_ERROR
    elif raw == "unexpected_error" or "erp" in raw.lower() or "node" in raw.lower():
        code = BookingErrorCode.SERVICE_UNAVAILABLE
    else:
        code = BookingErrorCode.VALIDATION_ERROR

    tid = trace_id
    if tid is None and ctx is not None:
        tid = getattr(ctx, "trace_id", None)

    return BookingErrorResponse(
        code=code,
        message=message,
        details=details,
        trace_id=tid,
    )

