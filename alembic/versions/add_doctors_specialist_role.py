"""Add doctors.specialist_role and specialist_role_custom_name.

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "v2w3x4y5z6a7"
down_revision: Union[str, Sequence[str], None] = "u1v2w3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column("specialist_role", sa.String(32), nullable=False, server_default="doctor"),
    )
    op.add_column(
        "doctors",
        sa.Column("specialist_role_custom_name", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("doctors", "specialist_role_custom_name")
    op.drop_column("doctors", "specialist_role")
