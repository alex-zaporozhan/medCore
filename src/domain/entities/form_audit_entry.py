"""Audit trail for form instance lifecycle events (minimal PPR-2)."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, String, TIMESTAMP, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class FormAuditEntry(Base):
    """One row per issued/filled/signed/revoked/cancelled event."""

    __tablename__ = "form_audit_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    digital_form_submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("digital_form_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # issued | filled | signed | revoked | cancelled | expired

    actor: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # patient | admin | doctor | system | legal | unknown

    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_form_audit_submission_created",
            "digital_form_submission_id",
            "created_at",
        ),
    )
