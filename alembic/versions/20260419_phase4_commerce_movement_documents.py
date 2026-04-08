"""Phase 4: commerce movement documents (goods_in / goods_out).

Revision ID: 20260419_phase4_commerce_movement_documents
Revises: 20260418_phase4_commerce_stock_balances
Create Date: 2026-04-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260419_phase4_commerce_movement_documents"
down_revision: Union[str, Sequence[str], None] = "20260418_phase4_commerce_stock_balances"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commerce_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("stock_location_id", sa.Uuid(), nullable=False),
        sa.Column("doc_kind", sa.String(length=32), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_location_id"], ["commerce_stock_locations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("doc_kind IN ('goods_in', 'goods_out')", name="ck_commerce_documents_doc_kind"),
    )
    op.create_index(
        "ix_commerce_documents_organization_id",
        "commerce_documents",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_documents_clinic_id",
        "commerce_documents",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_documents_clinic_created",
        "commerce_documents",
        ["clinic_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "commerce_document_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("nomenclature_item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["commerce_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["nomenclature_item_id"],
            ["commerce_nomenclature_items.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "nomenclature_item_id", name="ux_commerce_doc_line_doc_item"),
        sa.CheckConstraint("quantity > 0", name="ck_commerce_document_lines_qty_positive"),
    )
    op.create_index(
        "ix_commerce_document_lines_document_id",
        "commerce_document_lines",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_document_lines_clinic_id",
        "commerce_document_lines",
        ["clinic_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_commerce_document_lines_clinic_id", table_name="commerce_document_lines")
    op.drop_index("ix_commerce_document_lines_document_id", table_name="commerce_document_lines")
    op.drop_table("commerce_document_lines")
    op.drop_index("ix_commerce_documents_clinic_created", table_name="commerce_documents")
    op.drop_index("ix_commerce_documents_clinic_id", table_name="commerce_documents")
    op.drop_index("ix_commerce_documents_organization_id", table_name="commerce_documents")
    op.drop_table("commerce_documents")
