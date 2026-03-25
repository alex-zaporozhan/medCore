"""Staff chat room membership_kind: task_core vs invite, sync on assignee change.

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "staff_chat_room_members",
        sa.Column("membership_kind", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "ix_staff_chat_room_members_room_kind",
        "staff_chat_room_members",
        ["room_id", "membership_kind"],
        unique=False,
    )
    # Backfill: разделить «ядро» задачи и приглашённых в TASK-комнатах; прочие типы комнат.
    op.execute(
        """
        UPDATE staff_chat_room_members AS m
        SET membership_kind = CASE
            WHEN r.kind = 'TASK' AND t.id IS NOT NULL
                 AND (m.admin_id = t.creator_id OR m.admin_id = t.assignee_id)
                THEN 'task_core'
            WHEN r.kind = 'TASK' THEN 'invite'
            WHEN r.kind = 'GENERAL' THEN 'general'
            WHEN r.kind = 'GROUP' THEN 'group'
            WHEN r.kind = 'DM' THEN 'dm'
            ELSE NULL
        END
        FROM staff_chat_rooms AS r
        LEFT JOIN tasks AS t ON t.id = r.task_id AND r.kind = 'TASK'
        WHERE m.room_id = r.id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_staff_chat_room_members_room_kind", table_name="staff_chat_room_members")
    op.drop_column("staff_chat_room_members", "membership_kind")
