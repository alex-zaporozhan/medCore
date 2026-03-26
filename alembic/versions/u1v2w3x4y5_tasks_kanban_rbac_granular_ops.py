"""Tasks: granular RBAC permissions for kanban operations.

Revision ID: u1v2w3x4y5
Revises: t7u8v9w0x1
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "u1v2w3x4y5"
down_revision: Union[str, Sequence[str], None] = "t7u8v9w0x1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permissions (id, code, description, created_at)
        VALUES
          (gen_random_uuid(), 'tasks.change_status', 'Смена статуса задач', now()),
          (gen_random_uuid(), 'tasks.unblock', 'Снятие блокировки задач', now()),
          (gen_random_uuid(), 'tasks.bulk_status', 'Массовая смена статуса задач', now()),
          (gen_random_uuid(), 'tasks.reprioritize', 'Изменение приоритета/ранга задач', now())
        ON CONFLICT (code) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code IN (
          'tasks.change_status',
          'tasks.unblock',
          'tasks.bulk_status',
          'tasks.reprioritize'
        )
        WHERE r.code IN ('owner', 'manager', 'admin')
        ON CONFLICT DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code = 'tasks.change_status'
        WHERE r.code = 'doctor'
        ON CONFLICT DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
          SELECT id FROM permissions WHERE code IN (
            'tasks.change_status',
            'tasks.unblock',
            'tasks.bulk_status',
            'tasks.reprioritize'
          )
        );
        """
    )
    op.execute(
        """
        DELETE FROM permissions
        WHERE code IN (
          'tasks.change_status',
          'tasks.unblock',
          'tasks.bulk_status',
          'tasks.reprioritize'
        );
        """
    )
