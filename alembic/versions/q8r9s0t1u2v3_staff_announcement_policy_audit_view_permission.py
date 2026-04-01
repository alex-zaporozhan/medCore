"""RBAC: staff.announcements.policy.audit.view (owner-only by default).

Revision ID: q8r9s0t1u2v3
Revises: p3q4r5s6t7u8
Create Date: 2026-03-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "q8r9s0t1u2v3"
down_revision: Union[str, Sequence[str], None] = "p3q4r5s6t7u8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description) VALUES
            (gen_random_uuid(), 'staff.announcements.policy.audit.view',
             'Просмотр журнала изменений политики запретов публикации объявлений')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    # Link to owner roles (both global and clinic-scoped).
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code = 'staff.announcements.policy.audit.view'
            WHERE r.code = 'owner'
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions rp
            USING roles r, permissions p
            WHERE rp.role_id = r.id
              AND rp.permission_id = p.id
              AND p.code = 'staff.announcements.policy.audit.view'
              AND r.code = 'owner'
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM permissions WHERE code = 'staff.announcements.policy.audit.view'
            """
        )
    )

