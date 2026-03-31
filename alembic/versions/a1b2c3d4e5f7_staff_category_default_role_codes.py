"""Staff profession categories: default_role_codes JSONB template.

Revision ID: a1b2c3d4e5f7
Revises: p0q1r2s3t4u5
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "p0q1r2s3t4u5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "staff_profession_categories",
        sa.Column(
            "default_role_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[\"admin\"]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("staff_profession_categories", "default_role_codes")
