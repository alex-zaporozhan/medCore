"""1a-E3 TOTP columns on platform_founder_users; 1a-E5 optional RLS on organization_entitlements (GUC-gated).

Revision ID: 20260423_phase1a_founder_totp_org_ent_rls
Revises: 20260422_platform_founder_users
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260423_phase1a_founder_totp_org_ent_rls"
down_revision: Union[str, Sequence[str], None] = "20260422_platform_founder_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_founder_users",
        sa.Column("totp_secret_ciphertext", sa.Text(), nullable=True),
    )
    op.add_column(
        "platform_founder_users",
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column("platform_founder_users", "totp_enabled", server_default=None)

    # RLS: default bypass when app.rls_org_entitlements is unset/off; tests set to 'on' + app.effective_organization_id.
    # One statement per op.execute: asyncpg cannot run multiple commands in a prepared statement.
    op.execute("ALTER TABLE organization_entitlements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE organization_entitlements FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY organization_entitlements_tenant_scope ON organization_entitlements
        FOR ALL
        USING (
          COALESCE(NULLIF(btrim(current_setting('app.rls_org_entitlements', true)), ''), 'off') <> 'on'
          OR organization_id = NULLIF(btrim(current_setting('app.effective_organization_id', true)), '')::uuid
        )
        WITH CHECK (
          COALESCE(NULLIF(btrim(current_setting('app.rls_org_entitlements', true)), ''), 'off') <> 'on'
          OR organization_id = NULLIF(btrim(current_setting('app.effective_organization_id', true)), '')::uuid
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS organization_entitlements_tenant_scope ON organization_entitlements;")
    op.execute("ALTER TABLE organization_entitlements NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE organization_entitlements DISABLE ROW LEVEL SECURITY;")
    op.drop_column("platform_founder_users", "totp_enabled")
    op.drop_column("platform_founder_users", "totp_secret_ciphertext")
