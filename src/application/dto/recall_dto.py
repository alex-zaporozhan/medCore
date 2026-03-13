"""Recall DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecallSegmentRead(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    filter_json: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecallSegmentCreate(BaseModel):
    name: str = Field(..., max_length=255)
    filter_json: dict | None = None


class RecallSegmentUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    filter_json: dict | None = None


class RecallSegmentWithCount(RecallSegmentRead):
    patient_count: int = 0


class RecallTemplateRead(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    channel: str
    subject: str | None = None
    body_template: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecallTemplateCreate(BaseModel):
    name: str = Field(..., max_length=255)
    channel: str = Field(..., max_length=32)
    subject: str | None = Field(None, max_length=500)
    body_template: str = Field(..., min_length=1)


class RecallTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    channel: str | None = Field(None, max_length=32)
    subject: str | None = Field(None, max_length=500)
    body_template: str | None = None


class RecallCampaignRead(BaseModel):
    id: UUID
    clinic_id: UUID
    segment_id: UUID
    template_id: UUID
    name: str
    status: str
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecallCampaignCreate(BaseModel):
    segment_id: UUID
    template_id: UUID
    name: str = Field(..., max_length=255)
    status: str = Field(default="draft", max_length=32)
    scheduled_at: datetime | None = None


class RecallCampaignUpdate(BaseModel):
    segment_id: UUID | None = None
    template_id: UUID | None = None
    name: str | None = Field(None, max_length=255)
    status: str | None = Field(None, max_length=32)
    scheduled_at: datetime | None = None


class RecallAutomationRead(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    trigger_type: str
    trigger_config_json: dict | None = None
    segment_id: UUID | None = None
    template_id: UUID
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecallAutomationCreate(BaseModel):
    name: str = Field(..., max_length=255)
    trigger_type: str = Field(..., max_length=64)
    trigger_config_json: dict | None = None
    segment_id: UUID | None = None
    template_id: UUID
    enabled: bool = True


class RecallAutomationUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    trigger_type: str | None = Field(None, max_length=64)
    trigger_config_json: dict | None = None
    segment_id: UUID | None = None
    template_id: UUID | None = None
    enabled: bool | None = None


class RecallLogRead(BaseModel):
    id: UUID
    clinic_id: UUID
    campaign_id: UUID | None = None
    automation_id: UUID | None = None
    patient_id: UUID
    channel: str
    status: str
    sent_at: datetime | None = None
    error: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
