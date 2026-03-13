"""Omnichannel integration configuration: metadata + encrypted credentials.

This is a per-channel config that stores provider/type metadata and an
encrypted blob with provider-specific credentials. The encrypted blob
acts as a simple vault/KMS substitute inside this project.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, UniqueConstraint, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class OmnichannelIntegrationConfig(Base):
    """One row per business channel with encrypted credentials."""

    __tablename__ = "omni_integration_configs"
    __table_args__ = (
        UniqueConstraint("business_account_id", "channel_id", name="ux_omni_integration_channel"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_account_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    provider_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    scopes: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )  # PENDING / OK / EXPIRED / REVOKED / ERROR
    credentials_encrypted: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
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

