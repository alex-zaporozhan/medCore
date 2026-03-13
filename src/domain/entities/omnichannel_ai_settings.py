"""Omnichannel AISettings entity model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Index, String, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class AISettings(Base):
    """AI settings for omnichannel assistant on different scopes."""

    __tablename__ = "omni_ai_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scope: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # BUSINESS / CHANNEL / CHAT
    scope_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), nullable=False
    )
    ai_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="DISABLED"
    )  # AUTO_REPLY / SUGGEST_ONLY / DISABLED
    working_hours_policy: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    confidence_thresholds: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    prompt_profile_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    kb_profile_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ux_omni_ai_settings_scope",
            "scope",
            "scope_id",
            unique=True,
        ),
    )

