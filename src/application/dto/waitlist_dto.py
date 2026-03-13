"""Waitlist DTOs."""

from datetime import date, time
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class WaitlistEntryRead(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID | None = None
    speciality: str | None = None
    time_preferences_json: dict | None = None
    preferred_date: date | None = None
    preferred_time: time | None = None
    priority: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class WaitlistEntryCreate(BaseModel):
    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID | None = None
    speciality: str | None = None
    time_preferences_json: dict | None = None
    preferred_date: date | None = None
    preferred_time: time | None = None
    priority: int = 0
    status: str = Field(default="waiting", max_length=32)


class WaitlistEntryUpdate(BaseModel):
    patient_id: UUID | None = None
    doctor_id: UUID | None = None
    speciality: str | None = None
    time_preferences_json: dict | None = None
    preferred_date: date | None = None
    preferred_time: time | None = None
    priority: int | None = None
    status: str | None = None


class QueuePolicyRead(BaseModel):
    id: UUID
    clinic_id: UUID
    mode: str
    broadcast_size: int
    response_timeout_minutes: int
    max_notifications_per_entry: int | None = None

    model_config = ConfigDict(from_attributes=True)


class QueuePolicyUpdate(BaseModel):
    mode: str | None = None
    broadcast_size: int | None = None
    response_timeout_minutes: int | None = None
    max_notifications_per_entry: int | None = None
