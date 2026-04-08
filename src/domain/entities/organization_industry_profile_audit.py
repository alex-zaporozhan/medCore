"""Audit trail for organization vertical profile changes (Phase 3+)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OrganizationIndustryProfileAudit(Base):
    __tablename__ = "organization_industry_profile_audit"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    old_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    new_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_org_industry_audit_org_created", "organization_id", "created_at"),)
