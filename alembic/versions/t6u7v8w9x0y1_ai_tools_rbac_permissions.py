"""RBAC: booking AI tools + AI task runner permissions (QA_ARCH W4.1 C6/C7).

Revision ID: t6u7v8w9x0y1
Revises: r4s5t6u7v8w9
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "t6u7v8w9x0y1"
down_revision: Union[str, Sequence[str], None] = "r4s5t6u7v8w9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description) VALUES
            (gen_random_uuid(), 'booking.ai_tools.use',
             'Использование AI-инструментов записи (слоты, создание/перенос/отмена через Omni)'),
            (gen_random_uuid(), 'ai.tasks.run',
             'Запуск AI Task Manager / анализа attention для генерации задач')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    # Per-clinic roles: owner + manager get both; admin gets booking tools only.
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code IN ('booking.ai_tools.use', 'ai.tasks.run')
            WHERE r.clinic_id IS NOT NULL AND r.code = 'owner'
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code IN ('booking.ai_tools.use', 'ai.tasks.run')
            WHERE r.clinic_id IS NOT NULL AND r.code = 'manager'
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code = 'booking.ai_tools.use'
            WHERE r.clinic_id IS NOT NULL AND r.code = 'admin'
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
                SELECT id FROM permissions WHERE code IN ('booking.ai_tools.use', 'ai.tasks.run')
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM permissions WHERE code IN ('booking.ai_tools.use', 'ai.tasks.run')
            """
        )
    )
