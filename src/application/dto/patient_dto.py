"""Patient DTOs."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class PatientRead(BaseModel):
    """Patient read DTO."""

    id: UUID
    clinic_id: UUID
    phone: str
    full_name: str | None = None
    email: str | None = None
    birth_date: date | None = None
    telegram_chat_id: str | None = None
    preferred_channel: str = "sms"

    model_config = ConfigDict(from_attributes=True)


class PatientCreate(BaseModel):
    """Patient create DTO. clinic_id optional: server uses default clinic when omitted."""

    clinic_id: UUID | None = None
    phone: str = Field(..., min_length=10, max_length=20)
    full_name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    birth_date: date | None = None
    telegram_chat_id: str | None = Field(None, max_length=100)
    preferred_channel: str = Field(default="sms", pattern="^(sms|telegram|email)$")


class PatientUpdate(BaseModel):
    """Patient update DTO."""

    phone: str | None = Field(None, min_length=10, max_length=20)
    full_name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    birth_date: date | None = None
    telegram_chat_id: str | None = Field(None, max_length=100)
    preferred_channel: str | None = Field(None, pattern="^(sms|telegram|email)$")
