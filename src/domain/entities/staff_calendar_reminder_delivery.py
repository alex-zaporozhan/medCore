"""Scheduled calendar reminder (processed by Celery)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffCalendarReminderDelivery(Base):
    __tablename__ = "staff_calendar_reminder_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_calendar_events.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    fire_at: Mapped[datetime] = mapped_column(nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
