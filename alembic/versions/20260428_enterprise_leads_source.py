"""Enterprise leads: источник заявки (корпоратив / демо).

Revision ID: 20260428_enterprise_leads_source
Revises: 20260427_enterprise_leads
Create Date: 2026-04-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260428_enterprise_leads_source"
down_revision: Union[str, Sequence[str], None] = "20260427_enterprise_leads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "enterprise_leads",
        sa.Column("lead_source", sa.String(length=32), server_default="corporate", nullable=False),
    )
    op.add_column(
        "enterprise_leads",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("enterprise_leads", "updated_at")
    op.drop_column("enterprise_leads", "lead_source")
