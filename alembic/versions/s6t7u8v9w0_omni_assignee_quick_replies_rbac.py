"""Omni inbox: assignee on chats, quick replies table, RBAC omni.inbox.manage.

Revision ID: s6t7u8v9w0
Revises: q4r5s6t7u8
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "s6t7u8v9w0"
down_revision: Union[str, Sequence[str], None] = "q4r5s6t7u8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "omni_chats",
        sa.Column(
            "assignee_admin_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_omni_chats_assignee_admin_id_admins",
        "omni_chats",
        "admins",
        ["assignee_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_omni_chats_assignee_admin_id",
        "omni_chats",
        ["assignee_admin_id"],
        unique=False,
    )

    op.create_table(
        "omni_quick_replies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_omni_quick_replies_clinic_id", "omni_quick_replies", ["clinic_id"], unique=False)

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description) VALUES
            (gen_random_uuid(), 'omni.inbox.manage',
             'Омниканал: назначение диалогов, статусы, быстрые ответы')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    for role_code in ("owner", "manager", "admin"):
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions (id, role_id, permission_id, created_at)
                SELECT gen_random_uuid(), r.id, p.id, now()
                FROM roles r
                JOIN permissions p ON p.code = 'omni.inbox.manage'
                WHERE r.clinic_id IS NOT NULL AND r.code = :role_code
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ),
            {"role_code": role_code},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE code = 'omni.inbox.manage'
            )
            """
        )
    )
    conn.execute(sa.text("DELETE FROM permissions WHERE code = 'omni.inbox.manage'"))
    op.drop_index("ix_omni_quick_replies_clinic_id", table_name="omni_quick_replies")
    op.drop_table("omni_quick_replies")
    op.drop_index("ix_omni_chats_assignee_admin_id", table_name="omni_chats")
    op.drop_constraint("fk_omni_chats_assignee_admin_id_admins", "omni_chats", type_="foreignkey")
    op.drop_column("omni_chats", "assignee_admin_id")
