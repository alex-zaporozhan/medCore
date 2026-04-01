"""Merge RBAC heads.

Revision ID: m1n2o3p4q5r6
Revises: c4d5e6f7g8h9, z9y8x7w6v5u4
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "m1n2o3p4q5r6"
down_revision: Union[str, Sequence[str]] = ("c4d5e6f7g8h9", "z9y8x7w6v5u4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge-only revision to restore single Alembic head.
    pass


def downgrade() -> None:
    # Merge-only revision.
    pass

