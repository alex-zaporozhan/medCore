"""Partial unique index for active doctor slot (P0-1 / BACKEND_AUDIT 2026-04-11).

Revision ID: 20260430_slot_partial_uq
Revises: 20260429_storefront

Replaces global UNIQUE (doctor_id, date, time) with a partial unique index so
cancelled / canceled_by_* rows no longer block a new booking on the same slot.

Predicate must stay in sync with ``src.domain.booking_slot_policy``.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260430_slot_partial_uq"
down_revision = "20260429_storefront"
branch_labels = None
depends_on = None

# Keep in sync with ``booking_slot_policy.partial_unique_index_status_predicate_sql()``.
_SLOT_ACTIVE_PREDICATE = (
    "deleted_at IS NULL AND status NOT IN ("
    "'canceled_by_clinic', 'canceled_by_patient', 'cancelled'"
    ")"
)


def upgrade() -> None:
    op.drop_constraint("ux_bookings_doctor_slot", "bookings", type_="unique")
    op.create_index(
        "ux_bookings_doctor_slot_active",
        "bookings",
        ["doctor_id", "appointment_date", "appointment_time"],
        unique=True,
        postgresql_where=sa.text(_SLOT_ACTIVE_PREDICATE),
    )


def downgrade() -> None:
    # Recreating the global unique may fail if cancelled rows share a slot with an active row.
    op.drop_index("ux_bookings_doctor_slot_active", table_name="bookings")
    op.create_unique_constraint(
        "ux_bookings_doctor_slot",
        "bookings",
        ["doctor_id", "appointment_date", "appointment_time"],
    )
