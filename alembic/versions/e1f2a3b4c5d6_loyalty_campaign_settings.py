"""Loyalty campaign settings + RBAC for LOY_AI_014.

Revision ID: e1f2a3b4c5d6
Revises: d3e4f5a6b7c8
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "loyalty_campaign_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "expiring_packages_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "high_balance_low_activity_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "reengagement_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "channel_tasks_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "channel_omnichannel_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "max_contacts_per_day_clinic",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("50"),
        ),
        sa.Column(
            "max_contacts_per_day_patient",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3"),
        ),
        sa.Column(
            "campaign_cooldown_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("14"),
        ),
        sa.Column(
            "reengagement_inactive_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("180"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.UniqueConstraint("clinic_id", name="ux_loyalty_campaign_settings_clinic"),
    )
    op.create_index(
        "ix_loyalty_campaign_settings_clinic_id",
        "loyalty_campaign_settings",
        ["clinic_id"],
        unique=False,
    )

    op.alter_column(
        "tasks",
        "attention_kind",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=True,
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO permissions (id, code, description) VALUES "
            "(gen_random_uuid(), 'manage_loyalty_campaigns', "
            "'Настройки кампаний лояльности (флаги, лимиты, каналы)'), "
            "(gen_random_uuid(), 'run_loyalty_campaigns', "
            "'Запуск кампаний лояльности (оператор/система)') "
            "ON CONFLICT (code) DO NOTHING"
        )
    )

    res = conn.execute(sa.text("SELECT id, code FROM permissions WHERE code IN "
                               "('manage_loyalty_campaigns', 'run_loyalty_campaigns')"))
    perm_by_code = {row[1]: row[0] for row in res}

    roles_res = conn.execute(
        sa.text("SELECT id, code FROM roles WHERE clinic_id IS NULL")
    )
    role_by_code = {row[1]: row[0] for row in roles_res}

    def link(role_code: str, perm_codes: list[str]) -> None:
        rid = role_by_code.get(role_code)
        if not rid:
            return
        for pc in perm_codes:
            pid = perm_by_code.get(pc)
            if not pid:
                continue
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (id, role_id, permission_id, created_at) "
                    "VALUES (gen_random_uuid(), :rid, :pid, now()) "
                    "ON CONFLICT (role_id, permission_id) DO NOTHING"
                ),
                {"rid": rid, "pid": pid},
            )

    mid = perm_by_code.get("manage_loyalty_campaigns")
    rid_run = perm_by_code.get("run_loyalty_campaigns")
    if mid and rid_run:
        link("owner", ["manage_loyalty_campaigns", "run_loyalty_campaigns"])
        link("manager", ["manage_loyalty_campaigns", "run_loyalty_campaigns"])
        link("admin", ["run_loyalty_campaigns"])


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code IN "
            "('manage_loyalty_campaigns', 'run_loyalty_campaigns'))"
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN "
            "('manage_loyalty_campaigns', 'run_loyalty_campaigns')"
        )
    )

    op.alter_column(
        "tasks",
        "attention_kind",
        existing_type=sa.String(length=64),
        type_=sa.String(length=32),
        existing_nullable=True,
    )

    op.drop_index("ix_loyalty_campaign_settings_clinic_id", table_name="loyalty_campaign_settings")
    op.drop_table("loyalty_campaign_settings")
