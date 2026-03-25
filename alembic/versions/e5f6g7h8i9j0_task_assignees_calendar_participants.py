"""Task assignees (multi) + calendar event participants + RBAC invite.

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6g7h8i9j0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_assignees",
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("admin_id", sa.Uuid(), sa.ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_task_assignees_task_id", "task_assignees", ["task_id"])
    op.create_index("ix_task_assignees_admin_id", "task_assignees", ["admin_id"])

    op.create_table(
        "staff_calendar_event_participants",
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("staff_calendar_events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("admin_id", sa.Uuid(), sa.ForeignKey("admins.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_calendar_participants_event", "staff_calendar_event_participants", ["event_id"])

    op.execute(
        sa.text(
            """
            INSERT INTO staff_calendar_event_participants (event_id, admin_id)
            SELECT e.id, e.created_by_admin_id FROM staff_calendar_events e
            WHERE NOT EXISTS (
                SELECT 1 FROM staff_calendar_event_participants p
                WHERE p.event_id = e.id AND p.admin_id = e.created_by_admin_id
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO task_assignees (task_id, admin_id)
            SELECT t.id, t.assignee_id FROM tasks t
            WHERE t.assignee_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM task_assignees ta
                WHERE ta.task_id = t.id AND ta.admin_id = t.assignee_id
            )
            """
        )
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description) VALUES
            (gen_random_uuid(), 'invite_staff_calendar_participants',
             'Приглашение участников на события календаря (совещания)')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code = 'invite_staff_calendar_participants'
            WHERE r.clinic_id IS NOT NULL AND r.code IN ('owner', 'manager', 'admin')
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE code = 'invite_staff_calendar_participants'
            )
            """
        )
    )
    conn.execute(sa.text("DELETE FROM permissions WHERE code = 'invite_staff_calendar_participants'"))
    op.drop_index("ix_calendar_participants_event", table_name="staff_calendar_event_participants")
    op.drop_table("staff_calendar_event_participants")
    op.drop_index("ix_task_assignees_admin_id", table_name="task_assignees")
    op.drop_index("ix_task_assignees_task_id", table_name="task_assignees")
    op.drop_table("task_assignees")
