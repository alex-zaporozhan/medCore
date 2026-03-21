"""Wave 5 (A3): partial indexes for income ERP paths + salary period overlap.

Revision ID: w5perf1idx_fin
Revises: t6u7v8w9x0y1
Create Date: 2026-03-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "w5perf1idx_fin"
down_revision = "t6u7v8w9x0y1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_fin_tx_clinic_income_happened",
        "financial_transactions",
        ["clinic_id", "happened_at"],
        unique=False,
        postgresql_where=sa.text("type = 'income'"),
    )
    op.create_index(
        "idx_fin_tx_clinic_income_lead",
        "financial_transactions",
        ["clinic_id", "lead_id"],
        unique=False,
        postgresql_where=sa.text("type = 'income' AND lead_id IS NOT NULL"),
    )
    op.create_index(
        "idx_salary_tx_clinic_period_overlap",
        "salary_transactions",
        ["clinic_id", "period_start", "period_end"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_salary_tx_clinic_period_overlap", table_name="salary_transactions")
    op.drop_index("idx_fin_tx_clinic_income_lead", table_name="financial_transactions")
    op.drop_index("idx_fin_tx_clinic_income_happened", table_name="financial_transactions")
