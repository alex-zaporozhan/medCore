"""Shift demo patients' bookings forward by 4 days.

Revision ID: shift_demo_4d
Revises: b2c3d4e5f6g7_clinic_gateways
Create Date: 2026-03-07

Data migration: for patients with phone +70000000001 … +70000000010 (demo),
update their bookings: appointment_date += 4 days only where the target slot
(doctor_id, date+4, time) is free, to avoid ux_bookings_doctor_slot violation.
Run: poetry run alembic upgrade head
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "shift_demo_4d"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6g7_clinic_gateways"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Демо-пациенты: телефоны +70000000001 … +70000000010
DEMO_PHONE_LIKE = "+7000000000%"


def upgrade() -> None:
    conn = op.get_bind()
    # Сдвигаем только те записи, у которых слот (врач, дата+4, время) свободен
    conn.execute(
        text("""
            UPDATE bookings b1
            SET appointment_date = b1.appointment_date + INTERVAL '4 days'
            FROM patients p
            WHERE b1.patient_id = p.id
              AND b1.deleted_at IS NULL
              AND p.phone LIKE :pattern
              AND p.deleted_at IS NULL
              AND NOT EXISTS (
                SELECT 1 FROM bookings b2
                WHERE b2.doctor_id = b1.doctor_id
                  AND b2.appointment_date = b1.appointment_date + INTERVAL '4 days'
                  AND b2.appointment_time = b1.appointment_time
                  AND b2.deleted_at IS NULL
                  AND b2.id != b1.id
              )
        """),
        {"pattern": DEMO_PHONE_LIKE},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("""
            UPDATE bookings b1
            SET appointment_date = b1.appointment_date - INTERVAL '4 days'
            FROM patients p
            WHERE b1.patient_id = p.id
              AND b1.deleted_at IS NULL
              AND p.phone LIKE :pattern
              AND p.deleted_at IS NULL
              AND NOT EXISTS (
                SELECT 1 FROM bookings b2
                WHERE b2.doctor_id = b1.doctor_id
                  AND b2.appointment_date = b1.appointment_date - INTERVAL '4 days'
                  AND b2.appointment_time = b1.appointment_time
                  AND b2.deleted_at IS NULL
                  AND b2.id != b1.id
              )
        """),
        {"pattern": DEMO_PHONE_LIKE},
    )
