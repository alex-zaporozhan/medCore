"""Task boards: one clinic-wide board per clinic; RBAC tasks.manage_clinic_board.

Deduplicates legacy duplicate clinic_wide rows before creating a partial unique index.

Revision ID: k9j8h7g6f5e4
Revises: n1o2p3q4r5s6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k9j8h7g6f5e4"
down_revision: Union[str, Sequence[str], None] = "n1o2p3q4r5s6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            WITH keeper AS (
              SELECT DISTINCT ON (clinic_id) id
              FROM task_boards
              WHERE kind = 'clinic_wide' AND owner_admin_id IS NULL
              ORDER BY clinic_id, id
            ),
            doomed AS (
              SELECT tb.id
              FROM task_boards tb
              WHERE tb.kind = 'clinic_wide'
                AND tb.owner_admin_id IS NULL
                AND tb.id NOT IN (SELECT id FROM keeper)
            )
            DELETE FROM task_board_columns
            WHERE board_id IN (SELECT id FROM doomed)
            """
        )
    )
    conn.execute(
        sa.text(
            """
            WITH keeper AS (
              SELECT DISTINCT ON (clinic_id) id
              FROM task_boards
              WHERE kind = 'clinic_wide' AND owner_admin_id IS NULL
              ORDER BY clinic_id, id
            ),
            doomed AS (
              SELECT tb.id
              FROM task_boards tb
              WHERE tb.kind = 'clinic_wide'
                AND tb.owner_admin_id IS NULL
                AND tb.id NOT IN (SELECT id FROM keeper)
            )
            DELETE FROM task_boards WHERE id IN (SELECT id FROM doomed)
            """
        )
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_task_boards_clinic_wide_one
        ON task_boards (clinic_id)
        WHERE kind = 'clinic_wide' AND owner_admin_id IS NULL
        """
    )
    op.execute(
        """
        INSERT INTO permissions (id, code, description, created_at)
        VALUES (
          gen_random_uuid(),
          'tasks.manage_clinic_board',
          'Изменение общей доски Kanban клиники (порядок колонок)',
          now()
        )
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code = 'tasks.manage_clinic_board'
        WHERE r.code IN ('owner', 'manager')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
          SELECT id FROM permissions WHERE code = 'tasks.manage_clinic_board'
        )
        """
    )
    op.execute(
        """
        DELETE FROM permissions WHERE code = 'tasks.manage_clinic_board'
        """
    )
    op.execute("DROP INDEX IF EXISTS uq_task_boards_clinic_wide_one")
