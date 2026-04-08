"""Phase 1e: §24 catalog keys + embed API keys / webhook inbox settings.

Revision ID: 20260412_phase1e_embed_catalog_and_keys
Revises: 20260411_phase1b_catalog_plan_subscription_prices
Create Date: 2026-04-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260412_phase1e_embed_catalog_and_keys"
down_revision: Union[str, Sequence[str], None] = "20260411_phase1b_catalog_plan_subscription_prices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO platform_catalog_options (id, entitlement_key, display_name, description, list_price_rub, is_active, sort_order)
            VALUES
              ('a0000001-0000-4000-8000-000000000004'::uuid, 'marketing.attribution', 'Маркетинг / атрибуция', NULL, 1200.00, true, 15),
              ('a0000001-0000-4000-8000-000000000005'::uuid, 'retention.bundle', 'Ретеншн / возврат пациентов', NULL, 1800.00, true, 18),
              ('a0000001-0000-4000-8000-000000000006'::uuid, 'omni.embed.bundle', 'Embed-виджет + публичный периметр (§24)', 'Моно-пакет встраивания; API keys и webhook-инбокс', 4900.00, true, 40),
              ('a0000001-0000-4000-8000-000000000007'::uuid, 'ai.assistant.chat', 'AI-ассистент в чате (§24.2)', NULL, 2900.00, true, 50),
              ('a0000001-0000-4000-8000-000000000008'::uuid, 'ai.rag.org_kb', 'RAG база знаний организации (§24.3)', NULL, 3900.00, true, 60)
            ON CONFLICT (entitlement_key) DO NOTHING
            """
        )
    )

    op.create_table(
        "organization_embed_settings",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inbound_route_token", sa.Uuid(), nullable=False),
        sa.Column("webhook_bearer_hash", sa.String(length=255), nullable=True),
        sa.Column("webhook_bearer_prefix", sa.String(length=24), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id"),
        sa.UniqueConstraint("inbound_route_token", name="ux_organization_embed_settings_inbound_route_token"),
    )

    op.create_table(
        "organization_embed_api_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organization_embed_api_keys_organization_id",
        "organization_embed_api_keys",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_organization_embed_api_keys_organization_id", table_name="organization_embed_api_keys")
    op.drop_table("organization_embed_api_keys")
    op.drop_table("organization_embed_settings")

    op.execute(
        sa.text(
            """
            DELETE FROM platform_catalog_options
            WHERE entitlement_key IN (
              'marketing.attribution',
              'retention.bundle',
              'omni.embed.bundle',
              'ai.assistant.chat',
              'ai.rag.org_kb'
            )
            """
        )
    )
