"""Notification channel config DTOs (per-clinic Telegram/SMS/Email)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationChannelConfigRead(BaseModel):
    """Channel config read DTO."""

    id: UUID
    clinic_id: UUID
    channel: str  # telegram | sms | email
    config_json: dict | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationChannelConfigCreate(BaseModel):
    """Channel config create/upsert DTO."""

    channel: str = Field(..., pattern="^(telegram|sms|email)$")
    enabled: bool = True
    config_json: dict | None = None


class NotificationChannelConfigUpdate(BaseModel):
    """Channel config update DTO."""

    enabled: bool | None = None
    config_json: dict | None = None
