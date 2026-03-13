"""ChatMessage entity model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"), nullable=False, index=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    admin_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    sender_type: Mapped[str] = mapped_column(String(16), nullable=False)
    message_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="text")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sticker_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    follow_up_at: Mapped[datetime | None] = mapped_column(nullable=True)
    follow_up_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    follow_up_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    read_by_admin_at: Mapped[datetime | None] = mapped_column(nullable=True)
    read_by_patient_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_chat_messages_conversation_created_at", "conversation_id", "created_at"),
        Index("idx_chat_messages_clinic_created_at", "clinic_id", "created_at"),
    )
