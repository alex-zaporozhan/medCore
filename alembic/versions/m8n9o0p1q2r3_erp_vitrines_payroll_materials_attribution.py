"""ERP vitrines: payroll, daily inventory, attribution revenue (Engine L2 / VITRINES_026).

Revision ID: m8n9o0p1q2r3
Revises: k7l8m9n0o1p2
Create Date: 2026-03-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m8n9o0p1q2r3"
down_revision: Union[str, Sequence[str], None] = "k7l8m9n0o1p2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "erp_payroll_aggregate",
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_bucket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start_key", sa.Date(), nullable=False),
        sa.Column("period_end_key", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "clinic_id",
            "doctor_id",
            "booking_bucket_id",
            "period_start_key",
            "period_end_key",
        ),
    )
    op.create_index(
        "ix_erp_payroll_agg_clinic_period_overlap",
        "erp_payroll_aggregate",
        ["clinic_id", "period_start_key", "period_end_key"],
    )

    op.create_table(
        "erp_inventory_movement_aggregate",
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_date", sa.Date(), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_bucket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_day", sa.Numeric(12, 3), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "clinic_id",
            "movement_date",
            "product_id",
            "booking_bucket_id",
        ),
    )
    op.create_index(
        "ix_erp_inv_mov_agg_clinic_date",
        "erp_inventory_movement_aggregate",
        ["clinic_id", "movement_date"],
    )

    op.create_table(
        "erp_attribution_revenue_aggregate",
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("traffic_source_bucket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_bucket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_revenue", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "clinic_id",
            "visit_date",
            "traffic_source_bucket_id",
            "campaign_bucket_id",
        ),
    )
    op.create_index(
        "ix_erp_attr_rev_agg_clinic_visit_date",
        "erp_attribution_revenue_aggregate",
        ["clinic_id", "visit_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_erp_attr_rev_agg_clinic_visit_date",
        table_name="erp_attribution_revenue_aggregate",
    )
    op.drop_table("erp_attribution_revenue_aggregate")
    op.drop_index("ix_erp_inv_mov_agg_clinic_date", table_name="erp_inventory_movement_aggregate")
    op.drop_table("erp_inventory_movement_aggregate")
    op.drop_index("ix_erp_payroll_agg_clinic_period_overlap", table_name="erp_payroll_aggregate")
    op.drop_table("erp_payroll_aggregate")
