"""Add loyalty_policies table for clinic loyalty configuration.

Revision ID: loyalty_0002_policy_table
Revises: loyalty_0001_subscriptions_wallet
Create Date: 2026-03-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "loyalty_0002_policy_table"
down_revision: Union[str, Sequence[str], None] = "loyalty_0001_subscriptions_wallet"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create loyalty_policies table."""
    op.create_table(
        "loyalty_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cashback_percent", sa.Numeric(5, 4), nullable=False, server_default="0.00"),
        sa.Column("min_check_for_cashback", sa.Numeric(12, 2), nullable=True),
        sa.Column("allow_pay_with_points", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("max_points_share", sa.Numeric(5, 2), nullable=True),
        sa.Column("points_expire_days", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", name="ux_loyalty_policies_clinic"),
    )
    op.create_index(
        "ix_loyalty_policies_clinic_id",
        "loyalty_policies",
        ["clinic_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop loyalty_policies table."""
    op.drop_index("ix_loyalty_policies_clinic_id", table_name="loyalty_policies")
    op.drop_table("loyalty_policies")

