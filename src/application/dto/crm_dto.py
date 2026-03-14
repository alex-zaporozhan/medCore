"""CRM Kanban DTOs: pipelines, stages, leads, notes."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LeadPipelineDto(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    description: str | None = None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadStageDto(BaseModel):
    id: UUID
    clinic_id: UUID
    pipeline_id: UUID
    order: int
    code: str
    name: str
    probability: int
    color: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadNoteDto(BaseModel):
    id: UUID
    clinic_id: UUID
    lead_id: UUID
    author_admin_id: UUID
    text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadCardDto(BaseModel):
    id: UUID
    clinic_id: UUID
    pipeline_id: UUID
    stage_id: UUID
    omnichannel_contact_id: UUID | None = None
    patient_id: UUID | None = None
    primary_booking_id: UUID | None = None
    visit_attribution_id: UUID | None = None
    title: str
    source: str
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None
    estimated_value: Decimal
    actual_value: Decimal
    status: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    lost_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    items: list[LeadCardDto]
    total: int


class LeadDetailsResponse(BaseModel):
    lead: LeadCardDto
    notes: list[LeadNoteDto]


class ChangeLeadStageRequest(BaseModel):
    new_stage_id: UUID


class CreateLeadNoteRequest(BaseModel):
    text: str

