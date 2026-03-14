"""Add message_type and sticker_key to chat_messages (Premium stickers).

Revision ID: d5e6f7a8b9c0
Revises: f7a8b9c0d1e2
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("message_type", sa.String(16), nullable=False, server_default="text"),
    )
    op.add_column(
        "chat_messages",
        sa.Column("sticker_key", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "sticker_key")
    op.drop_column("chat_messages", "message_type")
