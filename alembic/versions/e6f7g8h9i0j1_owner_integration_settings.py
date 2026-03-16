"""Add owner_integration_settings table (B5.6 optional UI).

Revision ID: e6f7g8h9i0j1
Revises: d5e6f7g8h9i0_package_family_links
Create Date: 2026-03-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e6f7g8h9i0j1_owner_integration_settings"
down_revision: Union[str, Sequence[str], None] = "d5e6f7g8h9i0_package_family_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "owner_integration_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_morning_brief_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("owner_telegram_chat_id", sa.String(length=128), nullable=True),
        sa.Column("morning_brief_send_at_utc", sa.String(length=8), nullable=True),
        sa.Column("ai_supervisor_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("ai_supervisor_send_at_utc", sa.String(length=8), nullable=True),
        sa.Column("ai_supervisor_recipient_chat_ids", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", name="uq_owner_integration_settings_clinic_id"),
    )
    op.create_index(
        op.f("ix_owner_integration_settings_clinic_id"),
        "owner_integration_settings",
        ["clinic_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_owner_integration_settings_clinic_id"),
        table_name="owner_integration_settings",
    )
    op.drop_table("owner_integration_settings")
