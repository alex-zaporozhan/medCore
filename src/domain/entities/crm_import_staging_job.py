"""CRM import staging job (ADR-010, Phase 3+): per-org dry-run / commit tracking."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CrmImportStagingJob(Base):
    """
    Lightweight staging record before full ingest/validate/clean pipeline (§25.0).
    idempotency_key prevents duplicate dry-runs for the same logical upload.
    """

    __tablename__ = "crm_import_staging_jobs"

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
    source_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
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

    __table_args__ = (
        Index(
            "ux_crm_import_staging_jobs_org_idempotency",
            "organization_id",
            "idempotency_key",
            unique=True,
        ),
    )
