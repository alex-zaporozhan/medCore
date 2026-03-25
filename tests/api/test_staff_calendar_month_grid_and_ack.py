import pytest
from datetime import datetime, timedelta, timezone


def _day_range_iso(dt: datetime) -> tuple[str, str]:
    start = datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(dt.year, dt.month, dt.day, 23, 59, 59, tzinfo=timezone.utc)
    return start.isoformat(), end.isoformat()


@pytest.mark.asyncio
async def test_staff_calendar_month_grid_unseen_invites_and_reminders(
    client,
    admin_auth: dict,
    doctor_auth: dict,
) -> None:
    headers_owner = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    headers_doctor = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
    doctor_id = doctor_auth["admin_id"]

    now = datetime.now(timezone.utc)
    base = now + timedelta(days=45)
    start = base.replace(hour=12, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    from_iso, to_iso = _day_range_iso(start)

    create_payload = {
        "title": "Staff calendar event (test unseen/reminders)",
        "description": None,
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat(),
        "all_day": False,
        "task_id": None,
        "reminder_minutes_before": 15,
        "participant_admin_ids": [doctor_id],
    }

    r = await client.post("/api/v1/admin/staff/calendar/events", json=create_payload, headers=headers_owner)
    assert r.status_code == 201, r.text
    event = r.json()
    event_id = event["id"]

    r2 = await client.get(
        "/api/v1/admin/staff/calendar/month",
        params={"from": from_iso, "to": to_iso},
        headers=headers_doctor,
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()

    assert "notification_signals" in data
    assert isinstance(data["notification_signals"]["unseen_invites_count"], int)

    day_key = start.date().isoformat()
    day = next((d for d in data["days"] if d["date"] == day_key), None)
    assert day is not None
    assert event_id in day["unseen_invite_event_ids"]
    assert event_id in day["reminder_event_ids"]

    prev_unseen = data["notification_signals"]["unseen_invites_count"]

    ack = await client.post(
        f"/api/v1/admin/staff/calendar/events/{event_id}/invitations/ack",
        headers=headers_doctor,
    )
    assert ack.status_code == 200, ack.text
    ack_data = ack.json()
    assert ack_data["event_id"] == event_id
    assert ack_data["acknowledged_at"] is not None

    r3 = await client.get(
        "/api/v1/admin/staff/calendar/month",
        params={"from": from_iso, "to": to_iso},
        headers=headers_doctor,
    )
    assert r3.status_code == 200, r3.text
    data_after = r3.json()

    # Ack should clear exactly one unseen invitation for this event.
    assert data_after["notification_signals"]["unseen_invites_count"] == prev_unseen - 1

    day_after = next((d for d in data_after["days"] if d["date"] == day_key), None)
    assert day_after is not None
    assert event_id not in day_after["unseen_invite_event_ids"]


@pytest.mark.asyncio
async def test_staff_calendar_ack_for_non_participant_forbidden(
    client,
    admin_auth: dict,
    doctor_auth: dict,
) -> None:
    headers_owner = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    headers_doctor = {"Authorization": f"Bearer {doctor_auth['access_token']}"}

    now = datetime.now(timezone.utc)
    base = now + timedelta(days=60)
    start = base.replace(hour=12, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    from_iso, to_iso = _day_range_iso(start)

    # Event where only the creator (owner) is a participant/invitee.
    create_payload = {
        "title": "Staff calendar event (test forbidden ack)",
        "description": None,
        "starts_at": start.isoformat(),
        "ends_at": end.isoformat(),
        "all_day": False,
        "task_id": None,
        "reminder_minutes_before": 15,
        "participant_admin_ids": [],
    }

    r = await client.post("/api/v1/admin/staff/calendar/events", json=create_payload, headers=headers_owner)
    assert r.status_code == 201, r.text
    event_id = r.json()["id"]

    # Doctor is not a participant -> 403.
    ack = await client.post(
        f"/api/v1/admin/staff/calendar/events/{event_id}/invitations/ack",
        headers=headers_doctor,
    )
    assert ack.status_code == 403

    # Also ensure month-grid for doctor shows no unseen invitation for that event.
    r2 = await client.get(
        "/api/v1/admin/staff/calendar/month",
        params={"from": from_iso, "to": to_iso},
        headers=headers_doctor,
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    day_key = start.date().isoformat()
    day = next((d for d in data["days"] if d["date"] == day_key), None)
    assert day is not None
    assert event_id not in day["unseen_invite_event_ids"]

