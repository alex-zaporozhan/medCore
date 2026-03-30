"""DTOs for admin omnichannel chat API."""

from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from src.core.datetime_utils import to_iso8601_utc


class OmniMessageAttachmentDto(BaseModel):
    """Вложение в ленте omni: локальный файл (omni) или мост из PWA-чата (clinic_chat)."""

    id: UUID
    file_name: str
    content_type: str
    size_bytes: int = 0
    source: Literal["omni", "clinic_chat"] = "omni"
    conversation_id: UUID | None = None


class OmniMessageDto(BaseModel):
    id: UUID
    direction: str
    actor_type: str
    content: str
    message_content_type: str = "TEXT"
    attachments: list[OmniMessageAttachmentDto] = Field(default_factory=list)
    created_at: datetime | None
    ui_hidden: bool = False
    hidden_reason: str | None = None
    channel_id: UUID | None = None
    channel_type: str | None = None
    sender_admin_id: UUID | None = None
    delivery_status: str | None = None
    read_status: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str:
        return to_iso8601_utc(value) or ""


class OmniMessagesResponse(BaseModel):
    items: list[OmniMessageDto]


class SendOmniMessageRequest(BaseModel):
    content: str = Field(..., max_length=2000)
    reply_channel_id: UUID | None = Field(
        default=None,
        description="Optional explicit outbound channel; must belong to the clinic and support operator replies.",
    )

    @model_validator(mode="after")
    def validate_content(self):
        if not (self.content and self.content.strip()):
            raise ValueError("content must not be empty")
        return self


class OmniChatListItemDto(BaseModel):
    chat_id: UUID
    contact_id: UUID
    contact_name: str | None
    contact_primary_phone: str | None
    status: str
    last_message_at: datetime | None
    last_actor_type: str | None
    ai_mode: str | None = None
    assignee_admin_id: UUID | None = None
    assignee_name: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_message_at")
    def serialize_last_message_at(self, value: datetime | None) -> str:
        return to_iso8601_utc(value) or ""


class OmniChatsResponse(BaseModel):
    items: list[OmniChatListItemDto]
    total: int


class OmniChatDetailDto(BaseModel):
    """Single chat details for GET /admin/omni-chats/{chat_id}."""

    chat_id: UUID
    contact_id: UUID
    contact_name: str | None
    contact_primary_phone: str | None
    channel_id: UUID | None
    channel_type: str | None
    status: str
    ai_mode: str
    last_message_at: datetime | None
    last_actor_type: str | None
    created_at: datetime | None
    # CRM lead snapshot for this chat/contact (if any)
    lead_id: UUID | None = None
    lead_stage_id: UUID | None = None
    lead_stage_name: str | None = None
    lead_estimated_value: str | None = None
    lead_actual_value: str | None = None
    assignee_admin_id: UUID | None = None
    assignee_name: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_message_at", "created_at")
    def serialize_datetime(self, value: datetime | None) -> str:
        return to_iso8601_utc(value) or ""


class PatchOmniChatRequest(BaseModel):
    assignee_admin_id: UUID | None = None
    status: str | None = Field(None, max_length=32)

    @model_validator(mode="after")
    def validate_status(self):
        if self.status is None:
            return self
        allowed = {"OPEN", "WAITING_FOR_OPERATOR", "IN_PROGRESS", "CLOSED"}
        normalized = self.status.strip().upper()
        if normalized not in allowed:
            raise ValueError("status must be one of OPEN, WAITING_FOR_OPERATOR, IN_PROGRESS, CLOSED")
        self.status = normalized
        return self


class OmniQuickReplyDto(BaseModel):
    id: UUID
    clinic_id: UUID
    title: str
    body: str
    sort_order: int
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str:
        return to_iso8601_utc(value) or ""


class OmniQuickRepliesResponse(BaseModel):
    items: list[OmniQuickReplyDto]


class OmniQuickReplyCreateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    body: str = Field(..., max_length=8000)
    sort_order: int = 0

    @model_validator(mode="after")
    def validate_non_empty_fields(self):
        if not self.title or not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.body or not self.body.strip():
            raise ValueError("body must not be empty")
        return self


class OmniQuickReplyUpdateRequest(BaseModel):
    title: str | None = Field(None, max_length=255)
    body: str | None = Field(None, max_length=8000)
    sort_order: int | None = None

    @model_validator(mode="after")
    def validate_non_empty_optional_fields(self):
        if self.title is not None and not self.title.strip():
            raise ValueError("title must not be empty")
        if self.body is not None and not self.body.strip():
            raise ValueError("body must not be empty")
        return self


class HideOmniMessageRequest(BaseModel):
    reason: str = Field(..., max_length=500)

    @model_validator(mode="after")
    def validate_reason(self):
        if not (self.reason and self.reason.strip()):
            raise ValueError("reason must not be empty")
        return self

