"""Add clinics.person_label_* and staff_label_plural.

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w3x4y5z6a7b8"
down_revision: Union[str, Sequence[str], None] = "v2w3x4y5z6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clinics",
        sa.Column("person_label_singular", sa.String(50), nullable=True),
    )
    op.add_column(
        "clinics",
        sa.Column("person_label_plural", sa.String(50), nullable=True),
    )
    op.add_column(
        "clinics",
        sa.Column("staff_label_plural", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clinics", "staff_label_plural")
    op.drop_column("clinics", "person_label_plural")
    op.drop_column("clinics", "person_label_singular")

