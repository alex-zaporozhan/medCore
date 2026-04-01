"""Omnichannel Chat entity model."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Chat(Base):
    """Chat model for omnichannel assistant."""

    __tablename__ = "omni_chats"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_account_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("omni_contacts.id"),
        nullable=False,
        index=True,
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("omni_channels.id"),
        nullable=True,
        index=True,
    )
    assignee_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="OPEN",
    )  # OPEN / WAITING_FOR_OPERATOR / IN_PROGRESS / CLOSED
    ai_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="DISABLED",
    )  # AUTO_REPLY / SUGGEST_ONLY / DISABLED
    last_message_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_actor_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # CLIENT / AI / HUMAN_ADMIN / SYSTEM / OWNER
    claimed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_omni_chats_business_contact_open",
            "business_account_id",
            "contact_id",
            "status",
        ),
        Index(
            "idx_omni_chats_business_last_message",
            "business_account_id",
            "last_message_at",
        ),
    )

