"""Add service_doctors table.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "service_doctors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("custom_price", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
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
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "service_id",
            "doctor_id",
            name="ux_service_doctors_service_doctor",
        ),
    )
    op.create_index(
        "idx_service_doctors_service_id",
        "service_doctors",
        ["service_id"],
        unique=False,
    )
    op.create_index(
        "idx_service_doctors_doctor_id",
        "service_doctors",
        ["doctor_id"],
        unique=False,
    )
    op.create_index(
        "idx_service_doctors_is_active",
        "service_doctors",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_service_doctors_is_active", table_name="service_doctors")
    op.drop_index("idx_service_doctors_doctor_id", table_name="service_doctors")
    op.drop_index("idx_service_doctors_service_id", table_name="service_doctors")
    op.drop_table("service_doctors")

