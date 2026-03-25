"""Staff feed: title + file attachments on posts.

Revision ID: g8h9i0j1k2l3
Revises: f6g7h8i9j0k1
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g8h9i0j1k2l3"
down_revision: Union[str, Sequence[str], None] = "f6g7h8i9j0k1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "staff_feed_posts",
        sa.Column("title", sa.String(length=500), nullable=True),
    )
    op.create_table(
        "staff_feed_post_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["staff_feed_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_staff_feed_post_attachments_post_id",
        "staff_feed_post_attachments",
        ["post_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_staff_feed_post_attachments_post_id", table_name="staff_feed_post_attachments")
    op.drop_table("staff_feed_post_attachments")
    op.drop_column("staff_feed_posts", "title")
