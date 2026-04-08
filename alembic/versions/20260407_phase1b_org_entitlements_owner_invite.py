"""Phase 1b: organization_entitlements + owner invite columns on platform_signup_intents.

Revision ID: 20260407_phase1b_org_entitlements_owner_invite
Revises: 20260406_platform_billing_contour_b
Create Date: 2026-04-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260407_phase1b_org_entitlements_owner_invite"
down_revision: Union[str, Sequence[str], None] = "20260406_platform_billing_contour_b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_entitlements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("entitlement_key", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="tariff_snapshot", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "entitlement_key", name="ux_org_entitlements_org_key"),
    )
    op.create_index(
        "ix_organization_entitlements_organization_id",
        "organization_entitlements",
        ["organization_id"],
        unique=False,
    )

    op.add_column(
        "platform_signup_intents",
        sa.Column("provisioned_admin_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "platform_signup_intents",
        sa.Column("owner_invite_token_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "platform_signup_intents",
        sa.Column("owner_invite_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_platform_signup_intents_provisioned_admin_id",
        "platform_signup_intents",
        "admins",
        ["provisioned_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_platform_signup_intents_provisioned_admin_id",
        "platform_signup_intents",
        ["provisioned_admin_id"],
        unique=False,
    )
    op.create_index(
        "ux_platform_signup_intents_invite_hash",
        "platform_signup_intents",
        ["owner_invite_token_hash"],
        unique=True,
        postgresql_where=sa.text("owner_invite_token_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_platform_signup_intents_invite_hash",
        table_name="platform_signup_intents",
        postgresql_where=sa.text("owner_invite_token_hash IS NOT NULL"),
    )
    op.drop_index("ix_platform_signup_intents_provisioned_admin_id", table_name="platform_signup_intents")
    op.drop_constraint("fk_platform_signup_intents_provisioned_admin_id", "platform_signup_intents", type_="foreignkey")
    op.drop_column("platform_signup_intents", "owner_invite_expires_at")
    op.drop_column("platform_signup_intents", "owner_invite_token_hash")
    op.drop_column("platform_signup_intents", "provisioned_admin_id")

    op.drop_index("ix_organization_entitlements_organization_id", table_name="organization_entitlements")
    op.drop_table("organization_entitlements")
