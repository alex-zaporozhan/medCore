"""Doctor working hours entity model."""

import uuid
from datetime import datetime, time

from sqlalchemy import Time, Integer, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class DoctorWorkingHours(Base):
    """Template working hours per weekday for a doctor."""

    __tablename__ = "doctor_working_hours"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id"), nullable=False
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_working_hours_doctor_weekday", "doctor_id", "weekday"),
    )

