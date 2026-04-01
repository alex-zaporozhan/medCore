"""Lead-log routing rules (per clinic).

Revision ID: 20260401_lead_log_routing_rules
Revises: e2f3a4b5c6d7
Create Date: 2026-04-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260401_lead_log_routing_rules"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lead_log_routing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "clinic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel_type", sa.String(length=64), nullable=True),
        sa.Column("source_key", sa.String(length=128), nullable=True),
        sa.Column(
            "target_stream_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("task_streams.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lead_log_routing_rules_clinic_id", "lead_log_routing_rules", ["clinic_id"])
    op.create_index("ix_lead_log_routing_rules_target_stream_id", "lead_log_routing_rules", ["target_stream_id"])
    op.create_index(
        "idx_lead_log_routing_rules_clinic_active_sort",
        "lead_log_routing_rules",
        ["clinic_id", "is_active", "sort_order"],
    )
    op.create_index(
        "idx_lead_log_routing_rules_match",
        "lead_log_routing_rules",
        ["clinic_id", "channel_type", "source_key"],
    )


def downgrade() -> None:
    op.drop_index("idx_lead_log_routing_rules_match", table_name="lead_log_routing_rules")
    op.drop_index("idx_lead_log_routing_rules_clinic_active_sort", table_name="lead_log_routing_rules")
    op.drop_index("ix_lead_log_routing_rules_target_stream_id", table_name="lead_log_routing_rules")
    op.drop_index("ix_lead_log_routing_rules_clinic_id", table_name="lead_log_routing_rules")
    op.drop_table("lead_log_routing_rules")

