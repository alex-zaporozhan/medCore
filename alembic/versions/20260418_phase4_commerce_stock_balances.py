"""Phase 4: commerce_stock_balances (quantity per location + SKU).

Revision ID: 20260418_phase4_commerce_stock_balances
Revises: 20260417_phase4_commerce_core_tables
Create Date: 2026-04-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260418_phase4_commerce_stock_balances"
down_revision: Union[str, Sequence[str], None] = "20260417_phase4_commerce_core_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commerce_stock_balances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("stock_location_id", sa.Uuid(), nullable=False),
        sa.Column("nomenclature_item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=4), server_default="0", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["nomenclature_item_id"], ["commerce_nomenclature_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_location_id"], ["commerce_stock_locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stock_location_id",
            "nomenclature_item_id",
            name="ux_commerce_balance_loc_item",
        ),
    )
    op.create_index(
        "ix_commerce_stock_balances_organization_id",
        "commerce_stock_balances",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_stock_balances_clinic_id",
        "commerce_stock_balances",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_stock_balances_clinic_location",
        "commerce_stock_balances",
        ["clinic_id", "stock_location_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_commerce_stock_balances_clinic_location", table_name="commerce_stock_balances")
    op.drop_index("ix_commerce_stock_balances_clinic_id", table_name="commerce_stock_balances")
    op.drop_index("ix_commerce_stock_balances_organization_id", table_name="commerce_stock_balances")
    op.drop_table("commerce_stock_balances")
