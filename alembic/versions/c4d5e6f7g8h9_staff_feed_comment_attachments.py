"""Staff feed: attachments on comments.

Revision ID: c4d5e6f7g8h9
Revises: x9y0z1a2b3
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7g8h9"
down_revision: Union[str, Sequence[str], None] = "x9y0z1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_feed_comment_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("comment_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["comment_id"], ["staff_feed_comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_staff_feed_comment_attachments_comment_id",
        "staff_feed_comment_attachments",
        ["comment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_staff_feed_comment_attachments_comment_id",
        table_name="staff_feed_comment_attachments",
    )
    op.drop_table("staff_feed_comment_attachments")
