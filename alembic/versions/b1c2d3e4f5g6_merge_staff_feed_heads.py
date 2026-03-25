"""Merge staff feed heads.

Revision ID: b1c2d3e4f5g6
Revises: a0b1c2d3e4f5, g8h9i0j1k2l3
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "b1c2d3e4f5g6"
down_revision: Union[str, Sequence[str]] = ("a0b1c2d3e4f5", "g8h9i0j1k2l3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge-only revision to satisfy single-head upgrade.
    pass


def downgrade() -> None:
    # Merge-only revision; revert is not supported as it would require
    # rewinding two independent heads.
    pass

