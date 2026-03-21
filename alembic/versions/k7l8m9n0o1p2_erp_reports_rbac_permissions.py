"""RBAC: permissions for ERP owner reports and attribution ROI (Engine L2 QA).

Revision ID: k7l8m9n0o1p2
Revises: j6k7l8m9n0o1
Create Date: 2026-03-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "k7l8m9n0o1p2"
down_revision: Union[str, Sequence[str], None] = "j6k7l8m9n0o1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description) VALUES
            (gen_random_uuid(), 'erp.owner_reports.read',
             'ERP-отчёты владельца (выручка по периодам, зарплата, склад, витрины)'),
            (gen_random_uuid(), 'attribution.reports.read',
             'Отчёты по атрибуции и ROI по источникам')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    # rbac_matrix: only base role `owner` gets these (manager/admin are excluded).
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code IN ('erp.owner_reports.read', 'attribution.reports.read')
            WHERE r.clinic_id IS NOT NULL AND r.code = 'owner'
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
                SELECT id FROM permissions WHERE code IN (
                    'erp.owner_reports.read', 'attribution.reports.read'
                )
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM permissions WHERE code IN (
                'erp.owner_reports.read', 'attribution.reports.read'
            )
            """
        )
    )
