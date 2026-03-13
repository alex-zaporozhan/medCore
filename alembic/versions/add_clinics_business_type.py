"""Add clinics.business_type and business_type_custom_name.

Revision ID: u1v2w3x4y5z6
Revises: o5p6q7r8s9t0
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "u1v2w3x4y5z6"
down_revision: Union[str, Sequence[str], None] = "o5p6q7r8s9t0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clinics",
        sa.Column("business_type", sa.String(32), nullable=False, server_default="stomatology"),
    )
    op.add_column(
        "clinics",
        sa.Column("business_type_custom_name", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clinics", "business_type_custom_name")
    op.drop_column("clinics", "business_type")
