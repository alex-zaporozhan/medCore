"""Public doctor profile: client-facing doctor page content (per clinic)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class PublicDoctorProfile(Base):
    __tablename__ = "public_doctor_profiles"
    __table_args__ = (
        UniqueConstraint("clinic_id", "doctor_id", name="ux_public_doctor_profile_clinic_doctor"),
        UniqueConstraint("clinic_id", "doctor_slug", name="ux_public_doctor_profile_clinic_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id"), nullable=False, index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("doctors.id"), nullable=False, index=True
    )
    doctor_slug: Mapped[str] = mapped_column(String(120), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", index=True)

    public_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    short_bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    about_md: Mapped[str | None] = mapped_column(Text(), nullable=True)

    languages: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    education: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    certifications: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

