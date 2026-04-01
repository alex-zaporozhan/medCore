"""Omni chat leases for presence/automation.

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-04-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "omni_chat_leases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chat_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("omni_chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admins.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tab_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_omni_chat_leases_clinic_id", "omni_chat_leases", ["clinic_id"])
    op.create_index("ix_omni_chat_leases_chat_id", "omni_chat_leases", ["chat_id"])
    op.create_index("ix_omni_chat_leases_admin_id", "omni_chat_leases", ["admin_id"])
    op.create_index("ix_omni_chat_leases_expires_at", "omni_chat_leases", ["expires_at"])
    op.create_index("idx_omni_chat_leases_clinic_chat_expires", "omni_chat_leases", ["clinic_id", "chat_id", "expires_at"])
    op.create_index("idx_omni_chat_leases_clinic_admin_expires", "omni_chat_leases", ["clinic_id", "admin_id", "expires_at"])
    op.create_index("idx_omni_chat_leases_chat_tab", "omni_chat_leases", ["chat_id", "tab_id"])


def downgrade() -> None:
    op.drop_index("idx_omni_chat_leases_chat_tab", table_name="omni_chat_leases")
    op.drop_index("idx_omni_chat_leases_clinic_admin_expires", table_name="omni_chat_leases")
    op.drop_index("idx_omni_chat_leases_clinic_chat_expires", table_name="omni_chat_leases")
    op.drop_index("ix_omni_chat_leases_expires_at", table_name="omni_chat_leases")
    op.drop_index("ix_omni_chat_leases_admin_id", table_name="omni_chat_leases")
    op.drop_index("ix_omni_chat_leases_chat_id", table_name="omni_chat_leases")
    op.drop_index("ix_omni_chat_leases_clinic_id", table_name="omni_chat_leases")
    op.drop_table("omni_chat_leases")

