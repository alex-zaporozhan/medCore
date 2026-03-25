"""Clinic staff chat scope: owner policy placeholder for cross-location visibility.

Revision ID: b2c3d4e5f6g7
Revises: z1a2b3c4d5e6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, Sequence[str], None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "clinics",
        sa.Column(
            "staff_chat_scope",
            sa.String(length=32),
            nullable=False,
            server_default="clinic_isolated",
        ),
    )


def downgrade() -> None:
    op.drop_column("clinics", "staff_chat_scope")
