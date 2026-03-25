"""Участники события календаря персонала (совещания)."""

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffCalendarEventParticipant(Base):
    __tablename__ = "staff_calendar_event_participants"

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_calendar_events.id", ondelete="CASCADE"), primary_key=True
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True
    )
