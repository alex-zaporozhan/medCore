"""Phase 4: commerce_* core tables + nomenclature API stub (ADR-013).

Revision ID: 20260417_phase4_commerce_core_tables
Revises: 20260416_phase4_commerce_catalog_placeholder
Create Date: 2026-04-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260417_phase4_commerce_core_tables"
down_revision: Union[str, Sequence[str], None] = "20260416_phase4_commerce_catalog_placeholder"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commerce_stock_locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commerce_stock_locations_organization_id",
        "commerce_stock_locations",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_stock_locations_clinic_id",
        "commerce_stock_locations",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_stock_locations_org_clinic",
        "commerce_stock_locations",
        ["organization_id", "clinic_id"],
        unique=False,
    )

    op.create_table(
        "commerce_nomenclature_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), server_default="pcs", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "sku", name="ux_commerce_nom_clinic_sku"),
    )
    op.create_index(
        "ix_commerce_nomenclature_items_organization_id",
        "commerce_nomenclature_items",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_nomenclature_items_clinic_id",
        "commerce_nomenclature_items",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "ix_commerce_nom_org_clinic",
        "commerce_nomenclature_items",
        ["organization_id", "clinic_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_commerce_nom_org_clinic", table_name="commerce_nomenclature_items")
    op.drop_index("ix_commerce_nomenclature_items_clinic_id", table_name="commerce_nomenclature_items")
    op.drop_index("ix_commerce_nomenclature_items_organization_id", table_name="commerce_nomenclature_items")
    op.drop_table("commerce_nomenclature_items")

    op.drop_index("ix_commerce_stock_locations_org_clinic", table_name="commerce_stock_locations")
    op.drop_index("ix_commerce_stock_locations_clinic_id", table_name="commerce_stock_locations")
    op.drop_index("ix_commerce_stock_locations_organization_id", table_name="commerce_stock_locations")
    op.drop_table("commerce_stock_locations")
