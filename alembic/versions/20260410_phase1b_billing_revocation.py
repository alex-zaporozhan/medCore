"""Phase 1b ADR-012: billing revocation timestamp on platform signup intents.

Revision ID: 20260410_phase1b_billing_revocation
Revises: 20260408_phase1b_provision_retry_catalog
Create Date: 2026-04-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260410_phase1b_billing_revocation"
down_revision: Union[str, Sequence[str], None] = "20260408_phase1b_provision_retry_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_signup_intents",
        sa.Column("billing_revoked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_signup_intents", "billing_revoked_at")
