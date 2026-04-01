"""Patient medical record DTOs (admin-only)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PatientMedicalVisitCreate(BaseModel):
    visit_date: date
    doctor_id: UUID | None = None
    booking_id: UUID | None = None
    notes_md: str | None = None


class PatientMedicalVisitRead(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID | None = None
    booking_id: UUID | None = None
    visit_date: date
    notes_md: str | None = None
    created_by_admin_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientDiagnosisCreate(BaseModel):
    diagnosis_date: date
    visit_id: UUID | None = None
    icd10_code: str | None = Field(None, max_length=16)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class PatientDiagnosisRead(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    visit_id: UUID | None = None
    diagnosis_date: date
    icd10_code: str | None = None
    title: str
    description: str | None = None
    author_admin_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientMedicalFileRead(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    visit_id: UUID | None = None
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

