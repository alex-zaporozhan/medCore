"""Add discounts table, clinic notification policy, patient notification settings.

Revision ID: e7f8a9b0c1d2
Revises: d5e6f7a8b9c0
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("discount_type", sa.String(32), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("percent_off", sa.Numeric(5, 2), nullable=True),
        sa.Column("amount_off", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_discounts_clinic_active", "discounts", ["clinic_id", "is_active"], unique=False)
    op.create_index("idx_discounts_valid", "discounts", ["valid_from", "valid_until"], unique=False)

    op.add_column(
        "clinics",
        sa.Column("allow_patient_disable_discount_notifications", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "clinics",
        sa.Column("allow_patient_disable_reminders", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "clinics",
        sa.Column("allow_patient_disable_all_notifications", sa.Boolean(), nullable=False, server_default="true"),
    )

    op.add_column(
        "patients",
        sa.Column("disable_discount_notifications", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "patients",
        sa.Column("disable_reminders", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "patients",
        sa.Column("disable_all_notifications", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("patients", "disable_all_notifications")
    op.drop_column("patients", "disable_reminders")
    op.drop_column("patients", "disable_discount_notifications")
    op.drop_column("clinics", "allow_patient_disable_all_notifications")
    op.drop_column("clinics", "allow_patient_disable_reminders")
    op.drop_column("clinics", "allow_patient_disable_discount_notifications")
    op.drop_index("idx_discounts_valid", "discounts")
    op.drop_index("idx_discounts_clinic_active", "discounts")
    op.drop_table("discounts")
