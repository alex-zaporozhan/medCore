"""RBAC: patients PII read — owner / manager / admin only (QA_ARCH).

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6g7h8i9j0k1"
down_revision: Union[str, Sequence[str], None] = "e5f6g7h8i9j0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description) VALUES
            (gen_random_uuid(), 'patients.pii.read',
             'Просмотр и изменение ПД пациентов (списки, карточки, телефоны)')
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
            JOIN permissions p ON p.code = 'patients.pii.read'
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
                SELECT id FROM permissions WHERE code = 'patients.pii.read'
            )
            """
        )
    )
    conn.execute(sa.text("DELETE FROM permissions WHERE code = 'patients.pii.read'"))
