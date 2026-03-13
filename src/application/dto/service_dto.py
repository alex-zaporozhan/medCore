"""Service DTOs."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ServiceRead(BaseModel):
    """Service read DTO."""

    id: UUID
    clinic_id: UUID
    name: str
    category: str
    description: str | None = None
    price: Decimal
    duration_minutes: int
    is_active: bool = True
    # Pricing fields are populated at service layer; defaults allow validating from ORM entities.
    base_price: Decimal | None = None
    effective_price: Decimal | None = None
    has_active_discount: bool = False
    discount_id: UUID | None = None
    discount_type: str | None = None
    discount_label: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ServiceCreate(BaseModel):
    """Service create DTO."""

    clinic_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=Decimal("0"))
    duration_minutes: int = Field(default=30, ge=1)
    is_active: bool = True


class ServiceUpdate(BaseModel):
    """Service update DTO."""

    name: str | None = Field(None, min_length=1, max_length=255)
    category: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    price: Decimal | None = Field(None, gt=Decimal("0"))
    duration_minutes: int | None = Field(None, ge=1)
    is_active: bool | None = None


class ServiceDoctorLink(BaseModel):
    """Link between service and doctor in admin payloads."""

    doctor_id: UUID
    custom_price: Decimal | None = Field(default=None, gt=Decimal("0"))
    is_active: bool = True


class AdminServiceRead(BaseModel):
    """Admin view of service with linked doctors."""

    service: ServiceRead
    doctors: list[ServiceDoctorLink]


class AdminServiceCreate(BaseModel):
    """Admin create DTO with doctor links."""

    service: ServiceCreate
    doctors: list[ServiceDoctorLink] = Field(default_factory=list)


class AdminServiceUpdate(BaseModel):
    """Admin update DTO with doctor links."""

    service: ServiceUpdate
    doctors: list[ServiceDoctorLink] = Field(default_factory=list)

