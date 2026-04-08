"""Per-organization embed / webhook inbox routing (SaaS §24, Phase 1e)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OrganizationEmbedSettings(Base):
    """Inbound webhook URL segment + optional bearer verification."""

    __tablename__ = "organization_embed_settings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    inbound_route_token: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True)
    webhook_bearer_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_bearer_prefix: Mapped[str | None] = mapped_column(String(24), nullable=True)
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
