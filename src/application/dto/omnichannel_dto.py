"""DTOs for omnichannel Integration Gateway."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NormalizedMessageDTO(BaseModel):
    """Provider-agnostic representation of an inbound message."""

    provider: str
    external_message_id: str
    from_id: str
    chat_external_id: str
    text: str
    timestamp: datetime


class OutgoingMessageDTO(BaseModel):
    """Provider-agnostic representation of an outbound message."""

    provider: str
    channel_id: UUID | None = None
    chat_external_id: str | None = None
    to_id: str | None = None
    text: str

