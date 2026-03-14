"""Task entity for operational task management."""

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    Index,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Task(Base):
    """Operational task assigned to a user or role within a clinic."""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="open"
    )  # open|in_progress|done|cancelled
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )  # low|medium|high|urgent
    creator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id"), nullable=True
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id"), nullable=True
    )
    role_assignee: Mapped[str | None] = mapped_column(String(64), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    # Domain links
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patients.id"), nullable=True, index=True
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lead_cards.id"), nullable=True, index=True
    )
    inventory_product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manual",
    )  # manual|ai_suggested|ai_auto|system
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_tasks_clinic_status", "clinic_id", "status"),
        Index("idx_tasks_clinic_assignee", "clinic_id", "assignee_id"),
        Index("idx_tasks_clinic_role_assignee", "clinic_id", "role_assignee"),
        Index("idx_tasks_clinic_due_at", "clinic_id", "due_at"),
    )

