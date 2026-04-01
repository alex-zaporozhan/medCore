"""Omni messages: add composite index for (chat_id, channel_id).

Revision ID: u9v0w1x2y3
Revises: s6t7u8v9w0
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "u9v0w1x2y3"
down_revision: Union[str, Sequence[str], None] = "s6t7u8v9w0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_omni_messages_chat_channel",
        "omni_messages",
        ["chat_id", "channel_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_omni_messages_chat_channel", table_name="omni_messages")

