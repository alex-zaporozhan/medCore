"""Commerce import jobs: audit + idempotency (4-F5, ADR-010 alignment).

Revision ID: 20260421_commerce_import_jobs
Revises: 20260420_commerce_goods_transfer
Create Date: 2026-04-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260421_commerce_import_jobs"
down_revision: Union[str, Sequence[str], None] = "20260420_commerce_goods_transfer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commerce_import_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=True),
        sa.Column("stock_location_id", sa.Uuid(), nullable=True),
        sa.Column("source_profile", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("payload_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["admins.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["stock_location_id"],
            ["commerce_stock_locations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commerce_import_jobs_org_clinic_created",
        "commerce_import_jobs",
        ["organization_id", "clinic_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ux_commerce_import_jobs_org_idempotency",
        "commerce_import_jobs",
        ["organization_id", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_commerce_import_jobs_org_idempotency", table_name="commerce_import_jobs")
    op.drop_index("ix_commerce_import_jobs_org_clinic_created", table_name="commerce_import_jobs")
    op.drop_table("commerce_import_jobs")
