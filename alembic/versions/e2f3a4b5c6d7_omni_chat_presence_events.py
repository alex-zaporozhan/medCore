"""Omni chat presence events for idempotency.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-04-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "omni_chat_presence_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chat_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("omni_chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admins.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tab_id", sa.String(length=64), nullable=False),
        sa.Column("client_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_omni_chat_presence_events_clinic_id", "omni_chat_presence_events", ["clinic_id"])
    op.create_index("ix_omni_chat_presence_events_chat_id", "omni_chat_presence_events", ["chat_id"])
    op.create_index("ix_omni_chat_presence_events_admin_id", "omni_chat_presence_events", ["admin_id"])
    op.create_index("uq_omni_chat_presence_events_clinic_event", "omni_chat_presence_events", ["clinic_id", "client_event_id"], unique=True)
    op.create_index("idx_omni_chat_presence_events_clinic_chat", "omni_chat_presence_events", ["clinic_id", "chat_id"])


def downgrade() -> None:
    op.drop_index("idx_omni_chat_presence_events_clinic_chat", table_name="omni_chat_presence_events")
    op.drop_index("uq_omni_chat_presence_events_clinic_event", table_name="omni_chat_presence_events")
    op.drop_index("ix_omni_chat_presence_events_admin_id", table_name="omni_chat_presence_events")
    op.drop_index("ix_omni_chat_presence_events_chat_id", table_name="omni_chat_presence_events")
    op.drop_index("ix_omni_chat_presence_events_clinic_id", table_name="omni_chat_presence_events")
    op.drop_table("omni_chat_presence_events")

