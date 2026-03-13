"""Conversation entity model."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_message_sender_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    unread_by_admin_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    unread_by_patient_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("clinic_id", "patient_id", name="ux_conversations_clinic_patient"),
        Index("idx_conversations_clinic_patient", "clinic_id", "patient_id"),
        Index("idx_conversations_clinic_last_message", "clinic_id", "last_message_at"),
        Index("idx_conversations_assigned_admin", "assigned_admin_id", "last_message_at"),
        Index("idx_conversations_clinic_unread_admin", "clinic_id", "unread_by_admin_count"),
    )
