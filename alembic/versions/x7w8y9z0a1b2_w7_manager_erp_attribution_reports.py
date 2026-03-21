"""W7 SR5: grant manager role ERP owner reports + attribution read (QA_ARCH).

Revision ID: x7w8y9z0a1b2
Revises: w5perf1idx_fin
Create Date: 2026-03-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "x7w8y9z0a1b2"
down_revision = "w5perf1idx_fin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code IN ('erp.owner_reports.read', 'attribution.reports.read')
            WHERE r.clinic_id IS NOT NULL AND r.code = 'manager'
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
            WHERE role_id IN (
                SELECT id FROM roles WHERE clinic_id IS NOT NULL AND code = 'manager'
            )
            AND permission_id IN (
                SELECT id FROM permissions WHERE code IN (
                    'erp.owner_reports.read', 'attribution.reports.read'
                )
            )
            """
        )
    )
