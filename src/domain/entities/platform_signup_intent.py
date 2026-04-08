"""Platform SaaS signup intent (contour B) — pending payment until provisioning."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class PlatformSignupIntent(Base):
    """Owner self-service signup before organization is fully provisioned."""

    __tablename__ = "platform_signup_intents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="pending_payment",
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tariff_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    provisioned_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    #: SHA-256 hex of one-time owner invite token (cleared after accept).
    owner_invite_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Set when contour B payment is refunded and paid entitlements were revoked (ADR-012).
    billing_revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    provision_retry_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    provision_next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provision_last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    provision_dead_letter: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
