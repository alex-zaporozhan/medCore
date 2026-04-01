"""Staff feed: comment soft-delete + announcements publish policy + RBAC permission.

Revision ID: h7i8j9k0l1m2
Revises: f3a4b5c6d7e8
Create Date: 2026-03-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "h7i8j9k0l1m2"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Staff feed comments: edit + soft-delete metadata
    op.add_column(
        "staff_feed_comments",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "staff_feed_comments",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "staff_feed_comments",
        sa.Column("deleted_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_staff_feed_comments_deleted_by_admin_id",
        "staff_feed_comments",
        "admins",
        ["deleted_by_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_staff_feed_comments_deleted_at",
        "staff_feed_comments",
        ["deleted_at"],
    )

    # Announcements publish policy (deny/allow per role or user)
    op.create_table(
        "staff_announcement_publish_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=16), nullable=False),  # role | user
        sa.Column("scope_value", sa.String(length=64), nullable=False),  # role code or admin UUID string
        sa.Column("can_publish", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("clinic_id", "scope_type", "scope_value", name="ux_staff_announce_policy_scope"),
    )
    op.create_index(
        "ix_staff_announce_policy_clinic",
        "staff_announcement_publish_policies",
        ["clinic_id"],
    )

    # RBAC: allow trusted roles to moderate feed comments (doctor excluded).
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description) VALUES
            (gen_random_uuid(), 'staff.feed.comments.moderate',
             'Модерация комментариев в ленте персонала (удаление чужих комментариев)')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
            SELECT gen_random_uuid(), r.id, p.id, now()
            FROM roles r
            JOIN permissions p ON p.code = 'staff.feed.comments.moderate'
            WHERE r.code IN ('owner', 'manager', 'admin')
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions rp
            USING roles r, permissions p
            WHERE rp.role_id = r.id
              AND rp.permission_id = p.id
              AND p.code = 'staff.feed.comments.moderate'
              AND r.code IN ('owner', 'manager', 'admin')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM permissions WHERE code = 'staff.feed.comments.moderate'
            """
        )
    )

    op.drop_index("ix_staff_announce_policy_clinic", table_name="staff_announcement_publish_policies")
    op.drop_table("staff_announcement_publish_policies")

    op.drop_index("ix_staff_feed_comments_deleted_at", table_name="staff_feed_comments")
    op.drop_constraint(
        "fk_staff_feed_comments_deleted_by_admin_id",
        "staff_feed_comments",
        type_="foreignkey",
    )
    op.drop_column("staff_feed_comments", "deleted_by_admin_id")
    op.drop_column("staff_feed_comments", "deleted_at")
    op.drop_column("staff_feed_comments", "updated_at")

