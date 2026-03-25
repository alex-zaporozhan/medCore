"""Clinic AI settings entity."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ClinicAiSettings(Base):
    __tablename__ = "clinic_ai_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False, unique=True
    )
    ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    ai_tasks_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    ai_mode: Mapped[str] = mapped_column(String(32), nullable=False, server_default="draft_only")
    ai_business_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_allowed_intents: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default=text("'{}'::text[]")
    )
    ai_autoreply_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    ai_autoreply_hours: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_provider_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="external")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

