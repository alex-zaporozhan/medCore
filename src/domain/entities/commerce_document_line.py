"""Line of a commerce movement document (Phase 4, ADR-013)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class CommerceDocumentLine(Base):
    """One nomenclature line on a movement document; quantity always positive."""

    __tablename__ = "commerce_document_lines"
    __table_args__ = (
        UniqueConstraint("document_id", "nomenclature_item_id", name="ux_commerce_doc_line_doc_item"),
        CheckConstraint("quantity > 0", name="ck_commerce_document_lines_qty_positive"),
        Index("ix_commerce_document_lines_document_id", "document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commerce_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    nomenclature_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commerce_nomenclature_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
