"""Add paid_by_subscription flag to bookings.

Revision ID: loyalty_0003_booking_paid_by_subscription
Revises: loyalty_0002_policy_table
Create Date: 2026-03-13
"""

from alembic import op
import sqlalchemy as sa


revision = "loyalty_0003_booking_paid_by_subscription"
down_revision = "loyalty_0002_policy_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column(
            "paid_by_subscription",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("bookings", "paid_by_subscription")

