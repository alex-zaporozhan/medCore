"""Discount DTOs."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DiscountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    discount_type: str = Field(..., pattern="^(first_visit|service|doctor|period)$")
    service_id: UUID | None = None
    doctor_id: UUID | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    percent_off: Decimal | None = Field(None, ge=0, le=100)
    amount_off: Decimal | None = Field(None, ge=0)
    is_active: bool = True


class DiscountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    discount_type: str | None = Field(None, pattern="^(first_visit|service|doctor|period)$")
    service_id: UUID | None = None
    doctor_id: UUID | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    percent_off: Decimal | None = Field(None, ge=0, le=100)
    amount_off: Decimal | None = Field(None, ge=0)
    is_active: bool | None = None


class DiscountRead(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    discount_type: str
    service_id: UUID | None
    doctor_id: UUID | None
    valid_from: date | None
    valid_until: date | None
    percent_off: Decimal | None
    amount_off: Decimal | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
