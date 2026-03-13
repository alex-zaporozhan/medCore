"""Add clinic_plans table (plan/feature_flags per clinic).

Does NOT alter clinics table — avoids 500 for DBs without new columns.
Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-02-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinic_plans",
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False, server_default="basic"),
        sa.Column("feature_flags", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("clinic_id"),
    )
    # Backfill: one row per existing clinic
    op.execute(sa.text("""
        INSERT INTO clinic_plans (clinic_id, plan)
        SELECT id, 'basic' FROM clinics
    """))


def downgrade() -> None:
    op.drop_table("clinic_plans")
