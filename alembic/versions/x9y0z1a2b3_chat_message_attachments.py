"""chat_message_attachments for patient/admin clinic chat uploads.

Revision ID: x9y0z1a2b3
Revises: w3x4y5z6a7
Create Date: 2026-03-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x9y0z1a2b3"
down_revision: Union[str, None] = "w3x4y5z6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_message_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_message_attachments_clinic_id",
        "chat_message_attachments",
        ["clinic_id"],
    )
    op.create_index(
        "ix_chat_message_attachments_message_id",
        "chat_message_attachments",
        ["message_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_message_attachments_message_id", table_name="chat_message_attachments")
    op.drop_index("ix_chat_message_attachments_clinic_id", table_name="chat_message_attachments")
    op.drop_table("chat_message_attachments")
