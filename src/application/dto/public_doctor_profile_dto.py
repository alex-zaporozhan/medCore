"""Public doctor profile DTOs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PublicDoctorProfileRead(BaseModel):
    id: UUID
    clinic_id: UUID
    doctor_id: UUID
    doctor_slug: str
    is_published: bool
    public_photo_url: str | None = None
    short_bio: str | None = None
    about_md: str | None = None
    languages: dict | None = None
    education: dict | None = None
    certifications: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicDoctorProfileCreate(BaseModel):
    doctor_id: UUID
    doctor_slug: str = Field(..., min_length=3, max_length=120)
    is_published: bool = False
    public_photo_url: str | None = Field(None, max_length=500)
    short_bio: str | None = Field(None, max_length=500)
    about_md: str | None = None
    languages: dict | None = None
    education: dict | None = None
    certifications: dict | None = None


class PublicDoctorProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doctor_slug: str | None = Field(None, min_length=3, max_length=120)
    is_published: bool | None = None
    public_photo_url: str | None = Field(None, max_length=500)
    short_bio: str | None = Field(None, max_length=500)
    about_md: str | None = None
    languages: dict | None = None
    education: dict | None = None
    certifications: dict | None = None


class PublicDoctorProfilePublicDto(BaseModel):
    clinic_id: str
    clinic_slug: str
    doctor_id: str
    doctor_slug: str
    doctor_full_name: str
    doctor_specialization: str
    doctor_photo_url: str | None = None
    doctor_display_role: str | None = None

    public_photo_url: str | None = None
    short_bio: str | None = None
    about_md: str | None = None
    languages: dict | None = None
    education: dict | None = None
    certifications: dict | None = None

