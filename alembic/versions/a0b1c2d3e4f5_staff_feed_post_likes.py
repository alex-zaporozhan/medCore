"""Staff feed post likes.

Revision ID: a0b1c2d3e4f5
Revises: z1a2b3c4d5e6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_feed_post_likes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["staff_feed_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_admin_id"], ["admins.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_unique_constraint(
        "ux_staff_feed_post_likes_post_admin",
        "staff_feed_post_likes",
        ["post_id", "author_admin_id"],
    )
    op.create_index(
        "ix_staff_feed_post_likes_post_id",
        "staff_feed_post_likes",
        ["post_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_staff_feed_post_likes_post_id", table_name="staff_feed_post_likes")
    op.drop_constraint(
        "ux_staff_feed_post_likes_post_admin",
        "staff_feed_post_likes",
        type_="unique",
    )
    op.drop_table("staff_feed_post_likes")

