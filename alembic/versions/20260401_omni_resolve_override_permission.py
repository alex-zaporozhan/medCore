"""RBAC: omni.chat.resolve.override (owner+manager by default).

Revision ID: 20260401_omni_resolve_override_permission
Revises: m9n8b7v6c5x4
Create Date: 2026-04-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260401_omni_resolve_override_permission"
down_revision: Union[str, Sequence[str], None] = "m9n8b7v6c5x4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description) VALUES
            (gen_random_uuid(), 'omni.chat.resolve.override', 'Омниканал: аварийное закрытие/resolve диалога несмотря на active lease')
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
            JOIN permissions p ON p.code = 'omni.chat.resolve.override'
            WHERE r.code IN ('owner', 'manager')
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
              AND p.code = 'omni.chat.resolve.override'
              AND r.code IN ('owner', 'manager')
            """
        )
    )
    conn.execute(sa.text("DELETE FROM permissions WHERE code = 'omni.chat.resolve.override'"))

