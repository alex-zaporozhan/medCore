"""Payroll vitrine: nullable period bounds via flags (no sentinel collision in API).

Revision ID: n0o1p2q3r4s5
Revises: m8n9o0p1q2r3
Create Date: 2026-03-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n0o1p2q3r4s5"
down_revision: Union[str, Sequence[str], None] = "m8n9o0p1q2r3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "erp_payroll_aggregate",
        sa.Column(
            "period_start_is_null",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "erp_payroll_aggregate",
        sa.Column(
            "period_end_is_null",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        """
        UPDATE erp_payroll_aggregate SET
          period_start_is_null = (period_start_key = DATE '0001-01-01'),
          period_end_is_null = (period_end_key = DATE '9999-12-31')
        """
    )
    op.drop_constraint("erp_payroll_aggregate_pkey", "erp_payroll_aggregate", type_="primary")
    op.create_primary_key(
        "erp_payroll_aggregate_pkey",
        "erp_payroll_aggregate",
        [
            "clinic_id",
            "doctor_id",
            "booking_bucket_id",
            "period_start_is_null",
            "period_start_key",
            "period_end_is_null",
            "period_end_key",
        ],
    )
    op.alter_column(
        "erp_payroll_aggregate",
        "period_start_is_null",
        server_default=None,
    )
    op.alter_column(
        "erp_payroll_aggregate",
        "period_end_is_null",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_constraint("erp_payroll_aggregate_pkey", "erp_payroll_aggregate", type_="primary")
    op.create_primary_key(
        "erp_payroll_aggregate_pkey",
        "erp_payroll_aggregate",
        [
            "clinic_id",
            "doctor_id",
            "booking_bucket_id",
            "period_start_key",
            "period_end_key",
        ],
    )
    op.drop_column("erp_payroll_aggregate", "period_end_is_null")
    op.drop_column("erp_payroll_aggregate", "period_start_is_null")
