"""Waitlist BKG-4: booking link, service preference, source, notes, audit.

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2026-03-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "i5j6k7l8m9n0"
down_revision: Union[str, Sequence[str], None] = "h4i5j6k7l8m9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "waitlist_entries",
        sa.Column("booking_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column("preferred_service_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column("source", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_waitlist_entries_booking_id",
        "waitlist_entries",
        "bookings",
        ["booking_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_waitlist_entries_preferred_service_id",
        "waitlist_entries",
        "services",
        ["preferred_service_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_waitlist_entries_created_by_id",
        "waitlist_entries",
        "admins",
        ["created_by_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_waitlist_entries_updated_by_id",
        "waitlist_entries",
        "admins",
        ["updated_by_id"],
        ["id"],
    )
    op.create_index(
        "ix_waitlist_entries_booking_id",
        "waitlist_entries",
        ["booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_waitlist_entries_preferred_service_id",
        "waitlist_entries",
        ["preferred_service_id"],
        unique=False,
    )
    op.create_index(
        "ix_waitlist_entries_status",
        "waitlist_entries",
        ["status"],
        unique=False,
    )
    op.execute(
        sa.text(
            "UPDATE waitlist_entries SET status = 'booked' WHERE status = 'converted'"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_waitlist_entries_status", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_preferred_service_id", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_booking_id", table_name="waitlist_entries")
    op.drop_constraint("fk_waitlist_entries_updated_by_id", "waitlist_entries", type_="foreignkey")
    op.drop_constraint("fk_waitlist_entries_created_by_id", "waitlist_entries", type_="foreignkey")
    op.drop_constraint("fk_waitlist_entries_preferred_service_id", "waitlist_entries", type_="foreignkey")
    op.drop_constraint("fk_waitlist_entries_booking_id", "waitlist_entries", type_="foreignkey")
    op.drop_column("waitlist_entries", "updated_by_id")
    op.drop_column("waitlist_entries", "created_by_id")
    op.drop_column("waitlist_entries", "notes")
    op.drop_column("waitlist_entries", "source")
    op.drop_column("waitlist_entries", "preferred_service_id")
    op.drop_column("waitlist_entries", "booking_id")
