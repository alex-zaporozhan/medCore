"""End-to-end like flow for marketing attribution: landing -> lead -> patient -> booking -> finance -> summary."""

from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.domain.entities.lead_card import LeadCard
from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage
from src.domain.entities.visit_attribution import VisitAttribution


def _appointment_days_for_seed_doctor(seed_data: dict) -> list[date]:
    """Dates aligned with ``DoctorWorkingHours`` from ``seed_data`` (same weekday as ``seed_data['date']``)."""
    base: date = seed_data["date"]
    return [base + timedelta(weeks=w) for w in range(1, 20)]


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
    pl_row = await session.execute(
        select(LeadPipeline).where(
            LeadPipeline.clinic_id == clinic_id,
            LeadPipeline.is_default.is_(True),
        ).limit(1)
    )
    pipeline = pl_row.scalar_one_or_none()
    if pipeline is None:
        pipeline = LeadPipeline(
            clinic_id=clinic_id,
            name="Default",
            description=None,
            is_default=True,
        )
        session.add(pipeline)
        await session.flush()
    st_row = await session.execute(
        select(LeadStage.id).where(LeadStage.pipeline_id == pipeline.id).limit(1)
    )
    if st_row.scalar_one_or_none() is None:
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
    # Unique per run: idempotent landing API returns an old VisitAttribution if session_id+lead already exist.
    session_id = f"test-session-attr-{uuid4()}"
    # Random E.164 suffix avoids cross-test patient/Redis collisions in long suites.
    landing_phone = f"+7900{uuid4().int % 10_000_000:07d}"
    landing_payload = {
      "full_name": "UTM Patient",
      "phone": landing_phone,
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
    lead_id_str = str(landing_data["lead_id"])

    # 2. Simulate patient auth with same session_id (links VisitAttribution to Patient)
    r_send = await client.post(
        "/api/v1/auth/send-code",
        json={"phone": landing_phone, "clinic_slug": seed_data["clinic_slug"]},
    )
    assert r_send.status_code == 204, r_send.text
    code_key = f"auth:code:{clinic_id}:{landing_phone}"
    raw_code = await redis_client.get(code_key)
    assert raw_code, f"Auth code not in Redis for key {code_key}"
    code = raw_code.decode() if isinstance(raw_code, bytes) else raw_code
    auth_payload = {
        "phone": landing_phone,
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
    # Use weekdays covered by seed ``DoctorWorkingHours`` (see conftest ``seed_data['date']``), not random
    # calendar days — random 1..N days mostly miss that weekday and break completion/ERP in long runs.
    # Retry on slot_unavailable (shared seed doctor, partial unique on active bookings).
    booking_id = None
    candidate_days = _appointment_days_for_seed_doctor(seed_data)
    for attempt in range(24):
        appt_day = candidate_days[attempt % len(candidate_days)]
        appt_h = 10 + (uuid4().int % 5)
        appt_m, appt_s = uuid4().int % 60, uuid4().int % 60
        booking_payload = {
            "clinic_id": str(clinic_id),
            "patient_id": str(patient_id),
            "doctor_id": str(seed_data["doctor_id"]),
            "service_id": str(seed_data["service_id"]),
            "appointment_date": appt_day.isoformat(),
            "appointment_time": f"{appt_h:02d}:{appt_m:02d}:{appt_s:02d}",
            "status": "pending",
        }
        r_create = await client.post("/api/v1/admin/bookings", json=booking_payload, headers=headers)
        if r_create.status_code == 201:
            booking_id = r_create.json()["id"]
            break
        if r_create.status_code == 400:
            err_code = None
            try:
                body = r_create.json()
                if isinstance(body, dict):
                    detail = body.get("detail")
                    if isinstance(detail, dict):
                        err_code = detail.get("code")
                    else:
                        err_code = body.get("code")
            except Exception:
                pass
            if err_code == "slot_unavailable":
                continue
        assert r_create.status_code == 201, r_create.text
    assert booking_id is not None
    r_complete = await client.put(
        f"/api/v1/admin/bookings/{booking_id}/complete",
        headers=headers,
        json={},
    )
    assert r_complete.status_code == 200, r_complete.text

    # 4. Attribution chain must persist (LeadCard ↔ VisitAttribution, UTM on visit).
    # Rollback clears any stale transaction/identity state so SELECTs see rows committed by the API
    # without opening a second NullPool session (avoids SAWarning / GC connection leaks on Windows).
    lead_uuid = UUID(lead_id_str)
    await db_session.rollback()
    lc_row = await db_session.execute(
        select(LeadCard.visit_attribution_id, LeadCard.clinic_id).where(LeadCard.id == lead_uuid)
    )
    va_id, lc_clinic = lc_row.one()
    assert lc_clinic == clinic_id
    assert va_id is not None

    va_row = await db_session.execute(select(VisitAttribution).where(VisitAttribution.id == va_id))
    va = va_row.scalar_one()
    assert va.utm_source == "google"

