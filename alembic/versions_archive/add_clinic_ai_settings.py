"""Add clinic_ai_settings table for AI configuration per clinic.

Revision ID: y1z2a3b4c5d6
Revises: w3x4y5z6a7b8
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "y1z2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "w3x4y5z6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinic_ai_settings",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", sa.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ai_mode", sa.String(32), nullable=False, server_default="draft_only"),
        sa.Column("ai_business_prompt", sa.Text(), nullable=True),
        sa.Column("ai_allowed_intents", sa.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("ai_autoreply_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ai_autoreply_hours", sa.JSON(), nullable=True),
        sa.Column("ai_provider_type", sa.String(32), nullable=False, server_default="external"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint(
        "ux_clinic_ai_settings_clinic_id",
        "clinic_ai_settings",
        ["clinic_id"],
    )


def downgrade() -> None:
    op.drop_constraint("ux_clinic_ai_settings_clinic_id", "clinic_ai_settings", type_="unique")
    op.drop_table("clinic_ai_settings")

