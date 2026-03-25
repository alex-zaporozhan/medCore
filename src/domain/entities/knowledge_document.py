"""Knowledge base article with role visibility."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
    folder_key: Mapped[str] = mapped_column(String(64), nullable=False, server_default="general")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    visible_roles: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_by_admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admins.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_knowledge_documents_clinic_folder", "clinic_id", "folder_key"),)
