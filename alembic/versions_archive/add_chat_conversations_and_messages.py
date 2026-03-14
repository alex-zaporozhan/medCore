"""Add conversations and chat_messages tables.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_message_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_message_sender_type", sa.String(16), nullable=True),
        sa.Column("unread_by_admin_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unread_by_patient_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "patient_id", name="ux_conversations_clinic_patient"),
    )
    op.create_index("idx_conversations_clinic_patient", "conversations", ["clinic_id", "patient_id"], unique=False)
    op.create_index("idx_conversations_clinic_last_message", "conversations", ["clinic_id", "last_message_at"], unique=False)
    op.create_index("idx_conversations_assigned_admin", "conversations", ["assigned_admin_id", "last_message_at"], unique=False)
    op.create_index("idx_conversations_clinic_unread_admin", "conversations", ["clinic_id", "unread_by_admin_count"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sender_type", sa.String(16), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_by_admin_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("read_by_patient_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_chat_messages_conversation_created_at", "chat_messages", ["conversation_id", "created_at"], unique=False)
    op.create_index("idx_chat_messages_clinic_created_at", "chat_messages", ["clinic_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_chat_messages_clinic_created_at", table_name="chat_messages")
    op.drop_index("idx_chat_messages_conversation_created_at", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("idx_conversations_clinic_unread_admin", table_name="conversations")
    op.drop_index("idx_conversations_assigned_admin", table_name="conversations")
    op.drop_index("idx_conversations_clinic_last_message", table_name="conversations")
    op.drop_index("idx_conversations_clinic_patient", table_name="conversations")
    op.drop_table("conversations")
