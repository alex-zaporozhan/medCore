"""Admins: employment_status (active / terminated), коробка: блокировка входа.

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admins",
        sa.Column(
            "employment_status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
    )
    op.create_index("ix_admins_clinic_employment", "admins", ["clinic_id", "employment_status"])


def downgrade() -> None:
    op.drop_index("ix_admins_clinic_employment", table_name="admins")
    op.drop_column("admins", "employment_status")
