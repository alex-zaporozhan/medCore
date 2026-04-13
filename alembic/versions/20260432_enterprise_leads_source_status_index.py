"""Composite index on enterprise_leads (lead_source, status) for admin filters.

Revision ID: 20260432_enterprise_leads_source_status_idx
Revises: 20260431_slot_release_outcomes
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260432_enterprise_leads_source_status_idx"
down_revision: Union[str, Sequence[str], None] = "20260431_slot_release_outcomes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_enterprise_leads_lead_source_status",
        "enterprise_leads",
        ["lead_source", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_enterprise_leads_lead_source_status",
        table_name="enterprise_leads",
    )
