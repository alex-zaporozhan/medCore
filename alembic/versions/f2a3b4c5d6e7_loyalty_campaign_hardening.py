"""LOY campaign: SMS dedupe flag, tasks index, RBAC for clinic-scoped roles.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "loyalty_campaign_settings",
        sa.Column(
            "skip_expiring_task_if_sms_expiring_sent_today",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    op.create_index(
        "ix_tasks_loyalty_campaign_lookup",
        "tasks",
        ["clinic_id", "patient_id", "attention_kind", "created_at"],
        postgresql_where=sa.text("attention_kind LIKE 'LOYALTY_%'"),
    )

    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code IN ('manage_loyalty_campaigns', 'run_loyalty_campaigns')
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
            JOIN permissions p ON p.code IN ('manage_loyalty_campaigns', 'run_loyalty_campaigns')
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
            JOIN permissions p ON p.code = 'run_loyalty_campaigns'
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
                SELECT id FROM permissions WHERE code IN (
                    'manage_loyalty_campaigns', 'run_loyalty_campaigns'
                )
            )
            AND role_id IN (SELECT id FROM roles WHERE clinic_id IS NOT NULL)
            """
        )
    )

    op.drop_index("ix_tasks_loyalty_campaign_lookup", table_name="tasks")
    op.drop_column(
        "loyalty_campaign_settings",
        "skip_expiring_task_if_sms_expiring_sent_today",
    )
