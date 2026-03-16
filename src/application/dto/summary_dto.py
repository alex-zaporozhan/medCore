"""DTOs for HoverCard summary endpoints (patient, doctor)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PatientSummaryRead(BaseModel):
    """Lightweight patient summary for HoverCard."""

    id: UUID
    full_name: str | None
    phone: str
    ltv: Decimal
    next_visit_at: datetime | None
    next_visit_doctor_name: str | None

    model_config = ConfigDict(from_attributes=True)


class DoctorSummaryRead(BaseModel):
    """Lightweight doctor summary for HoverCard."""

    id: UUID
    full_name: str
    phone: str | None
    specialization: str | None

    model_config = ConfigDict(from_attributes=True)
