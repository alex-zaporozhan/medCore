"""P1 Staff Core: feed, staff chat, calendar, knowledge + RBAC.

Revision ID: y8z9a0b1c2d3
Revises: x7w8y9z0a1b2
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "y8z9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "x7w8y9z0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_feed_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["author_admin_id"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_feed_posts_clinic_created", "staff_feed_posts", ["clinic_id", "created_at"])

    op.create_table(
        "staff_feed_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["post_id"], ["staff_feed_posts.id"]),
        sa.ForeignKeyConstraint(["author_admin_id"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_feed_comments_post_id", "staff_feed_comments", ["post_id"])

    op.create_table(
        "staff_chat_rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_staff_chat_rooms_clinic_kind",
        "staff_chat_rooms",
        ["clinic_id", "kind"],
        unique=True,
    )

    op.create_table(
        "staff_chat_room_members",
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_read_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["room_id"], ["staff_chat_rooms.id"]),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"]),
        sa.PrimaryKeyConstraint("room_id", "admin_id"),
    )

    op.create_table(
        "staff_chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["staff_chat_rooms.id"]),
        sa.ForeignKeyConstraint(["author_admin_id"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_staff_chat_messages_room_created",
        "staff_chat_messages",
        ["room_id", "created_at"],
    )

    op.create_table(
        "staff_calendar_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ends_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admins.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_staff_calendar_events_clinic_starts",
        "staff_calendar_events",
        ["clinic_id", "starts_at"],
    )

    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folder_key", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column(
            "visible_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[\"owner\", \"manager\", \"admin\", \"doctor\"]'::jsonb"),
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_documents_clinic_folder", "knowledge_documents", ["clinic_id", "folder_key"])

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description) VALUES
            (gen_random_uuid(), 'view_staff_collab',
             'Просмотр ленты персонала, внутреннего чата, календаря и базы знаний'),
            (gen_random_uuid(), 'manage_staff_collab',
             'Публикация в ленту, сообщения в чате персонала, события календаря, статьи БЗ')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    for role_code in ("owner", "manager", "admin", "doctor"):
        conn.execute(
            sa.text(
                f"""
                INSERT INTO role_permissions (id, role_id, permission_id, created_at)
                SELECT gen_random_uuid(), r.id, p.id, now()
                FROM roles r
                JOIN permissions p ON p.code IN ('view_staff_collab', 'manage_staff_collab')
                WHERE r.clinic_id IS NOT NULL AND r.code = '{role_code}'
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
                SELECT id FROM permissions WHERE code IN ('view_staff_collab', 'manage_staff_collab')
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM permissions WHERE code IN ('view_staff_collab', 'manage_staff_collab')
            """
        )
    )

    op.drop_index("ix_knowledge_documents_clinic_folder", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
    op.drop_index("ix_staff_calendar_events_clinic_starts", table_name="staff_calendar_events")
    op.drop_table("staff_calendar_events")
    op.drop_index("ix_staff_chat_messages_room_created", table_name="staff_chat_messages")
    op.drop_table("staff_chat_messages")
    op.drop_table("staff_chat_room_members")
    op.drop_index("ux_staff_chat_rooms_clinic_kind", table_name="staff_chat_rooms")
    op.drop_table("staff_chat_rooms")
    op.drop_index("ix_staff_feed_comments_post_id", table_name="staff_feed_comments")
    op.drop_table("staff_feed_comments")
    op.drop_index("ix_staff_feed_posts_clinic_created", table_name="staff_feed_posts")
    op.drop_table("staff_feed_posts")
