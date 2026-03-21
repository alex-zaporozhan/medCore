"""erp_aggregate_coverage_watermark (A5)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "q3r4s5t6u7v8"
down_revision = "p2q3r4s5t6u7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "erp_aggregate_coverage_watermark",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_kind", sa.String(length=32), nullable=False),
        sa.Column("covered_from", sa.Date(), nullable=False),
        sa.Column("covered_to", sa.Date(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "aggregate_kind", name="uq_erp_agg_watermark_clinic_kind"),
    )
    op.create_index(
        "ix_erp_agg_watermark_clinic",
        "erp_aggregate_coverage_watermark",
        ["clinic_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_erp_agg_watermark_clinic", table_name="erp_aggregate_coverage_watermark")
    op.drop_table("erp_aggregate_coverage_watermark")
