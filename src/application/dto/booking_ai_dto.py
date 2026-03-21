"""DTOs for Booking AI tools (BKG_AI_TOOLS_006)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GetAvailableSlotsInput(BaseModel):
    clinic_id: UUID
    service_id: UUID | None = None
    doctor_id: UUID | None = None
    date_from: date
    date_to: date


class AvailableSlot(BaseModel):
    clinic_id: UUID
    doctor_id: UUID
    service_id: UUID | None = None
    date: date
    start_time: str
    end_time: str | None = None


class BookingSummary(BaseModel):
    """Safe minimal booking representation for AI layer (tokens instead of raw ids)."""

    booking_token: str
    clinic_id: UUID
    patient_token: str
    doctor_id: UUID
    service_id: UUID
    appointment_date: date
    appointment_time: str
    status: str
    notes: str | None = None


class CreateBookingInput(BaseModel):
    clinic_id: UUID
    patient_token: str | None = Field(
        default=None,
        description="Opaque patient token PATIENT#<uuid> (preferred).",
    )
    patient_id: UUID | None = Field(
        default=None,
        description="DEPRECATED. Use patient_token instead.",
    )
    doctor_id: UUID
    service_id: UUID
    appointment_start: datetime = Field(
        description="Start of appointment in ISO 8601 format (UTC or clinic local time)."
    )
    notes: str | None = Field(default=None, max_length=2000)
    source: str = Field(default="ai_agent", description="Logical source marker for analytics/audit.")


class CreateBookingOutput(BaseModel):
    booking: BookingSummary


class CancelBookingInput(BaseModel):
    clinic_id: UUID
    booking_token: str = Field(description="Opaque booking token BOOKING#<uuid>.")
    reason: str | None = Field(default=None, max_length=500)


class CancelBookingOutput(BaseModel):
    success: bool
    booking: BookingSummary | None = None
    error_code: str | None = None
    error_message: str | None = None


class RescheduleBookingInput(BaseModel):
    clinic_id: UUID
    booking_token: str = Field(description="Opaque booking token BOOKING#<uuid>.")
    new_appointment_start: datetime
    to_doctor_id: UUID | None = None


class RescheduleBookingOutput(BaseModel):
    booking: BookingSummary

