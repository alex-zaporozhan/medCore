"""Omni chat: closure outcome + SLA timestamps.

Revision ID: a2b3c4d5e6f7
Revises: v9w8x7y6z5m4
Create Date: 2026-04-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "v9w8x7y6z5m4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("omni_chats", sa.Column("claimed_at", sa.DateTime(), nullable=True))
    op.add_column("omni_chats", sa.Column("closed_at", sa.DateTime(), nullable=True))
    op.create_index("ix_omni_chats_claimed_at", "omni_chats", ["claimed_at"], unique=False)
    op.create_index("ix_omni_chats_closed_at", "omni_chats", ["closed_at"], unique=False)

    op.create_table(
        "omni_chat_closure_tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "title", name="ux_omni_chat_closure_tags_clinic_title"),
    )
    op.create_index(
        "ix_omni_chat_closure_tags_clinic_id",
        "omni_chat_closure_tags",
        ["clinic_id"],
        unique=False,
    )

    op.create_table(
        "omni_chat_closures",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chat_id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("closed_by_admin_id", sa.UUID(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["chat_id"], ["omni_chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["closed_by_admin_id"], ["admins.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", name="ux_omni_chat_closures_chat_id"),
    )
    op.create_index("ix_omni_chat_closures_clinic_id", "omni_chat_closures", ["clinic_id"], unique=False)
    op.create_index("ix_omni_chat_closures_outcome", "omni_chat_closures", ["outcome"], unique=False)

    op.create_table(
        "omni_chat_closure_tag_links",
        sa.Column("closure_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["closure_id"], ["omni_chat_closures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["omni_chat_closure_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("closure_id", "tag_id"),
    )
    op.create_index(
        "ix_omni_chat_closure_tag_links_tag_id",
        "omni_chat_closure_tag_links",
        ["tag_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_omni_chat_closure_tag_links_tag_id", table_name="omni_chat_closure_tag_links")
    op.drop_table("omni_chat_closure_tag_links")

    op.drop_index("ix_omni_chat_closures_outcome", table_name="omni_chat_closures")
    op.drop_index("ix_omni_chat_closures_clinic_id", table_name="omni_chat_closures")
    op.drop_table("omni_chat_closures")

    op.drop_index("ix_omni_chat_closure_tags_clinic_id", table_name="omni_chat_closure_tags")
    op.drop_table("omni_chat_closure_tags")

    op.drop_index("ix_omni_chats_closed_at", table_name="omni_chats")
    op.drop_index("ix_omni_chats_claimed_at", table_name="omni_chats")
    op.drop_column("omni_chats", "closed_at")
    op.drop_column("omni_chats", "claimed_at")

