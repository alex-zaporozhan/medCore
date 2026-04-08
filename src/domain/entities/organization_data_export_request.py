"""Owner-initiated data export / offboarding requests (Phase 1e-F3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OrganizationDataExportRequest(Base):
    __tablename__ = "organization_data_export_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    export_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_org_data_export_requests_org_created", "organization_id", "created_at"),)
