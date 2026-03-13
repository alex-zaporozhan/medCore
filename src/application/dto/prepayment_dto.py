"""Prepayment DTOs."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class PrepaymentPolicyRead(BaseModel):
    id: UUID
    clinic_id: UUID
    scope_type: str
    scope_doctor_id: UUID | None = None
    scope_service_id: UUID | None = None
    mode: str
    amount_type: str
    min_amount: Decimal
    deadline_hours_before_visit: int | None = None
    priority: int
    enabled: bool

    model_config = ConfigDict(from_attributes=True)


class PrepaymentPolicyCreate(BaseModel):
    clinic_id: UUID
    scope_type: str = Field(..., max_length=32)
    scope_doctor_id: UUID | None = None
    scope_service_id: UUID | None = None
    mode: str = Field(..., max_length=16)
    amount_type: str = Field(..., max_length=16)
    min_amount: Decimal = Field(default=Decimal("0"))
    deadline_hours_before_visit: int | None = None
    priority: int = 0
    enabled: bool = True


class PrepaymentPolicyUpdate(BaseModel):
    scope_type: str | None = None
    scope_doctor_id: UUID | None = None
    scope_service_id: UUID | None = None
    mode: str | None = None
    amount_type: str | None = None
    min_amount: Decimal | None = None
    deadline_hours_before_visit: int | None = None
    priority: int | None = None
    enabled: bool | None = None
