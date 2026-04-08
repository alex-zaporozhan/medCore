"""Phase 1e: embed webhook inbox idempotency receipts (§24.2 replay guard).

Revision ID: 20260413_phase1e_embed_inbound_idempotency
Revises: 20260412_phase1e_embed_catalog_and_keys
Create Date: 2026-04-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260413_phase1e_embed_inbound_idempotency"
down_revision: Union[str, Sequence[str], None] = "20260412_phase1e_embed_catalog_and_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_embed_inbound_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("body_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="ux_organization_embed_inbound_org_idem",
        ),
    )


def downgrade() -> None:
    op.drop_table("organization_embed_inbound_receipts")
