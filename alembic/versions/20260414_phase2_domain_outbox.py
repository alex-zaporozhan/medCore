"""Phase 2: domain_outbox for ADR-009 (PaymentSuccess path, contour A webhook).

Revision ID: 20260414_phase2_domain_outbox
Revises: 20260413_phase1e_embed_inbound_idempotency
Create Date: 2026-04-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260414_phase2_domain_outbox"
down_revision: Union[str, Sequence[str], None] = "20260413_phase1e_embed_inbound_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domain_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dedup_key", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key", name="ux_domain_outbox_dedup_key"),
    )
    op.create_index("ix_domain_outbox_aggregate_type", "domain_outbox", ["aggregate_type"], unique=False)
    op.create_index("ix_domain_outbox_aggregate_id", "domain_outbox", ["aggregate_id"], unique=False)
    op.create_index("ix_domain_outbox_event_type", "domain_outbox", ["event_type"], unique=False)
    op.create_index(
        "ix_domain_outbox_unpublished_created",
        "domain_outbox",
        ["published_at", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_domain_outbox_unpublished_created", table_name="domain_outbox")
    op.drop_index("ix_domain_outbox_event_type", table_name="domain_outbox")
    op.drop_index("ix_domain_outbox_aggregate_id", table_name="domain_outbox")
    op.drop_index("ix_domain_outbox_aggregate_type", table_name="domain_outbox")
    op.drop_table("domain_outbox")
