"""Add follow-up fields to chat_messages for attention feed.

Revision ID: x1y2z3a4b5c7
Revises: w3x4y5z6a7b8
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x1y2z3a4b5c7"
down_revision: Union[str, Sequence[str], None] = "w3x4y5z6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("follow_up_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("follow_up_closed", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "chat_messages",
        sa.Column("follow_up_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "follow_up_reason")
    op.drop_column("chat_messages", "follow_up_closed")
    op.drop_column("chat_messages", "follow_up_at")

