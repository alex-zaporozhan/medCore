"""DTOs for admin lead logs (immutable snapshots)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.core.datetime_utils import to_iso8601_utc


class OmniLeadLogListItemDto(BaseModel):
    id: UUID
    clinic_id: UUID
    omni_chat_id: UUID
    contact_id: UUID
    contact_name: str | None = None
    contact_primary_phone: str | None = None
    opened_by_admin_id: UUID | None = None
    opened_by_admin_name: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime
    title: str
    outcome: str = Field(..., description="BOOKED | NOT_BOOKED | UNKNOWN")
    lead_id: UUID | None = None
    booking_id: UUID | None = None
    patient_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("opened_at", "closed_at")
    def serialize_datetime(self, value: datetime | None) -> str:
        return to_iso8601_utc(value) or ""


class OmniLeadLogDetailDto(OmniLeadLogListItemDto):
    transcript_text: str
    transcript_json: dict = Field(default_factory=dict)

