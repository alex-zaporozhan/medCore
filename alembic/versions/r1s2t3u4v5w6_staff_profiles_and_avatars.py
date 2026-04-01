"""Staff profiles (bio + avatar ref).

Revision ID: r1s2t3u4v5w6
Revises: q8r9s0t1u2v3
Create Date: 2026-03-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "r1s2t3u4v5w6"
down_revision: Union[str, Sequence[str], None] = "q8r9s0t1u2v3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_profiles",
        sa.Column("admin_id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("bio", sa.Text(), server_default="", nullable=False),
        sa.Column("avatar_s3_key", sa.String(length=900), nullable=True),
        sa.Column("avatar_updated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("admin_id"),
        sa.UniqueConstraint("clinic_id", "admin_id", name="ux_staff_profiles_clinic_admin"),
        sa.UniqueConstraint("avatar_s3_key"),
    )
    op.create_index("ix_staff_profiles_clinic_id", "staff_profiles", ["clinic_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_staff_profiles_clinic_id", table_name="staff_profiles")
    op.drop_table("staff_profiles")

