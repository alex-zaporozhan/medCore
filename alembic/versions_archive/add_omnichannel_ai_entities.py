"""Add omnichannel AI assistant core tables.

Revision ID: z1a2b3c4d5e6
Revises: y1z2a3b4c5d6
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "z1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "y1z2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # omni_contacts
    op.create_table(
        "omni_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "business_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("primary_phone", sa.String(length=32), nullable=True),
        sa.Column(
            "emails",
            postgresql.ARRAY(sa.String(length=255)),
            nullable=True,
        ),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("external_ids", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(length=64)),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_omni_contacts_business_account_phone",
        "omni_contacts",
        ["business_account_id", "primary_phone"],
        unique=False,
    )

    # omni_channels
    op.create_table(
        "omni_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "business_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="PENDING_SETUP",
        ),
        sa.Column("settings_ref", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_omni_channels_business_type",
        "omni_channels",
        ["business_account_id", "type"],
        unique=False,
    )

    # omni_chats
    op.create_table(
        "omni_chats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "business_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("omni_contacts.id"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("omni_channels.id"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column(
            "ai_mode",
            sa.String(length=32),
            nullable=False,
            server_default="DISABLED",
        ),
        sa.Column("last_message_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_actor_type", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_omni_chats_business_contact_open",
        "omni_chats",
        ["business_account_id", "contact_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_omni_chats_business_last_message",
        "omni_chats",
        ["business_account_id", "last_message_at"],
        unique=False,
    )

    # omni_messages
    op.create_table(
        "omni_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "chat_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("omni_chats.id"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("omni_contacts.id"),
            nullable=True,
        ),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("omni_channels.id"),
            nullable=True,
        ),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column(
            "content_type",
            sa.String(length=32),
            nullable=False,
            server_default="TEXT",
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_metadata", postgresql.JSONB, nullable=True),
        sa.Column("ui_hidden", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("hidden_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_omni_messages_chat_created_at",
        "omni_messages",
        ["chat_id", "created_at"],
        unique=False,
    )

    # omni_ai_settings
    op.create_table(
        "omni_ai_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "ai_mode",
            sa.String(length=32),
            nullable=False,
            server_default="DISABLED",
        ),
        sa.Column("working_hours_policy", sa.JSON(), nullable=True),
        sa.Column("confidence_thresholds", sa.JSON(), nullable=True),
        sa.Column("prompt_profile_id", sa.String(length=64), nullable=True),
        sa.Column("kb_profile_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_omni_ai_settings_scope",
        "omni_ai_settings",
        ["scope", "scope_id"],
        unique=True,
    )

    # omni_audit_logs
    op.create_table(
        "omni_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "business_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id"),
            nullable=False,
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_omni_audit_logs_business_created_at",
        "omni_audit_logs",
        ["business_account_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_omni_audit_logs_target",
        "omni_audit_logs",
        ["target_type", "target_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_omni_audit_logs_target",
        table_name="omni_audit_logs",
    )
    op.drop_index(
        "idx_omni_audit_logs_business_created_at",
        table_name="omni_audit_logs",
    )
    op.drop_table("omni_audit_logs")

    op.drop_index(
        "ux_omni_ai_settings_scope",
        table_name="omni_ai_settings",
    )
    op.drop_table("omni_ai_settings")

    op.drop_index(
        "idx_omni_messages_chat_created_at",
        table_name="omni_messages",
    )
    op.drop_table("omni_messages")

    op.drop_index(
        "idx_omni_chats_business_last_message",
        table_name="omni_chats",
    )
    op.drop_index(
        "idx_omni_chats_business_contact_open",
        table_name="omni_chats",
    )
    op.drop_table("omni_chats")

    op.drop_index(
        "idx_omni_channels_business_type",
        table_name="omni_channels",
    )
    op.drop_table("omni_channels")

    op.drop_index(
        "idx_omni_contacts_business_account_phone",
        table_name="omni_contacts",
    )
    op.drop_table("omni_contacts")

