"""Commerce CSV import job record (Phase 4-F5): audit + optional idempotency (ADR-010)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CommerceImportJob(Base):
    """One row per logical import; idempotency_key unique per organization when client supplies it."""

    __tablename__ = "commerce_import_jobs"
    __table_args__ = (
        Index(
            "ux_commerce_import_jobs_org_idempotency",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "ix_commerce_import_jobs_org_clinic_created",
            "organization_id",
            "clinic_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clinics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    stock_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("commerce_stock_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
