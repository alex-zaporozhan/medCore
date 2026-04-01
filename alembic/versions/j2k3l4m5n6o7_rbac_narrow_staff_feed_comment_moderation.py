"""RBAC: narrow staff feed comment moderation (remove from admin role).

Revision ID: j2k3l4m5n6o7
Revises: h7i8j9k0l1m2
Create Date: 2026-03-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "j2k3l4m5n6o7"
down_revision: Union[str, Sequence[str], None] = "h7i8j9k0l1m2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions rp
            USING roles r, permissions p
            WHERE rp.role_id = r.id
              AND rp.permission_id = p.id
              AND p.code = 'staff.feed.comments.moderate'
              AND r.code = 'admin'
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code = 'staff.feed.comments.moderate'
            WHERE r.code = 'admin'
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )

