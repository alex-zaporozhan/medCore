"""E2E: booking flow from auth to payment URL."""

import random
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


def _booking_error_code_from_response(r) -> str | None:
    """Parse FastAPI HTTPException body for ``slot_unavailable`` etc. (same shape as API tests)."""
    try:
        body = r.json()
    except Exception:
        return None
    if not isinstance(body, dict):
        return None
    detail = body.get("detail")
    if isinstance(detail, dict):
        return detail.get("code")
    return body.get("code")


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

    # 4–7. Use seed doctor/service only. Full suite shares one doctor: schedule can show a slot as
    # free while another test books it before POST (TOCTOU). Retry POST across slots/weeks like
    # ``test_money_flows`` / ``test_marketing_attribution_flow`` (slot_unavailable).
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    base_day = seed_data["date"]
    booking = None
    last_booking_response = None
    for week in range(12):
        cand = base_day + timedelta(weeks=week)
        r_sched = await client.get(
            f"/api/v1/doctors/{doctor_id}/schedule",
            params={"date": cand.isoformat(), "clinic_id": str(clinic_id)},
            headers=headers,
        )
        assert r_sched.status_code == 200, r_sched.text
        schedule = r_sched.json()
        slots = [s for s in schedule.get("slots", []) if s.get("is_available", True)]
        # Later slots collide less often with other tests that pick morning grid.
        for slot in reversed(slots):
            start_time = slot.get("start_time", "10:00:00")
            if isinstance(start_time, str) and len(start_time) == 5:
                start_time = start_time + ":00"
            r = await client.post(
                f"/api/v1/patient/bookings?patient_id={patient_id}",
                json={
                    "clinic_id": str(seed_data["clinic_id"]),
                    "doctor_id": str(doctor_id),
                    "service_id": str(service_id),
                    "appointment_date": cand.isoformat(),
                    "appointment_time": start_time,
                },
                headers=headers,
            )
            last_booking_response = r
            if r.status_code == 201:
                booking = r.json()
                break
            if r.status_code == 400 and _booking_error_code_from_response(r) == "slot_unavailable":
                continue
            pytest.fail(f"unexpected booking response {r.status_code}: {r.text}")
        if booking:
            break
    assert booking is not None, (
        "no successful patient booking in 12 weeks of seed weekday; "
        f"last={getattr(last_booking_response, 'status_code', None)} {getattr(last_booking_response, 'text', '')}"
    )
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
