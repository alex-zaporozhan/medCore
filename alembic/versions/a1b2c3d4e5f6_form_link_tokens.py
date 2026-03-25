"""Add form_link_tokens table for send-link (one-time form fill URL).

Revision ID: a1b2c3d4e5f6_form_link_tokens
Revises: expand_alembic_ver_64
Create Date: 2026-03-15

Note: ERP finance/inventory tables live in schema_v2_initial; the former c3d4 revision was redundant and removed from the chain.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6_form_link_tokens"
down_revision: Union[str, Sequence[str], None] = "expand_alembic_ver_64"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "form_link_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["digital_form_templates.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
    )
    op.create_index("ix_form_link_tokens_token", "form_link_tokens", ["token"], unique=True)
    op.create_index("ix_form_link_tokens_clinic_id", "form_link_tokens", ["clinic_id"], unique=False)
    op.create_index("idx_form_link_tokens_expires", "form_link_tokens", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_form_link_tokens_expires", table_name="form_link_tokens")
    op.drop_index("ix_form_link_tokens_clinic_id", table_name="form_link_tokens")
    op.drop_index("ix_form_link_tokens_token", table_name="form_link_tokens")
    op.drop_table("form_link_tokens")
