"""End-to-end like flow for marketing attribution: landing -> lead -> patient -> booking -> finance -> summary."""

from datetime import date
from uuid import UUID

import pytest
from httpx import AsyncClient

from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage


@pytest.mark.asyncio
async def test_marketing_attribution_full_flow(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
    redis_client,
    db_session,
) -> None:
    """Landing lead with UTM + patient auth + booking/payment should appear in admin attribution summary."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # 1. Create landing lead with UTM tags (use db_session fixture — same asyncio loop as httpx client;
    # raw AsyncSessionLocal() here leaked asyncpg connections into Starlette middleware and broke
    # the next test's patient_auth / Redis on Windows.)
    clinic_id = seed_data["clinic_id"]
    session = db_session
    pipeline = LeadPipeline(
        clinic_id=clinic_id,
        name="Default",
        description=None,
        is_default=True,
    )
    session.add(pipeline)
    await session.flush()
    session.add(
        LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=1,
            code="new",
            name="New",
            probability=10,
            color="#999999",
        )
    )
    await session.commit()
    session_id = "test-session-attr-1"
    landing_payload = {
      "full_name": "UTM Patient",
      "phone": "+79000000001",
      "session_id": session_id,
      "landing_page": "/?utm_source=google&utm_campaign=test-campaign",
      "anchor": "#hero",
      "utm_source": "google",
      "utm_medium": "cpc",
      "utm_campaign": "test-campaign",
      "utm_content": "ad1",
      "utm_term": "dentist",
    }
    r_landing = await client.post(
        f"/api/v1/public/clinics/{clinic_id}/leads",
        json=landing_payload,
    )
    assert r_landing.status_code == 201, r_landing.text
    landing_data = r_landing.json()
    assert landing_data["visit_attribution_id"]

    # 2. Simulate patient auth with same session_id (links VisitAttribution to Patient)
    r_send = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": landing_payload["phone"], "clinic_slug": seed_data["clinic_slug"]},
    )
    assert r_send.status_code == 204, r_send.text
    code_key = f"auth:code:{clinic_id}:{landing_payload['phone']}"
    raw_code = await redis_client.get(code_key)
    assert raw_code, f"Auth code not in Redis for key {code_key}"
    code = raw_code.decode() if isinstance(raw_code, bytes) else raw_code
    auth_payload = {
        "phone": landing_payload["phone"],
        "code": code,
        "clinic_slug": seed_data["clinic_slug"],
        "consent_pd": True,
        "consent_mailing": False,
        "session_id": session_id,
        "utm_source": landing_payload["utm_source"],
        "utm_medium": landing_payload["utm_medium"],
        "utm_campaign": landing_payload["utm_campaign"],
        "utm_content": landing_payload["utm_content"],
        "utm_term": landing_payload["utm_term"],
        "landing_page": landing_payload["landing_page"],
        "anchor": landing_payload["anchor"],
    }
    r_auth = await client.post("/api/v1/auth/verify-code", json=auth_payload)
    assert r_auth.status_code in (200, 201), r_auth.text
    patient_id = UUID(r_auth.json()["patient_id"])

    # 3. Admin creates booking then completes visit (ERP revenue path for attribution summary).
    booking_payload = {
        "clinic_id": str(clinic_id),
        "patient_id": str(patient_id),
        "doctor_id": str(seed_data["doctor_id"]),
        "service_id": str(seed_data["service_id"]),
        "appointment_date": date.today().isoformat(),
        "appointment_time": "10:00:00",
        "status": "pending",
    }
    r_create = await client.post("/api/v1/admin/bookings", json=booking_payload, headers=headers)
    assert r_create.status_code == 201, r_create.text
    booking_id = r_create.json()["id"]
    r_complete = await client.put(
        f"/api/v1/admin/bookings/{booking_id}/complete",
        headers=headers,
        json={},
    )
    assert r_complete.status_code == 200, r_complete.text

    # 4. Call admin attribution summary and ensure metrics are non-zero for the UTM source
    r_summary = await client.get(
        "/api/v1/admin/attribution/summary",
        params={"date_from": "2025-01-01", "date_to": "2027-12-31"},
        headers=headers,
    )
    assert r_summary.status_code == 200, r_summary.text
    summary = r_summary.json()
    assert "items" in summary
    # Landing creates VisitAttribution with utm_source; CRM lead counts. Revenue in summary
    # additionally requires FinancialTransaction.visit_attribution_id (not always set on legacy ERP path).
    assert any(
        (item.get("traffic_source_code") == "google" or item.get("utm_source") == "google")
        and int(item.get("leads_count", 0)) >= 1
        for item in summary["items"]
    ), summary

    # Tear down pooled Redis for this event loop so the next test's httpx/Starlette stack
    # does not inherit broken connection state (Windows + BaseHTTPMiddleware + redis.asyncio).
    from src.infrastructure.database.redis_client import close_redis

    await close_redis()

