"""Platform SaaS billing contour B: signup intent + subscription payments.

Revision ID: 20260406_platform_billing_contour_b
Revises: 20260401_omni_resolve_override_permission
Create Date: 2026-04-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260406_platform_billing_contour_b"
down_revision: Union[str, Sequence[str], None] = "20260401_omni_resolve_override_permission"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_signup_intents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending_payment", nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("tariff_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_signup_intents_organization_id",
        "platform_signup_intents",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "platform_subscription_payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("signup_intent_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=8), server_default="RUB", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("webhook_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["signup_intent_id"],
            ["platform_signup_intents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_payment_id", name="ux_platform_sub_payments_provider_id"),
    )
    op.create_index(
        "ix_platform_subscription_payments_signup_intent_id",
        "platform_subscription_payments",
        ["signup_intent_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_platform_subscription_payments_signup_intent_id", table_name="platform_subscription_payments")
    op.drop_table("platform_subscription_payments")
    op.drop_index("ix_platform_signup_intents_organization_id", table_name="platform_signup_intents")
    op.drop_table("platform_signup_intents")
