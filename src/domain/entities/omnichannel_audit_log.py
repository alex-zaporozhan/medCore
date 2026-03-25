"""Omnichannel AuditLog entity model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, String, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class AuditLog(Base):
    """Audit log for omnichannel assistant actions."""

    __tablename__ = "omni_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_account_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("clinics.id"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True), nullable=True
    )
    actor_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # OWNER / ADMIN / SYSTEM
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True), nullable=True
    )
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index(
            "idx_omni_audit_logs_business_created_at",
            "business_account_id",
            "created_at",
        ),
        Index(
            "idx_omni_audit_logs_target",
            "target_type",
            "target_id",
        ),
    )

