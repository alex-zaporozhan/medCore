"""API smoke tests for pricing/discounts and AI module.

These tests cover pricing/discounts, payments, and AI module smoke scenarios:
- public/admin services pricing fields and discounts;
- payments original/discount/final amounts;
- AI assistant fallbacks when external AI is not configured;
- AI reports conflicts endpoints.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_public_clinic_services_pricing_no_discounts(
    client: AsyncClient,
    seed_data: dict,
):
    """GET /api/v1/public/clinics/{clinic_id}/services without discounts."""
    clinic_id = seed_data["clinic_id"]
    response = await client.get(f"/api/v1/public/clinics/{clinic_id}/services")
    assert response.status_code == 200, response.text

    data = response.json()
    assert isinstance(data, list)
    assert data, "Expected at least one service in public services response"

    service = data[0]
    # Old field must stay for backward compatibility
    assert "price" in service
    assert "base_price" in service
    assert "effective_price" in service
    assert "has_active_discount" in service

    price = Decimal(str(service["price"]))
    base_price = Decimal(str(service["base_price"]))
    effective_price = Decimal(str(service["effective_price"]))
    has_active_discount = bool(service["has_active_discount"])

    # In seed data we do not create discounts, so effective/base should match price
    assert price == base_price == effective_price
    assert has_active_discount is False


@pytest.mark.asyncio
async def test_admin_clinic_services_pricing_fields(
    client: AsyncClient,
    seed_data: dict,
    admin_auth: dict,
):
    """GET /api/v1/admin/clinics/{clinic_id}/services has old+new pricing fields."""
    clinic_id = seed_data["clinic_id"]
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    response = await client.get(f"/api/v1/admin/clinics/{clinic_id}/services", headers=headers)
    assert response.status_code == 200, response.text

    data = response.json()
    assert isinstance(data, list)
    assert data, "Expected at least one admin service"

    service_row = data[0]
    assert "service" in service_row, "AdminServiceRead should contain nested service object"
    s = service_row["service"]

    # Old field should remain
    assert "price" in s
    # New pricing fields from PricingService
    assert "base_price" in s
    assert "effective_price" in s
    assert "has_active_discount" in s


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_create_payment_pricing_fields_without_discount(
    client: AsyncClient,
    seed_data: dict,
    patient_auth: dict,
):
    """POST /api/v1/payments returns consistent pricing fields when no discounts."""
    access_token = patient_auth["access_token"]
    clinic_id = seed_data["clinic_id"]
    doctor_id = seed_data["doctor_id"]
    service_id = seed_data["service_id"]
    booking_date: date = seed_data["date"]

    # 1) Create booking — pick a free slot from schedule to avoid double-booking across tests
    headers = {"Authorization": f"Bearer {access_token}"}
    schedule_resp = await client.get(
        f"/api/v1/doctors/{doctor_id}/schedule",
        params={"date": booking_date.isoformat(), "clinic_id": str(clinic_id)},
        headers=headers,
    )
    assert schedule_resp.status_code == 200, schedule_resp.text
    schedule = schedule_resp.json()
    slots = schedule.get("slots") or []
    assert slots, "Expected at least one available slot in schedule"
    start_time = slots[0].get("start_time", "10:00:00")
    if isinstance(start_time, str) and len(start_time) == 5:
        start_time = start_time + ":00"

    booking_payload = {
        "clinic_id": str(clinic_id),
        "doctor_id": str(doctor_id),
        "service_id": str(service_id),
        "appointment_date": booking_date.isoformat(),
        "appointment_time": start_time,
    }
    booking_resp = await client.post(
        f"/api/v1/patient/bookings?patient_id={patient_auth['patient_id']}",
        headers=headers,
        json=booking_payload,
    )
    assert booking_resp.status_code == 201, booking_resp.text
    booking_data = booking_resp.json()
    booking_id = booking_data["id"]

    # 2) Create payment
    pay_resp = await client.post(
        "/api/v1/payments",
        headers=headers,
        json={"booking_id": booking_id},
    )
    assert pay_resp.status_code == 200, pay_resp.text
    data = pay_resp.json()

    # Always required
    assert "payment_url" in data
    assert "provider_payment_id" in data

    # When there is no discount, original/discount/final may be omitted (None).
    # If they are present, they must be consistent with zero discount.
    original_amount = data.get("original_amount")
    discount_amount = data.get("discount_amount")
    final_amount = data.get("final_amount")

    if discount_amount is not None:
        d = Decimal(str(discount_amount))
        assert d == Decimal("0"), "Expected zero discount in base scenario without discounts"

    if original_amount is not None and final_amount is not None:
        orig = Decimal(str(original_amount))
        final = Decimal(str(final_amount))
        assert orig == final, "Without discounts original and final amounts must match"


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_chat_ai_summary_fallback_without_provider(
    client: AsyncClient,
    seed_data: dict,
    admin_auth: dict,
):
    """AI summary endpoint should work with local fallback when AI provider is not configured."""
    clinic_id = seed_data["clinic_id"]
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Ensure there is at least one admin conversation; if not, endpoint should still not 500.
    resp = await client.get("/api/v1/admin/chat/conversations", headers=headers)
    assert resp.status_code in (200, 404), resp.text

    body = resp.json()
    items = body.get("items") if isinstance(body, dict) else body
    if resp.status_code == 200 and isinstance(items, list) and items:
        conv = items[0]
        conv_id = conv["conversation_id"]
        summary_resp = await client.get(
            f"/api/v1/admin/chat/conversations/{conv_id}/ai-summary",
            params={"clinic_id": str(clinic_id)},
            headers=headers,
        )
        assert summary_resp.status_code == 200, summary_resp.text
        summary_data = summary_resp.json()
        # Fallback DTO: at least summary field must exist
        assert "summary" in summary_data


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_chat_ai_suggest_reply_fallback_without_provider(
    client: AsyncClient,
    seed_data: dict,
    admin_auth: dict,
):
    """AI suggest-reply endpoint should return at least one variant without external AI."""
    clinic_id = seed_data["clinic_id"]
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    resp = await client.get("/api/v1/admin/chat/conversations", headers=headers)
    assert resp.status_code in (200, 404), resp.text

    body = resp.json()
    items = body.get("items") if isinstance(body, dict) else body
    if resp.status_code == 200 and isinstance(items, list) and items:
        conv = items[0]
        conv_id = conv["conversation_id"]
        reply_resp = await client.post(
            f"/api/v1/admin/chat/conversations/{conv_id}/ai-suggest-reply",
            params={"clinic_id": str(clinic_id)},
            json={"intent": "auto"},
            headers=headers,
        )
        assert reply_resp.status_code == 200, reply_resp.text
        data = reply_resp.json()
        assert "variants" in data
        assert isinstance(data["variants"], list)
        assert data["variants"], "Expected at least one local suggestion variant"


@pytest.mark.regression_chats
@pytest.mark.asyncio
async def test_admin_patient_ai_insight_fallback_without_provider(
    client: AsyncClient,
    seed_data: dict,
    admin_auth: dict,
):
    """Patient AI insight should work with heuristic fallback when AI provider is off."""
    clinic_id = seed_data["clinic_id"]
    patient_id = seed_data["patient_id"]
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    resp = await client.get(
        f"/api/v1/admin/patients/{patient_id}/ai-insight",
        params={"clinic_id": str(clinic_id)},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "summary" in data
    assert "risk_flags" in data


@pytest.mark.asyncio
async def test_admin_ai_reports_conflicts_reanalyze_and_list(
    client: AsyncClient,
    seed_data: dict,
    admin_auth: dict,
):
    """Smoke: POST /v1/admin/ai-reports/conflicts/reanalyze then GET conflicts."""
    clinic_id = seed_data["clinic_id"]
    today = date.today().isoformat()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    reanalyze_resp = await client.post(
        "/api/v1/admin/ai-reports/conflicts/reanalyze",
        params={"clinic_id": str(clinic_id)},
        json={"date_from": today, "date_to": today},
        headers=headers,
    )
    # Endpoint may respond 202/200 depending on implementation; main thing is no 5xx
    assert reanalyze_resp.status_code in (200, 202, 204), reanalyze_resp.text

    list_resp = await client.get(
        "/api/v1/admin/ai-reports/conflicts",
        params={"clinic_id": str(clinic_id), "date_from": today, "date_to": today},
        headers=headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    data = list_resp.json()
    # Response should be either empty or have summary/items fields according to DTO
    if isinstance(data, dict):
        assert "summary" in data
        assert "items" in data

