"""Add prepayment and waitlist tables.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prepayment_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column("scope_doctor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope_service_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("amount_type", sa.String(16), nullable=False),
        sa.Column("min_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("deadline_hours_before_visit", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["scope_doctor_id"], ["doctors.id"]),
        sa.ForeignKeyConstraint(["scope_service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_prepayment_policies_clinic_id", "prepayment_policies", ["clinic_id"], unique=False)

    op.create_table(
        "prepayment_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="RUB"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("provider_payment_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_prepayment_transactions_booking_id", "prepayment_transactions", ["booking_id"], unique=False)

    op.create_table(
        "waitlist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("speciality", sa.String(100), nullable=True),
        sa.Column("time_preferences_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_waitlist_entries_clinic_id", "waitlist_entries", ["clinic_id"], unique=False)
    op.create_index("idx_waitlist_entries_patient_id", "waitlist_entries", ["patient_id"], unique=False)
    op.create_index("idx_waitlist_entries_doctor_id", "waitlist_entries", ["doctor_id"], unique=False)

    op.create_table(
        "queue_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("broadcast_size", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("response_timeout_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("max_notifications_per_entry", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_queue_policies_clinic_id", "queue_policies", ["clinic_id"], unique=True)

    op.create_table(
        "waitlist_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("waitlist_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_date", sa.Date(), nullable=False),
        sa.Column("slot_time", sa.Time(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["waitlist_entry_id"], ["waitlist_entries.id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_waitlist_notifications_entry_id", "waitlist_notifications", ["waitlist_entry_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_waitlist_notifications_entry_id", table_name="waitlist_notifications")
    op.drop_table("waitlist_notifications")
    op.drop_index("idx_queue_policies_clinic_id", table_name="queue_policies")
    op.drop_table("queue_policies")
    op.drop_index("idx_waitlist_entries_doctor_id", table_name="waitlist_entries")
    op.drop_index("idx_waitlist_entries_patient_id", table_name="waitlist_entries")
    op.drop_index("idx_waitlist_entries_clinic_id", table_name="waitlist_entries")
    op.drop_table("waitlist_entries")
    op.drop_index("idx_prepayment_transactions_booking_id", table_name="prepayment_transactions")
    op.drop_table("prepayment_transactions")
    op.drop_index("idx_prepayment_policies_clinic_id", table_name="prepayment_policies")
    op.drop_table("prepayment_policies")
