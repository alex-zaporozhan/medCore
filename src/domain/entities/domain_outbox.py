"""Transactional outbox for reliable domain event delivery (ADR-009, U-007)."""

import uuid
from datetime import datetime

from sqlalchemy import Index, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class DomainOutbox(Base):
    """Outbox row: inserted in the same DB transaction as domain writes; dispatched after commit."""

    __tablename__ = "domain_outbox"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dedup_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_domain_outbox_unpublished_created", "published_at", "created_at"),)
