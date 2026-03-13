"""Omnichannel Message entity model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Message(Base):
    """Message model for omnichannel assistant."""

    __tablename__ = "omni_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("omni_chats.id"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("omni_contacts.id"),
        nullable=True,
        index=True,
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("omni_channels.id"),
        nullable=True,
        index=True,
    )
    direction: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # INBOUND / OUTBOUND
    actor_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # CLIENT / AI / HUMAN_ADMIN / SYSTEM / OWNER
    content_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="TEXT"
    )  # TEXT / MEDIA / SYSTEM_EVENT / TEMPLATE
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_metadata: Mapped[dict | None] = mapped_column(
        postgresql.JSONB, nullable=True
    )
    ui_hidden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    hidden_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_omni_messages_chat_created_at",
            "chat_id",
            "created_at",
        ),
    )

