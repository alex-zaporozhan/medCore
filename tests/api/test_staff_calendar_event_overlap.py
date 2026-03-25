import pytest
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_staff_calendar_event_overlap_create_forbidden(client, admin_auth: dict) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    now = datetime.now(timezone.utc)
    base = now + timedelta(days=30)

    start1 = base.replace(hour=10, minute=0, second=0, microsecond=0)
    end1 = start1 + timedelta(hours=1)
    start2 = start1 + timedelta(minutes=30)
    end2 = start1 + timedelta(minutes=90)  # overlaps with [start1, end1)

    payload1 = {
        "title": "Overlap test #1",
        "description": None,
        "starts_at": start1.isoformat(),
        "ends_at": end1.isoformat(),
        "all_day": False,
        "task_id": None,
        "reminder_minutes_before": 15,
        "participant_admin_ids": [],
    }

    payload2 = {
        "title": "Overlap test #2",
        "description": None,
        "starts_at": start2.isoformat(),
        "ends_at": end2.isoformat(),
        "all_day": False,
        "task_id": None,
        "reminder_minutes_before": 15,
        "participant_admin_ids": [],
    }

    r1 = await client.post("/api/v1/admin/staff/calendar/events", json=payload1, headers=headers)
    assert r1.status_code == 201, r1.text
    ev1 = r1.json()
    assert "id" in ev1

    r2 = await client.post("/api/v1/admin/staff/calendar/events", json=payload2, headers=headers)
    assert r2.status_code == 400, r2.text
    data2 = r2.json()
    assert "пересекается" in data2.get("detail", "")


@pytest.mark.asyncio
async def test_staff_calendar_event_overlap_patch_forbidden(client, admin_auth: dict) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    now = datetime.now(timezone.utc)
    base = now + timedelta(days=31)

    start1 = base.replace(hour=10, minute=0, second=0, microsecond=0)
    end1 = start1 + timedelta(hours=1)

    # Second event placed after the first one.
    start2 = end1 + timedelta(hours=1)
    end2 = start2 + timedelta(hours=1)

    payload1 = {
        "title": "Overlap patch base #1",
        "description": None,
        "starts_at": start1.isoformat(),
        "ends_at": end1.isoformat(),
        "all_day": False,
        "task_id": None,
        "reminder_minutes_before": 15,
        "participant_admin_ids": [],
    }
    payload2 = {
        "title": "Overlap patch base #2",
        "description": None,
        "starts_at": start2.isoformat(),
        "ends_at": end2.isoformat(),
        "all_day": False,
        "task_id": None,
        "reminder_minutes_before": 15,
        "participant_admin_ids": [],
    }

    r1 = await client.post("/api/v1/admin/staff/calendar/events", json=payload1, headers=headers)
    assert r1.status_code == 201, r1.text
    ev1_id = r1.json()["id"]

    r2 = await client.post("/api/v1/admin/staff/calendar/events", json=payload2, headers=headers)
    assert r2.status_code == 201, r2.text
    ev2_id = r2.json()["id"]
    assert ev1_id != ev2_id

    # Patch event2 so it overlaps with event1.
    patch_payload = {
        "starts_at": (start1 + timedelta(minutes=15)).isoformat(),
        "ends_at": (start1 + timedelta(minutes=75)).isoformat(),
    }

    r3 = await client.patch(f"/api/v1/admin/staff/calendar/events/{ev2_id}", json=patch_payload, headers=headers)
    assert r3.status_code == 400, r3.text
    data3 = r3.json()
    assert "пересекается" in data3.get("detail", "")

