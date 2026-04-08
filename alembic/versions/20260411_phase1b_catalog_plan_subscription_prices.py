"""Phase 1b: monthly/annual subscription prices on platform catalog plans.

Revision ID: 20260411_phase1b_catalog_plan_subscription_prices
Revises: 20260410_phase1b_billing_revocation
Create Date: 2026-04-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260411_phase1b_catalog_plan_subscription_prices"
down_revision: Union[str, Sequence[str], None] = "20260410_phase1b_billing_revocation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_catalog_plans",
        sa.Column("price_monthly_rub", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "platform_catalog_plans",
        sa.Column("price_annual_rub", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE platform_catalog_plans
            SET price_monthly_rub = 4990.00,
                price_annual_rub = 49900.00
            WHERE slug = 'starter_rf'
            """
        )
    )


def downgrade() -> None:
    op.drop_column("platform_catalog_plans", "price_annual_rub")
    op.drop_column("platform_catalog_plans", "price_monthly_rub")
