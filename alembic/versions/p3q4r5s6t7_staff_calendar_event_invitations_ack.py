"""Staff calendar event invitations (ack "я увидел").

Revision ID: p3q4r5s6t7
Revises: b1c2d3e4f5g6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p3q4r5s6t7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5g6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_calendar_event_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invitee_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("acknowledged_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["staff_calendar_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invitee_admin_id"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "invitee_admin_id",
            name="uq_staff_calendar_event_invitations_event_invitee",
        ),
    )

    op.create_index(
        "ix_staff_calendar_event_invitations_clinic_invitee_ack",
        "staff_calendar_event_invitations",
        ["clinic_id", "invitee_admin_id", "acknowledged_at"],
    )
    op.create_index(
        "ix_staff_calendar_event_invitations_event_id",
        "staff_calendar_event_invitations",
        ["event_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staff_calendar_event_invitations_event_id",
        table_name="staff_calendar_event_invitations",
    )
    op.drop_index(
        "ix_staff_calendar_event_invitations_clinic_invitee_ack",
        table_name="staff_calendar_event_invitations",
    )
    op.drop_table("staff_calendar_event_invitations")

