"""Doctor DTOs."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

SpecialistRole = Literal["doctor", "nurse", "master", "therapist", "other"]


class DoctorRead(BaseModel):
    """Doctor read DTO."""

    id: UUID
    clinic_id: UUID
    full_name: str
    specialization: str
    photo_url: str | None = None
    rating: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), le=Decimal("5.0"))
    experience_years: int | None = None
    is_active: bool = True
    specialist_role: str = "doctor"
    specialist_role_custom_name: str | None = None
    display_role: str = "Врач"

    model_config = ConfigDict(from_attributes=True)


class DoctorCreate(BaseModel):
    """Doctor create DTO. clinic_id optional: server uses default clinic when omitted."""

    clinic_id: UUID | None = None
    full_name: str = Field(..., min_length=1, max_length=255)
    specialization: str = Field(..., min_length=1, max_length=255)
    photo_url: str | None = Field(None, max_length=500)
    rating: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), le=Decimal("5.0"))
    experience_years: int | None = Field(None, ge=0)
    is_active: bool = True
    specialist_role: SpecialistRole = "doctor"
    specialist_role_custom_name: str | None = Field(None, max_length=255)


class DoctorUpdate(BaseModel):
    """Doctor update DTO."""

    full_name: str | None = Field(None, min_length=1, max_length=255)
    specialization: str | None = Field(None, min_length=1, max_length=255)
    photo_url: str | None = Field(None, max_length=500)
    rating: Decimal | None = Field(None, ge=Decimal("0.0"), le=Decimal("5.0"))
    experience_years: int | None = Field(None, ge=0)
    is_active: bool | None = None
    specialist_role: SpecialistRole | None = None
    specialist_role_custom_name: str | None = Field(None, max_length=255)