"""QueuePolicy entity (one per clinic)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class QueuePolicy(Base):
    """How waitlist is processed when a slot frees up."""

    __tablename__ = "queue_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, unique=True, index=True
    )
    mode: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # sequential, broadcast
    broadcast_size: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="5"
    )
    response_timeout_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="60"
    )
    max_notifications_per_entry: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
