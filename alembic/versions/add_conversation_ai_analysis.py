"""Add conversation_ai_analysis table for AI conflict analysis.

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f6
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b1c2d3e4f5g6"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_ai_analysis",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", sa.UUID(as_uuid=True), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("conversation_id", sa.UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("analysis_date", sa.Date(), nullable=False),
        sa.Column("sentiment", sa.String(16), nullable=False),
        sa.Column("issue_category", sa.String(32), nullable=False),
        sa.Column("is_conflict", sa.Boolean(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False),
        sa.Column("admin_mistakes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("business_root_causes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("suggested_playbook", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("raw_ai_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "idx_conv_ai_analysis_clinic_date",
        "conversation_ai_analysis",
        ["clinic_id", "analysis_date"],
    )
    op.create_index(
        "idx_conv_ai_analysis_conv",
        "conversation_ai_analysis",
        ["conversation_id"],
    )
    op.create_index(
        "idx_conv_ai_analysis_conflict",
        "conversation_ai_analysis",
        ["clinic_id", "is_conflict", "is_resolved"],
    )


def downgrade() -> None:
    op.drop_index("idx_conv_ai_analysis_conflict", table_name="conversation_ai_analysis")
    op.drop_index("idx_conv_ai_analysis_conv", table_name="conversation_ai_analysis")
    op.drop_index("idx_conv_ai_analysis_clinic_date", table_name="conversation_ai_analysis")
    op.drop_table("conversation_ai_analysis")

