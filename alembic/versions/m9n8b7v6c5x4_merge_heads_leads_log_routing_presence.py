"""Merge heads: leads-log routing + omni presence.

Revision ID: m9n8b7v6c5x4
Revises: e2f3a4b5c6d7, g4h5i6j7k8l9
Create Date: 2026-04-01
"""

from __future__ import annotations

from typing import Sequence, Union


revision: str = "m9n8b7v6c5x4"
down_revision: Union[str, Sequence[str], None] = ("e2f3a4b5c6d7", "g4h5i6j7k8l9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Merge revision: no schema changes.
    pass


def downgrade() -> None:
    # Merge revision: no schema changes.
    pass

