"""staff attention announcements + read receipts

Revision ID: y1z2a3b4c5d6
Revises: v2w3x4y5z6
Create Date: 2026-03-30 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "y1z2a3b4c5d6"
down_revision = "v2w3x4y5z6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "staff_feed_posts",
        sa.Column("is_announcement", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "staff_feed_posts",
        sa.Column("priority_level", sa.String(length=32), nullable=False, server_default=sa.text("'normal'")),
    )
    op.add_column(
        "staff_feed_posts",
        sa.Column("requires_ack", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "staff_feed_posts",
        sa.Column("audience_roles", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "staff_feed_posts",
        sa.Column("audience_admin_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )

    op.create_table(
        "staff_feed_post_acks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"]),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["staff_feed_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "admin_id", name="ux_staff_feed_post_acks_post_admin"),
    )
    op.create_index("ix_staff_feed_post_acks_post_id", "staff_feed_post_acks", ["post_id"], unique=False)
    op.create_index(op.f("ix_staff_feed_post_acks_admin_id"), "staff_feed_post_acks", ["admin_id"], unique=False)
    op.create_index(op.f("ix_staff_feed_post_acks_clinic_id"), "staff_feed_post_acks", ["clinic_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_staff_feed_post_acks_clinic_id"), table_name="staff_feed_post_acks")
    op.drop_index(op.f("ix_staff_feed_post_acks_admin_id"), table_name="staff_feed_post_acks")
    op.drop_index("ix_staff_feed_post_acks_post_id", table_name="staff_feed_post_acks")
    op.drop_table("staff_feed_post_acks")
    op.drop_column("staff_feed_posts", "audience_admin_ids")
    op.drop_column("staff_feed_posts", "audience_roles")
    op.drop_column("staff_feed_posts", "requires_ack")
    op.drop_column("staff_feed_posts", "priority_level")
    op.drop_column("staff_feed_posts", "is_announcement")

