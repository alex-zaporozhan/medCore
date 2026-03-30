"""Staff feed: replies to comments (parent_comment_id).

Revision ID: w3x4y5z6a7
Revises: v2w3x4y5z6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "w3x4y5z6a7"
down_revision: Union[str, Sequence[str], None] = "v2w3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "staff_feed_comments",
        sa.Column("parent_comment_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_staff_feed_comments_parent_comment_id",
        "staff_feed_comments",
        ["parent_comment_id"],
    )
    op.create_foreign_key(
        "fk_staff_feed_comments_parent_comment_id",
        "staff_feed_comments",
        "staff_feed_comments",
        ["parent_comment_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_staff_feed_comments_parent_comment_id",
        "staff_feed_comments",
        type_="foreignkey",
    )
    op.drop_index("ix_staff_feed_comments_parent_comment_id", table_name="staff_feed_comments")
    op.drop_column("staff_feed_comments", "parent_comment_id")
