"""Omni lead logs: immutable transcript snapshots.

Revision ID: b8c9d0e1f2a3
Revises: a2b3c4d5e6f7
Create Date: 2026-04-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "omni_lead_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("omni_chat_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("omni_chats.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("omni_contacts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("opened_by_admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True),
        sa.Column("opened_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="Обращение"),
        sa.Column("outcome", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
        sa.Column("transcript_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("transcript_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lead_cards.id", ondelete="SET NULL"), nullable=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("omni_chat_id", name="uq_omni_lead_logs_omni_chat_id"),
    )
    op.create_index("ix_omni_lead_logs_clinic_id", "omni_lead_logs", ["clinic_id"])
    op.create_index("ix_omni_lead_logs_omni_chat_id", "omni_lead_logs", ["omni_chat_id"])
    op.create_index("ix_omni_lead_logs_contact_id", "omni_lead_logs", ["contact_id"])
    op.create_index("ix_omni_lead_logs_opened_by_admin_id", "omni_lead_logs", ["opened_by_admin_id"])
    op.create_index("ix_omni_lead_logs_closed_at", "omni_lead_logs", ["closed_at"])
    op.create_index("ix_omni_lead_logs_outcome", "omni_lead_logs", ["outcome"])
    op.create_index("ix_omni_lead_logs_lead_id", "omni_lead_logs", ["lead_id"])
    op.create_index("ix_omni_lead_logs_booking_id", "omni_lead_logs", ["booking_id"])
    op.create_index("ix_omni_lead_logs_patient_id", "omni_lead_logs", ["patient_id"])
    op.create_index("idx_omni_lead_logs_clinic_closed_at", "omni_lead_logs", ["clinic_id", "closed_at"])
    op.create_index("idx_omni_lead_logs_clinic_outcome_closed_at", "omni_lead_logs", ["clinic_id", "outcome", "closed_at"])
    op.create_index("idx_omni_lead_logs_clinic_contact_closed_at", "omni_lead_logs", ["clinic_id", "contact_id", "closed_at"])


def downgrade() -> None:
    op.drop_index("idx_omni_lead_logs_clinic_contact_closed_at", table_name="omni_lead_logs")
    op.drop_index("idx_omni_lead_logs_clinic_outcome_closed_at", table_name="omni_lead_logs")
    op.drop_index("idx_omni_lead_logs_clinic_closed_at", table_name="omni_lead_logs")
    op.drop_index("ix_omni_lead_logs_patient_id", table_name="omni_lead_logs")
    op.drop_index("ix_omni_lead_logs_booking_id", table_name="omni_lead_logs")
    op.drop_index("ix_omni_lead_logs_lead_id", table_name="omni_lead_logs")
    op.drop_index("ix_omni_lead_logs_outcome", table_name="omni_lead_logs")
    op.drop_index("ix_omni_lead_logs_closed_at", table_name="omni_lead_logs")
    op.drop_index("ix_omni_lead_logs_opened_by_admin_id", table_name="omni_lead_logs")
    op.drop_index("ix_omni_lead_logs_contact_id", table_name="omni_lead_logs")
    op.drop_index("ix_omni_lead_logs_omni_chat_id", table_name="omni_lead_logs")
    op.drop_index("ix_omni_lead_logs_clinic_id", table_name="omni_lead_logs")
    op.drop_table("omni_lead_logs")

