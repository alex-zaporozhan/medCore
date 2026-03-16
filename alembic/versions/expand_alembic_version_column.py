"""Expand alembic_version.version_num to VARCHAR(128) for long revision IDs.

Revision ID: expand_alembic_ver_64
Revises: b2c3d4e5f6g7_clinic_gateways
Create Date: 2026-03-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "expand_alembic_ver_64"
down_revision: Union[str, Sequence[str], None] = "schema_v2_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(32),
        type_=sa.String(128),
    )


def downgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(128),
        type_=sa.String(32),
    )
