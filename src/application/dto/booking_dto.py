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
    """Booking create DTO for admin flow. When waitlist_entry_id is set, patient_id/doctor_id/date/time may be taken from the waitlist entry."""

    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID
    service_id: UUID
    appointment_date: date
    appointment_time: time
    status: str = Field(default="pending")
    prepayment_amount: Decimal | None = None
    notes: str | None = Field(None, max_length=2000)
    waitlist_entry_id: UUID | None = None


class BookingRescheduleRequest(BaseModel):
    """Booking reschedule DTO (time only or time + doctor)."""

    appointment_date: date
    appointment_time: time
    to_doctor_id: UUID | None = None


class EligibleSubscriptionItem(BaseModel):
    """One eligible subscription for checkout (B4.4)."""

    customer_subscription_id: UUID
    package_name: str
    remaining_visits: int | None = None
    remaining_amount: Decimal | None = None


class CheckoutInfoResponse(BaseModel):
    """Response for GET bookings/{id}/checkout-info (B4.4)."""

    eligible_subscriptions: list[EligibleSubscriptionItem]


class CompleteBookingRequest(BaseModel):
    """Optional body for complete booking (B4.4): use specific subscription."""

    use_subscription_id: UUID | None = None

