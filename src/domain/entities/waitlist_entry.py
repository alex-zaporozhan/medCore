"""WaitlistEntry entity."""

import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, ForeignKey, Integer, String, Text, Time, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class WaitlistEntry(Base):
    """Patient in waitlist for a slot."""

    __tablename__ = "waitlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id"), nullable=False, index=True
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id"), nullable=True, index=True
    )
    speciality: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g. "therapy"
    time_preferences_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    preferred_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    preferred_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # waiting, notified, expired, cancelled
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
