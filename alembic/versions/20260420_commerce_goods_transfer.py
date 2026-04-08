"""Commerce: goods_transfer + to_stock_location_id on documents.

Revision ID: 20260420_commerce_goods_transfer
Revises: 20260419_phase4_commerce_movement_documents
Create Date: 2026-04-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260420_commerce_goods_transfer"
down_revision: Union[str, Sequence[str], None] = "20260419_phase4_commerce_movement_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_commerce_documents_doc_kind", "commerce_documents", type_="check")
    op.add_column(
        "commerce_documents",
        sa.Column("to_stock_location_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_commerce_documents_to_stock_location",
        "commerce_documents",
        "commerce_stock_locations",
        ["to_stock_location_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_commerce_documents_kind_and_transfer",
        "commerce_documents",
        sa.text(
            "(doc_kind IN ('goods_in', 'goods_out', 'goods_transfer')) AND ("
            "(doc_kind = 'goods_transfer' AND to_stock_location_id IS NOT NULL "
            "AND to_stock_location_id <> stock_location_id) OR "
            "(doc_kind <> 'goods_transfer' AND to_stock_location_id IS NULL))"
        ),
    )


def downgrade() -> None:
    op.drop_constraint("ck_commerce_documents_kind_and_transfer", "commerce_documents", type_="check")
    op.drop_constraint("fk_commerce_documents_to_stock_location", "commerce_documents", type_="foreignkey")
    op.drop_column("commerce_documents", "to_stock_location_id")
    op.create_check_constraint(
        "ck_commerce_documents_doc_kind",
        "commerce_documents",
        sa.text("doc_kind IN ('goods_in', 'goods_out')"),
    )
