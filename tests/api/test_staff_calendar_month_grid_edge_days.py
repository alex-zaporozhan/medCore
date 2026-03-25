from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_month_grid_includes_events_on_leading_days_from_prev_month(
    client,
    admin_auth: dict,
) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Create event on Feb 25, 2026.
    ev_start = datetime(2026, 2, 25, 9, 0, tzinfo=timezone.utc)
    ev_end = ev_start + timedelta(hours=1)
    create_payload = {
        "title": "Edge-day event",
        "description": None,
        "starts_at": ev_start.isoformat(),
        "ends_at": ev_end.isoformat(),
        "all_day": False,
        "task_id": None,
        "reminder_minutes_before": 15,
        "participant_admin_ids": [],
    }
    created = await client.post("/api/v1/admin/staff/calendar/events", json=create_payload, headers=headers)
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]

    # Request March month-grid. It includes leading days from February (Mon-first grid).
    month = await client.get(
        "/api/v1/admin/staff/calendar/month",
        params={
            "from": "2026-03-01T00:00:00+00:00",
            "to": "2026-03-31T23:59:59+00:00",
        },
        headers=headers,
    )
    assert month.status_code == 200, month.text
    data = month.json()

    feb_25 = next((d for d in data["days"] if d["date"] == "2026-02-25"), None)
    assert feb_25 is not None, "Leading grid day should be present"
    assert any(e["id"] == event_id for e in feb_25["events"]), "Event on leading day must be visible"

