"""RBAC: patients.pii.read для глобальных ролей owner/manager/admin.

Миграция f6g7h8i9j0k1 связывала право только с ролями ``clinic_id IS NOT NULL``.
В проде и в dev часто используются глобальные роли (``clinic_id IS NULL``) из
``seed_rbac_baseline`` — у таких администраторов не было ``patients.pii.read``,
хотя матрица ``rbac_matrix.ROLE_PERMISSIONS`` это право для роли admin предусматривает.

Revision ID: v2w3x4y5z6
Revises: u1v2w3x4y5
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v2w3x4y5z6"
down_revision: Union[str, Sequence[str], None] = "u1v2w3x4y5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code = 'patients.pii.read'
            WHERE r.clinic_id IS NULL AND r.code IN ('owner', 'manager', 'admin')
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
              AND p.code = 'patients.pii.read'
              AND r.clinic_id IS NULL
              AND r.code IN ('owner', 'manager', 'admin')
            """
        )
    )
