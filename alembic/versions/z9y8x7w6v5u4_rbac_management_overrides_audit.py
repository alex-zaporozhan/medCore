"""RBAC management: user overrides, audit log, rbac.manage permission.

Revision ID: z9y8x7w6v5u4
Revises: y1z2a3b4c5d6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "z9y8x7w6v5u4"
down_revision: Union[str, Sequence[str], None] = "y1z2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_permission_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("effect", sa.String(length=16), nullable=False),
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["admins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "clinic_id",
            "user_id",
            "permission_id",
            name="ux_user_permission_grants_clinic_user_permission",
        ),
    )
    op.create_index(
        "ix_user_permission_grants_user_effect",
        "user_permission_grants",
        ["clinic_id", "user_id", "effect"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_permission_grants_clinic_id"),
        "user_permission_grants",
        ["clinic_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_permission_grants_user_id"),
        "user_permission_grants",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "rbac_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("before_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_admin_id"], ["admins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rbac_audit_log_clinic_created",
        "rbac_audit_log",
        ["clinic_id", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_rbac_audit_log_actor_admin_id"), "rbac_audit_log", ["actor_admin_id"], unique=False)
    op.create_index(op.f("ix_rbac_audit_log_clinic_id"), "rbac_audit_log", ["clinic_id"], unique=False)

    op.execute(
        """
        INSERT INTO permissions (id, code, description)
        VALUES (gen_random_uuid(), 'rbac.manage', 'Управление ролями, персональными правами и политиками доступа')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT
            gen_random_uuid(),
            r.id,
            p.id
        FROM roles r
        JOIN permissions p ON p.code = 'rbac.manage'
        WHERE r.code = 'owner'
          AND (
            r.clinic_id IS NULL
            OR EXISTS (SELECT 1 FROM clinics c WHERE c.id = r.clinic_id)
          )
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (SELECT id FROM permissions WHERE code = 'rbac.manage')
        """
    )
    op.execute("DELETE FROM permissions WHERE code = 'rbac.manage'")
    op.drop_index(op.f("ix_rbac_audit_log_clinic_id"), table_name="rbac_audit_log")
    op.drop_index(op.f("ix_rbac_audit_log_actor_admin_id"), table_name="rbac_audit_log")
    op.drop_index("ix_rbac_audit_log_clinic_created", table_name="rbac_audit_log")
    op.drop_table("rbac_audit_log")
    op.drop_index(op.f("ix_user_permission_grants_user_id"), table_name="user_permission_grants")
    op.drop_index(op.f("ix_user_permission_grants_clinic_id"), table_name="user_permission_grants")
    op.drop_index("ix_user_permission_grants_user_effect", table_name="user_permission_grants")
    op.drop_table("user_permission_grants")

