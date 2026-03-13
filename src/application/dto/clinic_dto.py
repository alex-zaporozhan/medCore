"""Clinic DTOs."""

from datetime import time, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BusinessType = Literal["stomatology", "clinic", "beauty_salon", "barbershop", "nail_salon", "massage_salon", "other"]


class BusinessLexiconRead(BaseModel):
    """Computed business lexicon for a clinic."""

    business_type: str
    business_type_custom_name: str | None = None
    person_label_singular: str
    person_label_plural: str
    staff_label_plural: str
    role_display: dict[str, str]


class PaymentOptionRead(BaseModel):
    """One payment option (gateway) offered to the client for prepayment."""

    gateway_id: str
    display_name: str


class ClinicRead(BaseModel):
    """Clinic read DTO."""

    id: UUID
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    workday_start: time
    workday_end: time
    slot_duration_minutes: int
    prepayment_amount: Decimal
    prepayment_enabled: bool = False
    payment_gateway: str = "yookassa"
    payment_gateway_custom_name: str | None = None
    payment_options: list[PaymentOptionRead] = Field(default_factory=list)
    yookassa_shop_id: str | None = None
    theme_primary_color: str | None = None
    theme_logo_url: str | None = None
    theme_font_family: str | None = None
    business_type: str = "stomatology"
    business_type_custom_name: str | None = None
    person_label_singular: str | None = None
    person_label_plural: str | None = None
    staff_label_plural: str | None = None
    created_at: datetime
    updated_at: datetime
    business_lexicon: BusinessLexiconRead | None = None

    model_config = ConfigDict(from_attributes=True)


class ClinicCreate(BaseModel):
    """Clinic create DTO."""

    name: str = Field(..., max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    address: str | None = Field(None, max_length=500)
    workday_start: time | None = None
    workday_end: time | None = None
    slot_duration_minutes: int | None = None
    prepayment_amount: Decimal | None = None
    business_type: BusinessType = "stomatology"
    business_type_custom_name: str | None = Field(None, max_length=255)
    person_label_singular: str | None = Field(None, max_length=50)
    person_label_plural: str | None = Field(None, max_length=50)
    staff_label_plural: str | None = Field(None, max_length=50)


class ClinicUpdate(BaseModel):
    """Clinic update DTO (partial)."""

    name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    address: str | None = Field(None, max_length=500)
    workday_start: time | None = None
    workday_end: time | None = None
    slot_duration_minutes: int | None = None
    prepayment_amount: Decimal | None = None
    prepayment_enabled: bool | None = None
    payment_gateway: str | None = None
    payment_gateway_custom_name: str | None = None
    yookassa_shop_id: str | None = Field(None, max_length=100)
    yookassa_secret_key: str | None = Field(None, max_length=200)
    theme_primary_color: str | None = Field(None, max_length=50)
    theme_logo_url: str | None = Field(None, max_length=500)
    theme_font_family: str | None = Field(None, max_length=100)
    business_type: BusinessType | None = None
    business_type_custom_name: str | None = Field(None, max_length=255)
    person_label_singular: str | None = Field(None, max_length=50)
    person_label_plural: str | None = Field(None, max_length=50)
    staff_label_plural: str | None = Field(None, max_length=50)

