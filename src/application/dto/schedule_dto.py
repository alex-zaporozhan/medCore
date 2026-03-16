"""DTOs for schedule representation."""

from datetime import date, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScheduleSlot(BaseModel):
    """Single time slot in doctor's schedule."""

    start_time: time
    end_time: time
    is_available: bool
    booking_id: UUID | None = None
    status: str | None = None


class DailySchedule(BaseModel):
    """Schedule for a single day."""

    doctor_id: UUID
    date: date
    slots: list[ScheduleSlot]

    model_config = ConfigDict(from_attributes=True)


class DoctorSlot(BaseModel):
    """Slot for one doctor in aggregated grid (time + optional booking)."""

    start_time: time
    end_time: time
    is_available: bool
    booking_id: UUID | None = None
    status: str | None = None


class AggregatedSchedule(BaseModel):
    """Aggregated schedule: multiple doctors × unified time grid. by_doctor keys are doctor_id str."""

    doctors: list[UUID]
    date: date
    times: list[time]
    by_doctor: dict[str, list[DoctorSlot]]


class SuggestSlotItem(BaseModel):
    """Single free slot for suggest-slots (start/end as HH:MM strings)."""

    start: str
    end: str


class SuggestSlotsResponse(BaseModel):
    """Response for GET suggest-slots: list of free time windows."""

    slots: list[SuggestSlotItem]

