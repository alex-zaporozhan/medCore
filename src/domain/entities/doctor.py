"""Doctor entity model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Integer, Boolean, Numeric, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Doctor(Base):
    """Doctor model."""

    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str] = mapped_column(String(255), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rating: Mapped[Decimal] = mapped_column(
        Numeric(2, 1), nullable=False, server_default="0.0"
    )
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", index=True)
    specialist_role: Mapped[str] = mapped_column(String(32), nullable=False, server_default="doctor")
    specialist_role_custom_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_doctors_clinic_id", "clinic_id"),
        Index("idx_doctors_is_active", "is_active"),
    )

    @property
    def display_role(self) -> str:
        """Human-readable role for UI (Врач, Мастер, Медсестра, etc.)."""
        if self.specialist_role == "doctor":
            return "Врач"
        if self.specialist_role == "master":
            return "Мастер"
        if self.specialist_role == "nurse":
            return "Медсестра"
        if self.specialist_role == "therapist":
            return "Терапевт"
        if self.specialist_role == "other" and self.specialist_role_custom_name:
            return self.specialist_role_custom_name.strip()
        return "Специалист"
