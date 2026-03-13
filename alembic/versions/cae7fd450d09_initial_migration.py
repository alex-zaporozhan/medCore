"""Initial migration

Revision ID: cae7fd450d09
Revises:
Create Date: 2026-02-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "cae7fd450d09"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "clinics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("workday_start", sa.Time(), nullable=False, server_default="09:00:00"),
        sa.Column("workday_end", sa.Time(), nullable=False, server_default="21:00:00"),
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("prepayment_amount", sa.Numeric(10, 2), nullable=False, server_default="500.00"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_clinics_deleted_at", "clinics", ["deleted_at"], unique=False)

    op.create_table(
        "doctors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("specialization", sa.String(255), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("rating", sa.Numeric(2, 1), nullable=False, server_default="0.0"),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_doctors_clinic_id", "doctors", ["clinic_id"], unique=False)
    op.create_index("idx_doctors_is_active", "doctors", ["is_active"], unique=False)
    op.create_index("ix_doctors_clinic_id", "doctors", ["clinic_id"], unique=False)
    op.create_index("ix_doctors_is_active", "doctors", ["is_active"], unique=False)

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_services_clinic_id", "services", ["clinic_id"], unique=False)
    op.create_index("idx_services_is_active", "services", ["is_active"], unique=False)
    op.create_index("ix_services_clinic_id", "services", ["clinic_id"], unique=False)
    op.create_index("ix_services_is_active", "services", ["is_active"], unique=False)

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("telegram_chat_id", sa.String(100), nullable=True),
        sa.Column("preferred_channel", sa.String(20), nullable=False, server_default="sms"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "phone", name="ux_patients_clinic_phone"),
    )
    op.create_index("idx_patients_clinic_id", "patients", ["clinic_id"], unique=False)
    op.create_index("ix_patients_clinic_id", "patients", ["clinic_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_patients_clinic_id", table_name="patients")
    op.drop_index("idx_patients_clinic_id", table_name="patients")
    op.drop_table("patients")
    op.drop_index("ix_services_is_active", table_name="services")
    op.drop_index("ix_services_clinic_id", table_name="services")
    op.drop_index("idx_services_is_active", table_name="services")
    op.drop_index("idx_services_clinic_id", table_name="services")
    op.drop_table("services")
    op.drop_index("ix_doctors_is_active", table_name="doctors")
    op.drop_index("ix_doctors_clinic_id", table_name="doctors")
    op.drop_index("idx_doctors_is_active", table_name="doctors")
    op.drop_index("idx_doctors_clinic_id", table_name="doctors")
    op.drop_table("doctors")
    op.drop_index("idx_clinics_deleted_at", table_name="clinics")
    op.drop_table("clinics")
