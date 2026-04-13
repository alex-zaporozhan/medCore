"""Enterprise leads from public marketing (корпоративные заявки).

Revision ID: 20260427_enterprise_leads
Revises: 20260426_public_catalog_business_os_tiers
Create Date: 2026-04-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260427_enterprise_leads"
down_revision: Union[str, Sequence[str], None] = "20260426_public_catalog_business_os_tiers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "enterprise_leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("phone_or_email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="NEW", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_enterprise_leads_status", "enterprise_leads", ["status"], unique=False)
    op.create_index("ix_enterprise_leads_created_at", "enterprise_leads", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_enterprise_leads_created_at", table_name="enterprise_leads")
    op.drop_index("ix_enterprise_leads_status", table_name="enterprise_leads")
    op.drop_table("enterprise_leads")
