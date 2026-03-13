"""Add client_reference table (single row for editable client reference content).

Revision ID: m3n4o5p6q7r8
Revises: k2l3m4n5o6p7
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "m3n4o5p6q7r8"
down_revision: Union[str, Sequence[str], None] = "k2l3m4n5o6p7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "client_reference",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO client_reference (id, content, updated_at) VALUES (gen_random_uuid(), '', now())"
    )


def downgrade() -> None:
    op.drop_table("client_reference")
