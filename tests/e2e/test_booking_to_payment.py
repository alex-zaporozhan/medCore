"""E2E: booking flow from auth to payment URL."""

import random
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_booking_to_payment_flow(
    client: AsyncClient,
    seed_data: dict,
):
    """
    Full flow: health -> send-code -> verify-code -> doctors -> services ->
    schedule -> create booking -> create payment (mocked) -> assert payment_url.
    """
    phone = "+7900" + "".join(random.choices("0123456789", k=7))
    clinic_id = seed_data["clinic_id"]
    key = f"auth:code:{clinic_id}:{phone}"

    # 1. Health
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

    # 2. Send code -> stores code in Redis (reset pool: ``redis_client`` fixture can bind another loop).
    from src.infrastructure.database.redis_client import close_redis, get_redis

    await close_redis()
    r = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": phone, "clinic_slug": seed_data["clinic_slug"]},
    )
    assert r.status_code == 204
    redis = await get_redis()
    raw_code = await redis.get(key)
    assert raw_code, "send_code must store code in Redis"
    code = raw_code.decode() if isinstance(raw_code, bytes) else raw_code

    # 3. Verify code -> token and patient_id
    r = await client.post(
        "/api/v1/auth/verify-code",
        json={
            "phone": phone,
            "code": code,
            "clinic_slug": seed_data["clinic_slug"],
        },
    )
    assert r.status_code == 200
    data = r.json()
    access_token = data["access_token"]
    patient_id = data["patient_id"]
    assert access_token and patient_id

    headers = {"Authorization": f"Bearer {access_token}"}

    # 4. Doctors (scope to seed clinic — full suite may add other clinics; schedule enforces doctor.clinic_id)
    r = await client.get(
        "/api/v1/doctors",
        headers=headers,
        params={"clinic_id": str(clinic_id)},
    )
    assert r.status_code == 200
    doctors = r.json()
    assert len(doctors) >= 1
    doctor_id = doctors[0]["id"]

    # 5. Services
    r = await client.get(
        "/api/v1/services",
        headers=headers,
        params={"clinic_id": str(clinic_id)},
    )
    assert r.status_code == 200
    services = r.json()
    assert len(services) >= 1
    service_id = services[0]["id"]

    # 6. Schedule
    day = seed_data["date"]
    r = await client.get(
        f"/api/v1/doctors/{doctor_id}/schedule",
        params={"date": day.isoformat(), "clinic_id": str(seed_data["clinic_id"])},
        headers=headers,
    )
    assert r.status_code == 200
    schedule = r.json()
    slots = schedule.get("slots", [])
    assert len(slots) >= 1
    # Use a slot that is less likely to be taken by other tests (e.g. second slot),
    # falling back to the first if only one is available.
    slot = slots[1] if len(slots) > 1 else slots[0]
    start_time = slot.get("start_time", "10:00:00")
    if isinstance(start_time, str) and len(start_time) == 5:
        start_time = start_time + ":00"

    # 7. Create booking
    r = await client.post(
        f"/api/v1/patient/bookings?patient_id={patient_id}",
        json={
            "clinic_id": str(seed_data["clinic_id"]),
            "doctor_id": str(doctor_id),
            "service_id": str(service_id),
            "appointment_date": day.isoformat(),
            "appointment_time": start_time,
        },
        headers=headers,
    )
    assert r.status_code == 201
    booking = r.json()
    booking_id = booking["id"]
    assert booking.get("status") == "pending"

    # 8. Create payment (mock YooKassa via PaymentService.create_payment)
    with patch("src.api.v1.routers.payments.PaymentService") as MockPaymentService:
        mock_instance = MagicMock()
        mock_instance.create_payment = AsyncMock(
            return_value=MagicMock(
                payment_url="https://mock.yookassa.test/pay",
                provider_payment_id="mock-payment-id",
            )
        )
        MockPaymentService.return_value = mock_instance
        r = await client.post(
            "/api/v1/payments",
            json={"booking_id": booking_id},
            headers=headers,
        )
    assert r.status_code == 200
    pay_data = r.json()
    assert pay_data.get("payment_url")
    assert len(pay_data["payment_url"]) > 0
