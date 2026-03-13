"""Booking DTOs."""

from datetime import date, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class BookingRead(BaseModel):
    """Booking read DTO."""

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID
    service_id: UUID
    appointment_date: date
    appointment_time: time
    status: str
    prepayment_amount: Decimal
    payment_id: UUID | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BookingCreatePatient(BaseModel):
    """Booking create DTO for patient flow."""

    clinic_id: UUID
    doctor_id: UUID
    service_id: UUID
    appointment_date: date
    appointment_time: time
    notes: str | None = Field(None, max_length=2000)


class BookingCreateAdmin(BaseModel):
    """Booking create DTO for admin flow."""

    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID
    service_id: UUID
    appointment_date: date
    appointment_time: time
    status: str = Field(default="pending")
    prepayment_amount: Decimal | None = None
    notes: str | None = Field(None, max_length=2000)


class BookingRescheduleRequest(BaseModel):
    """Booking reschedule DTO (time only or time + doctor)."""

    appointment_date: date
    appointment_time: time
    to_doctor_id: UUID | None = None

