"""Chat DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from src.core.datetime_utils import to_iso8601_utc


class ChatAttachmentBrief(BaseModel):
    id: UUID
    file_name: str
    content_type: str
    size_bytes: int

    model_config = ConfigDict(from_attributes=True)


class MessageDto(BaseModel):
    id: UUID
    sender_type: str
    message_type: str = "text"
    body: str
    sticker_key: str | None = None
    created_at: datetime | None
    is_mine: bool
    attachments: list[ChatAttachmentBrief] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str:
        return to_iso8601_utc(value) or ""


class ConversationResponse(BaseModel):
    conversation_id: UUID
    unread_by_patient_count: int
    unread_by_admin_count: int
    last_message_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class MessagesResponse(BaseModel):
    items: list[MessageDto]
    next_cursor: UUID | None


class SendMessageRequest(BaseModel):
    message_type: str = Field(default="text", pattern="^(text|sticker)$")
    body: str = Field(default="", max_length=2000)
    sticker_key: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def check_sticker_or_body(self):
        if self.message_type == "sticker":
            if not self.sticker_key or not self.sticker_key.strip():
                raise ValueError("sticker_key is required when message_type is sticker")
        else:
            if not (self.body and self.body.strip()):
                raise ValueError("body is required when message_type is text")
        return self


class MarkReadRequest(BaseModel):
    up_to_message_id: UUID | None = None


class AdminConversationListItemDto(BaseModel):
    conversation_id: UUID
    patient_id: UUID
    patient_name: str | None
    patient_phone: str
    assigned_admin_id: UUID | None
    assigned_admin_name: str | None
    last_message_at: datetime | None
    last_message_sender_type: str | None
    unread_by_admin_count: int

    model_config = ConfigDict(from_attributes=True)


class AdminConversationsResponse(BaseModel):
    items: list[AdminConversationListItemDto]
    total: int


class AssignRequest(BaseModel):
    admin_id: UUID | None = None


class AssignResponse(BaseModel):
    conversation_id: UUID
    assigned_admin_id: UUID | None
