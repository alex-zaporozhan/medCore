"""Omnichannel chat closure metadata (outcome + tags)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OmniChatClosureTag(Base):
    __tablename__ = "omni_chat_closure_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("clinic_id", "title", name="ux_omni_chat_closure_tags_clinic_title"),
    )


class OmniChatClosure(Base):
    __tablename__ = "omni_chat_closures"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("omni_chats.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    closed_by_admin_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("admins.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    closed_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class OmniChatClosureTagLink(Base):
    __tablename__ = "omni_chat_closure_tag_links"

    closure_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("omni_chat_closures.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("omni_chat_closure_tags.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

