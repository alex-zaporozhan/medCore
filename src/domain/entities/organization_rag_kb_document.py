"""Per-organization RAG knowledge base text chunks (§24.3) — store + search scoped by organization_id."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import Computed

from src.infrastructure.database.base import Base


class OrganizationRagKbDocument(Base):
    __tablename__ = "organization_rag_kb_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    #: Полнотекст (PostgreSQL GENERATED STORED); GIN в миграции `20260425_rag_kb_audit_fts`.
    search_tsv: Mapped[object | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(body, ''))",
            persisted=True,
        ),
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

    __table_args__ = (Index("ix_org_rag_kb_documents_organization_id", "organization_id"),)
