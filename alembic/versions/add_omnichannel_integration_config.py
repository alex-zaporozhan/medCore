"""Add omni_integration_configs table for omnichannel assistant.

Revision ID: z1a2b3c4d5e7
Revises: z1a2b3c4d5e6
Create Date: 2026-03-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "z1a2b3c4d5e7"
down_revision: Union[str, Sequence[str], None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "omni_integration_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "business_account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_omni_integration_configs_business",
        "omni_integration_configs",
        ["business_account_id"],
        unique=False,
    )
    op.create_index(
        "idx_omni_integration_configs_channel",
        "omni_integration_configs",
        ["channel_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "ux_omni_integration_channel",
        "omni_integration_configs",
        ["business_account_id", "channel_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "ux_omni_integration_channel",
        "omni_integration_configs",
        type_="unique",
    )
    op.drop_index(
        "idx_omni_integration_configs_channel",
        table_name="omni_integration_configs",
    )
    op.drop_index(
        "idx_omni_integration_configs_business",
        table_name="omni_integration_configs",
    )
    op.drop_table("omni_integration_configs")

