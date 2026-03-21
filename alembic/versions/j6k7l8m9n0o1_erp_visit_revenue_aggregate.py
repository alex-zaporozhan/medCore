"""ERP visit revenue pre-aggregate + Kanban cursor index (Engine L2).

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-03-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "j6k7l8m9n0o1"
down_revision: Union[str, Sequence[str], None] = "i5j6k7l8m9n0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "erp_visit_revenue_aggregate",
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("booking_bucket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_revenue", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("clinic_id", "visit_date", "booking_bucket_id"),
    )
    op.create_index(
        "ix_erp_visit_rev_agg_clinic_date",
        "erp_visit_revenue_aggregate",
        ["clinic_id", "visit_date"],
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_lead_cards_kanban_cursor
        ON lead_cards (clinic_id, stage_id, created_at DESC, id DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_lead_cards_kanban_cursor;")
    op.drop_index("ix_erp_visit_rev_agg_clinic_date", table_name="erp_visit_revenue_aggregate")
    op.drop_table("erp_visit_revenue_aggregate")
