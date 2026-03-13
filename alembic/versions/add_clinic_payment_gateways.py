"""Add clinic_payment_gateways table for storing encrypted payment gateway credentials.

Revision ID: b2c3d4e5f6g7_clinic_gateways
Revises: a1b2c3d4e5f6_omni_names
Create Date: 2026-03-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b2c3d4e5f6g7_clinic_gateways"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6_omni_names"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinic_payment_gateways",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gateway", sa.String(32), nullable=False),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "clinic_id",
            "gateway",
            name="uq_clinic_payment_gateway",
        ),
    )
    op.create_index(
        "ix_clinic_payment_gateways_clinic_id",
        "clinic_payment_gateways",
        ["clinic_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_clinic_payment_gateways_clinic_id",
        table_name="clinic_payment_gateways",
    )
    op.drop_table("clinic_payment_gateways")

