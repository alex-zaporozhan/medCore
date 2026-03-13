"""WaitlistNotification entity."""

import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, ForeignKey, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class WaitlistNotification(Base):
    """Notification sent to waitlist entry for a slot offer."""

    __tablename__ = "waitlist_notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    waitlist_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("waitlist_entries.id"), nullable=False, index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id"), nullable=False
    )
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_time: Mapped[time] = mapped_column(Time, nullable=False)
    channel: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # sms, telegram, email
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # sent, failed, expired
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
