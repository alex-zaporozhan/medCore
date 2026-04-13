"""Extend partial unique slot predicate: no_show + completed release slot (P1-1 backlog).

Revision ID: 20260431_slot_release_outcomes
Revises: 20260430_slot_partial_uq

Must match ``BOOKING_STATUSES_RELEASE_DOCTOR_SLOT`` in ``src/domain/booking_slot_policy.py``.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260431_slot_release_outcomes"
down_revision = "20260430_slot_partial_uq"
branch_labels = None
depends_on = None

# Keep in sync with ``booking_slot_policy.partial_unique_index_status_predicate_sql()``.
_SLOT_ACTIVE_PREDICATE = (
    "deleted_at IS NULL AND status NOT IN ("
    "'canceled_by_clinic', 'canceled_by_patient', 'cancelled', "
    "'completed', 'no_show'"
    ")"
)


def upgrade() -> None:
    op.drop_index("ux_bookings_doctor_slot_active", table_name="bookings")
    op.create_index(
        "ux_bookings_doctor_slot_active",
        "bookings",
        ["doctor_id", "appointment_date", "appointment_time"],
        unique=True,
        postgresql_where=sa.text(_SLOT_ACTIVE_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index("ux_bookings_doctor_slot_active", table_name="bookings")
    op.create_index(
        "ux_bookings_doctor_slot_active",
        "bookings",
        ["doctor_id", "appointment_date", "appointment_time"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND status NOT IN ("
            "'canceled_by_clinic', 'canceled_by_patient', 'cancelled'"
            ")"
        ),
    )
