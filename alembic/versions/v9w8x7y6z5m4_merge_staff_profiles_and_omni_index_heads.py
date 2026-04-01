"""Merge heads: staff_profiles and omni_messages index.

Revision ID: v9w8x7y6z5m4
Revises: r1s2t3u4v5w6, u9v0w1x2y3
Create Date: 2026-04-01
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "v9w8x7y6z5m4"
down_revision: Union[str, Sequence[str], None] = ("r1s2t3u4v5w6", "u9v0w1x2y3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # merge-only revision
    op.execute("SELECT 1")


def downgrade() -> None:
    # merge-only revision
    op.execute("SELECT 1")

