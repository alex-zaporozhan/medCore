"""Regression tests: payment authz boundary."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from src.core.datetime_utils import utc_now
from src.domain.entities.booking import Booking
from src.domain.entities.patient import Patient
from src.infrastructure.database.base import AsyncSessionLocal


async def _create_confirmed_booking(seed_data: dict, patient_id):
    """Create confirmed booking in test DB for reminder scenarios."""
    async with AsyncSessionLocal() as session:
        booking = Booking(
            id=uuid4(),
            clinic_id=seed_data["clinic_id"],
            patient_id=patient_id,
            doctor_id=seed_data["doctor_id"],
            service_id=seed_data["service_id"],
            appointment_date=(utc_now() + timedelta(hours=24)).date(),
            appointment_time=(utc_now() + timedelta(hours=24)).time().replace(microsecond=0),
            status="confirmed",
            prepayment_amount=0,
        )
        session.add(booking)
        await session.commit()
        return booking.id


async def _create_foreign_patient_in_same_clinic(seed_data: dict):
    async with AsyncSessionLocal() as session:
        patient = Patient(
            id=uuid4(),
            clinic_id=seed_data["clinic_id"],
            phone="+7999" + str(uuid4().int)[:7],
            full_name="Foreign Patient",
        )
        session.add(patient)
        await session.commit()
        return patient.id


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_create_payment_requires_patient_subject(
    client,
    seed_data: dict,
):
    """POST /api/v1/payments must reject unauthenticated/system subject."""
    response = await client.post(
        "/api/v1/payments",
        json={"booking_id": str(uuid4())},
    )
    assert response.status_code == 403, response.text
    body = response.json()
    assert body.get("detail", {}).get("code") == "FORBIDDEN"


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_create_payment_rejects_foreign_patient_booking(
    client,
    seed_data: dict,
    patient_auth: dict,
):
    """Patient cannot create payment for another patient's booking."""
    foreign_patient_id = await _create_foreign_patient_in_same_clinic(seed_data)
    booking_id = await _create_confirmed_booking(seed_data, foreign_patient_id)
    headers = {"Authorization": f"Bearer {patient_auth['access_token']}"}

    response = await client.post(
        "/api/v1/payments",
        headers=headers,
        json={"booking_id": str(booking_id)},
    )
    assert response.status_code == 404, response.text
    body = response.json()
    assert body.get("detail", {}).get("code") == "PAYMENT_BOOKING_NOT_FOUND"

    async with AsyncSessionLocal() as session:
        row = await session.execute(select(Booking).where(Booking.id == booking_id))
        booking = row.scalar_one_or_none()
        assert booking is not None
        assert booking.patient_id == foreign_patient_id

