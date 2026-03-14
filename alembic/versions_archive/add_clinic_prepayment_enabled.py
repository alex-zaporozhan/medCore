"""Add clinics.prepayment_enabled and payment_gateway.

Revision ID: p1q2r3s4t5u6
Revises: f9a0b1c2d3e4
Create Date: 2026-03-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "p1q2r3s4t5u6"
down_revision: Union[str, Sequence[str], None] = "f9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clinics",
        sa.Column("prepayment_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "clinics",
        sa.Column("payment_gateway", sa.String(32), nullable=False, server_default="yookassa"),
    )
    op.add_column(
        "clinics",
        sa.Column("payment_gateway_custom_name", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clinics", "payment_gateway_custom_name")
    op.drop_column("clinics", "payment_gateway")
    op.drop_column("clinics", "prepayment_enabled")
