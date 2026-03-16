"""Owner integration settings: Morning Brief and AI Supervisor Telegram (B5.6)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OwnerIntegrationSettings(Base):
    """Per-clinic settings for owner morning brief and AI supervisor summary (Telegram)."""

    __tablename__ = "owner_integration_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Owner Morning Brief
    owner_morning_brief_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    owner_telegram_chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    morning_brief_send_at_utc: Mapped[str | None] = mapped_column(
        String(8), nullable=True
    )  # "09:00" or "06:00"

    # AI Supervisor Summary
    ai_supervisor_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    ai_supervisor_send_at_utc: Mapped[str | None] = mapped_column(String(8), nullable=True)  # "20:00"
    ai_supervisor_recipient_chat_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )  # ["chat_id1", "chat_id2"]

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)
