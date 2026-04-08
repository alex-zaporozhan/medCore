"""Phase 1b: provision retry/DLQ columns, catalog plans/options (SaaS).

Revision ID: 20260408_phase1b_provision_retry_catalog
Revises: 20260407_phase1b_org_entitlements_owner_invite
Create Date: 2026-04-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260408_phase1b_provision_retry_catalog"
down_revision: Union[str, Sequence[str], None] = "20260407_phase1b_org_entitlements_owner_invite"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_catalog_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entitlement_key", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("list_price_rub", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entitlement_key", name="ux_platform_catalog_options_entitlement_key"),
    )

    op.create_table(
        "platform_catalog_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "option_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="ux_platform_catalog_plans_slug"),
    )

    op.add_column(
        "platform_signup_intents",
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "platform_signup_intents",
        sa.Column("provision_retry_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "platform_signup_intents",
        sa.Column("provision_next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "platform_signup_intents",
        sa.Column("provision_last_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "platform_signup_intents",
        sa.Column("provision_dead_letter", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    # Seed catalog (idempotent via fixed UUIDs)
    op.execute(
        sa.text(
            """
            INSERT INTO platform_catalog_options (id, entitlement_key, display_name, description, list_price_rub, is_active, sort_order)
            VALUES
              ('a0000001-0000-4000-8000-000000000001'::uuid, 'core.base', 'Базовый пакет', 'Орг, клиника, RBAC, расписание, базовые платежи', NULL, true, 0),
              ('a0000001-0000-4000-8000-000000000002'::uuid, 'tasks.kanban', 'Задачи / канбан', NULL, 1500.00, true, 10),
              ('a0000001-0000-4000-8000-000000000003'::uuid, 'crm.pipeline', 'CRM / воронка', NULL, 2800.00, true, 20)
            ON CONFLICT (entitlement_key) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO platform_catalog_plans (id, slug, display_name, description, option_keys, is_active, sort_order)
            VALUES (
              'b0000001-0000-4000-8000-000000000001'::uuid,
              'starter_rf',
              'Старт (РФ)',
              'База + задачи — пресет для лендинга',
              '["core.base", "tasks.kanban"]'::jsonb,
              true,
              0
            )
            ON CONFLICT (slug) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_column("platform_signup_intents", "provision_dead_letter")
    op.drop_column("platform_signup_intents", "provision_last_error")
    op.drop_column("platform_signup_intents", "provision_next_attempt_at")
    op.drop_column("platform_signup_intents", "provision_retry_count")
    op.drop_column("platform_signup_intents", "paid_at")
    op.drop_table("platform_catalog_plans")
    op.drop_table("platform_catalog_options")
