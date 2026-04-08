"""Audit steps for CRM import pipeline (§25.0)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CrmImportJobAudit(Base):
    __tablename__ = "crm_import_job_audit"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crm_import_staging_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_crm_import_job_audit_job_created", "job_id", "created_at"),)
