"""DTOs for rich entity cards (Patient, Booking, Doctor, Service)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ----- Patient card -----
class PatientCardPatient(BaseModel):
    """Patient block for card (with computed ltv, bonus_balance)."""
    id: UUID
    full_name: str | None
    phone: str
    email: str | None = None
    ltv: Decimal = Decimal("0")
    bonus_balance: Decimal = Decimal("0")
    tags: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class PatientCardVisitItem(BaseModel):
    id: UUID
    date: date
    doctor_name: str
    service_name: str
    status: str
    amount: Decimal
    nps: float | None = None


class PatientCardFinanceItem(BaseModel):
    type: str  # "payment" | "refund" | "subscription"
    amount: Decimal
    date: datetime
    description: str | None = None


class PatientCardNoteItem(BaseModel):
    """Placeholder for medical notes (no entity yet)."""
    id: str
    content: str
    created_at: datetime


class PatientCardCommItem(BaseModel):
    channel: str
    template: str
    status: str
    sent_at: datetime | None = None
    created_at: datetime


class PatientCardResponse(BaseModel):
    patient: PatientCardPatient
    visits: list[PatientCardVisitItem] = []
    finances: list[PatientCardFinanceItem] = []
    notes: list[PatientCardNoteItem] = []
    comms: list[PatientCardCommItem] = []


# ----- Booking card -----
class BookingCardServiceItem(BaseModel):
    service_id: UUID
    service_name: str
    amount: Decimal | None = None


class BookingCardConsumableItem(BaseModel):
    product_id: UUID
    product_name: str | None = None
    quantity_per_service: Decimal
    unit: str


class BookingCardTaskItem(BaseModel):
    id: UUID
    title: str
    status: str
    priority: str
    due_at: datetime | None = None


class BookingCardResponse(BaseModel):
    booking: dict  # BookingRead-compatible
    services: list[BookingCardServiceItem] = []
    consumables: list[BookingCardConsumableItem] = []
    tasks: list[BookingCardTaskItem] = []


# ----- Doctor card -----
class DoctorCardWorkingHoursItem(BaseModel):
    weekday: int
    start_time: str
    end_time: str


class DoctorCardPayrollItem(BaseModel):
    """Payroll policy summary (if exists)."""
    id: UUID
    name: str | None = None
    type: str | None = None


class DoctorCardServiceDoctorItem(BaseModel):
    service_id: UUID
    service_name: str
    custom_price: Decimal | None = None
    is_active: bool


class DoctorCardResponse(BaseModel):
    doctor: dict  # DoctorRead-compatible
    working_hours: list[DoctorCardWorkingHoursItem] = []
    payroll_policy: DoctorCardPayrollItem | None = None
    services: list[DoctorCardServiceDoctorItem] = []  # services this doctor provides


# ----- Service card -----
class ServiceCardDoctorItem(BaseModel):
    doctor_id: UUID
    doctor_name: str
    custom_price: Decimal | None = None
    is_active: bool


class ServiceCardConsumableItem(BaseModel):
    product_id: UUID
    product_name: str | None = None
    quantity_per_service: Decimal
    unit: str


class ServiceCardResponse(BaseModel):
    service: dict  # ServiceRead-compatible
    doctors: list[ServiceCardDoctorItem] = []
    consumables: list[ServiceCardConsumableItem] = []
    online_booking_enabled: bool | None = None
