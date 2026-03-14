"""Add preferred_date and preferred_time to waitlist_entries.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-02-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "waitlist_entries",
        sa.Column("preferred_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column("preferred_time", sa.Time(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("waitlist_entries", "preferred_time")
    op.drop_column("waitlist_entries", "preferred_date")
