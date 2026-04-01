"""Staff profile (bio + avatar ref) for clinic admins."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class StaffProfile(Base):
    __tablename__ = "staff_profiles"

    admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admins.id", ondelete="CASCADE"),
        primary_key=True,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bio: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    avatar_s3_key: Mapped[str | None] = mapped_column(String(900), nullable=True, unique=True)
    avatar_updated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("clinic_id", "admin_id", name="ux_staff_profiles_clinic_admin"),
        Index("ix_staff_profiles_clinic_id", "clinic_id"),
    )

