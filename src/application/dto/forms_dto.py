"""DTOs for digital forms, submissions and signatures."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DigitalFormFieldSchema(BaseModel):
    """Single field description inside DigitalFormTemplate.schema."""

    id: str = Field(..., description="Unique field key within form")
    label: str
    type: str = Field(
        ...,
        description="text|textarea|number|select|checkbox|date",
    )
    required: bool = False
    options: list[str] | None = None
    sensitive: bool = False


class DigitalFormTemplateSchema(BaseModel):
    """Top-level schema wrapper storing list of fields."""

    fields: list[DigitalFormFieldSchema] = Field(default_factory=list)


class DigitalFormTemplateBase(BaseModel):
    code: str = Field(..., description="Template code (e.g. health_questionnaire)")
    name: str
    description: str | None = None
    schema: DigitalFormTemplateSchema
    requires_signature: bool = False
    active: bool = True


class DigitalFormTemplateCreate(DigitalFormTemplateBase):
    pass


class DigitalFormTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    schema: DigitalFormTemplateSchema | None = None
    requires_signature: bool | None = None
    active: bool | None = None


class DigitalFormTemplateRead(DigitalFormTemplateBase):
    id: UUID
    clinic_id: UUID
    version: int

    class Config:
        from_attributes = True


class DigitalFormSubmissionRead(BaseModel):
    id: UUID
    clinic_id: UUID
    template_id: UUID
    patient_id: UUID | None
    booking_id: UUID | None
    submitted_at: datetime
    submitted_by: str
    data: dict[str, Any]
    signature_id: UUID | None

    class Config:
        from_attributes = True


class DigitalFormSubmissionListItem(DigitalFormSubmissionRead):
    """Submission with template code/name for list views."""

    template_code: str = ""
    template_name: str = ""


class ESignatureRead(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID | None
    digital_form_submission_id: UUID
    signed_at: datetime
    signer_name: str | None
    signer_role: str
    signature_type: str
    signature_payload: dict[str, Any]
    meta: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class DigitalFormSubmissionWithTemplateAndSignature(BaseModel):
    """Composite DTO for admin view of submission with template and signature."""

    submission: DigitalFormSubmissionRead
    template: DigitalFormTemplateRead
    signature: ESignatureRead | None = None


class SendLinkRequest(BaseModel):
    """Request body for POST /admin/forms/send-link."""

    patient_id: UUID | None = None
    booking_id: UUID | None = None
    template_id: UUID
    send_via: str = Field(
        ...,
        description="whatsapp | sms | copy_only",
        pattern="^(whatsapp|sms|copy_only)$",
    )


class SendLinkResponse(BaseModel):
    """Response for POST /admin/forms/send-link."""

    url: str
    sent: bool
    channel: str | None = None  # "whatsapp" | "sms" | null when copy_only or not sent

