"""Staff collab layer 2: DM/group rooms, task rooms, attachments, calendar reminders.

Revision ID: z1a2b3c4d5e6
Revises: y8z9a0b1c2d3
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "z1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "y8z9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ux_staff_chat_rooms_clinic_kind", table_name="staff_chat_rooms")
    op.create_index(
        "ux_staff_chat_one_general_per_clinic",
        "staff_chat_rooms",
        ["clinic_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'GENERAL'"),
    )
    op.add_column(
        "staff_chat_rooms",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "staff_chat_rooms",
        sa.Column("dm_pair_key", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "staff_chat_rooms",
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_staff_chat_rooms_task_id",
        "staff_chat_rooms",
        "tasks",
        ["task_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_staff_chat_rooms_created_by",
        "staff_chat_rooms",
        "admins",
        ["created_by_admin_id"],
        ["id"],
    )
    op.create_index(
        "ux_staff_chat_rooms_clinic_dm_pair",
        "staff_chat_rooms",
        ["clinic_id", "dm_pair_key"],
        unique=True,
        postgresql_where=sa.text("dm_pair_key IS NOT NULL"),
    )
    op.create_index(
        "ix_staff_chat_rooms_task_id",
        "staff_chat_rooms",
        ["task_id"],
        unique=True,
        postgresql_where=sa.text("task_id IS NOT NULL"),
    )

    op.create_table(
        "staff_chat_message_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["staff_chat_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_staff_chat_attachments_message_id",
        "staff_chat_message_attachments",
        ["message_id"],
    )

    op.add_column(
        "staff_calendar_events",
        sa.Column("reminder_minutes_before", sa.Integer(), nullable=True),
    )

    op.create_table(
        "staff_calendar_reminder_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fire_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["staff_calendar_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="ux_staff_cal_rem_delivery_event"),
    )
    op.create_index(
        "ix_staff_cal_rem_delivery_fire",
        "staff_calendar_reminder_deliveries",
        ["fire_at"],
        postgresql_where=sa.text("sent_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_staff_cal_rem_delivery_fire", table_name="staff_calendar_reminder_deliveries")
    op.drop_table("staff_calendar_reminder_deliveries")
    op.drop_column("staff_calendar_events", "reminder_minutes_before")

    op.drop_index("ix_staff_chat_attachments_message_id", table_name="staff_chat_message_attachments")
    op.drop_table("staff_chat_message_attachments")

    op.drop_index("ix_staff_chat_rooms_task_id", table_name="staff_chat_rooms")
    op.drop_index("ux_staff_chat_rooms_clinic_dm_pair", table_name="staff_chat_rooms")
    op.drop_constraint("fk_staff_chat_rooms_created_by", "staff_chat_rooms", type_="foreignkey")
    op.drop_constraint("fk_staff_chat_rooms_task_id", "staff_chat_rooms", type_="foreignkey")
    op.drop_column("staff_chat_rooms", "created_by_admin_id")
    op.drop_column("staff_chat_rooms", "dm_pair_key")
    op.drop_column("staff_chat_rooms", "task_id")

    op.drop_index("ux_staff_chat_one_general_per_clinic", table_name="staff_chat_rooms")
    op.create_index(
        "ux_staff_chat_rooms_clinic_kind",
        "staff_chat_rooms",
        ["clinic_id", "kind"],
        unique=True,
    )
