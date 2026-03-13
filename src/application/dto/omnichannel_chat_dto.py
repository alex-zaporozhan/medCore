"""DTOs for admin omnichannel chat API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from src.core.datetime_utils import to_iso8601_utc


class OmniMessageDto(BaseModel):
    id: UUID
    direction: str
    actor_type: str
    content: str
    created_at: datetime | None
    ui_hidden: bool = False
    hidden_reason: str | None = None
    channel_type: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str:
        return to_iso8601_utc(value) or ""


class OmniMessagesResponse(BaseModel):
    items: list[OmniMessageDto]


class SendOmniMessageRequest(BaseModel):
    content: str = Field(..., max_length=2000)

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

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_message_at", "created_at")
    def serialize_datetime(self, value: datetime | None) -> str:
        return to_iso8601_utc(value) or ""


class HideOmniMessageRequest(BaseModel):
    reason: str = Field(..., max_length=500)

    @model_validator(mode="after")
    def validate_reason(self):
        if not (self.reason and self.reason.strip()):
            raise ValueError("reason must not be empty")
        return self

