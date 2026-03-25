"""Invitation row for staff calendar event ack ("я увидел").

Used for month-grid "new for me" markers:
- ack is considered unseen when `acknowledged_at IS NULL`
- one invitation is unique per (event_id, invitee_admin_id)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffCalendarEventInvitation(Base):
    __tablename__ = "staff_calendar_event_invitations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False)

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_calendar_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    invitee_admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admins.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("event_id", "invitee_admin_id", name="uq_staff_calendar_event_invitations_event_invitee"),
        Index(
            "ix_staff_calendar_event_invitations_clinic_invitee_ack",
            "clinic_id",
            "invitee_admin_id",
            "acknowledged_at",
        ),
        Index("ix_staff_calendar_event_invitations_event_id", "event_id"),
    )

