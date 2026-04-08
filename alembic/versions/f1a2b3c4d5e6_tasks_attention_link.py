"""Add attention link fields to tasks for Tasks&Attention model.

Revision ID: f1a2b3c4d5e6
Revises: 2ac77a14a1f8_erp_loyalty_obligations
Create Date: 2026-03-17 18:05:00.000000

This migration adds optional link fields from tasks to owner's attention feed
items. Instead of a separate AttentionTaskLink table we follow the alternative
design (tasks ↔ attention feed) and store:

- attention_kind: logical kind of attention item (follow_up|retention_gap|conflict)
- attention_ref_id: UUID of the underlying source entity (chat message, booking, patient, etc.)

Multiple tasks can reference the same (attention_kind, attention_ref_id)
pair, which allows modelling 1:N relations between a signal and tasks.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "2ac77a14a1f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add attention link columns to tasks."""
    op.add_column(
        "tasks",
        sa.Column("attention_kind", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("attention_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "idx_tasks_clinic_attention_ref",
        "tasks",
        ["clinic_id", "attention_kind", "attention_ref_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop attention link columns from tasks."""
    op.drop_index("idx_tasks_clinic_attention_ref", table_name="tasks")
    op.drop_column("tasks", "attention_ref_id")
    op.drop_column("tasks", "attention_kind")

