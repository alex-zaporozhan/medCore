"""DTOs for doctor schedule config (working hours, absence)."""

from datetime import date, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkingHoursRead(BaseModel):
    """Working hours row (one weekday)."""

    id: UUID
    doctor_id: UUID
    weekday: int  # 0=Mon, 6=Sun
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)


class WorkingHoursCreate(BaseModel):
    """Create working hours for one weekday."""

    weekday: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time


class WorkingHoursUpdate(BaseModel):
    """Update working hours."""

    start_time: time | None = None
    end_time: time | None = None


class AbsenceRead(BaseModel):
    """Doctor absence (vacation) period."""

    id: UUID
    doctor_id: UUID
    date_from: date
    date_to: date
    reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AbsenceCreate(BaseModel):
    """Create absence period."""

    date_from: date
    date_to: date
    reason: str | None = Field(None, max_length=255)
