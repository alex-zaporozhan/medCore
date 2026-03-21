"""erp_aggregate_manual_refresh_audit (A13 manual POST refresh audit)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "p2q3r4s5t6u7"
down_revision = "o1p2q3r4s5t6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "erp_aggregate_manual_refresh_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("scope_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "rows_written",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admins.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_erp_agg_manual_refresh_audit_clinic",
        "erp_aggregate_manual_refresh_audit",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        "ix_erp_agg_manual_refresh_audit_admin",
        "erp_aggregate_manual_refresh_audit",
        ["admin_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_erp_agg_manual_refresh_audit_admin", table_name="erp_aggregate_manual_refresh_audit")
    op.drop_index("ix_erp_agg_manual_refresh_audit_clinic", table_name="erp_aggregate_manual_refresh_audit")
    op.drop_table("erp_aggregate_manual_refresh_audit")
