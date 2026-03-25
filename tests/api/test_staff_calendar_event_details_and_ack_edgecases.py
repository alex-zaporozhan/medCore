import uuid
from datetime import datetime, timedelta, timezone

import pytest


def _day_range_iso(dt: datetime) -> tuple[str, str]:
    start = datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(dt.year, dt.month, dt.day, 23, 59, 59, tzinfo=timezone.utc)
    return start.isoformat(), end.isoformat()


@pytest.mark.asyncio
async def test_staff_calendar_event_details_non_participant_forbidden(
    client,
    admin_auth: dict,
    doctor_auth: dict,
) -> None:
    headers_owner = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    headers_doctor = {"Authorization": f"Bearer {doctor_auth['access_token']}"}

    now = datetime.now(timezone.utc)
    base = now + timedelta(days=140)
    start = base.replace(hour=12, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    from_iso, to_iso = _day_range_iso(start)

    # Event where only the creator (owner) is a participant/invitee.
    create_payload = {
        "title": "Staff calendar event (details forbidden)",
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
    r2 = await client.get(f"/api/v1/admin/staff/calendar/events/{event_id}", headers=headers_doctor)
    assert r2.status_code == 403, r2.text

    # Month-grid still should not leak unseen invite info.
    r3 = await client.get(
        "/api/v1/admin/staff/calendar/month",
        params={"from": from_iso, "to": to_iso},
        headers=headers_doctor,
    )
    assert r3.status_code == 200, r3.text
    data = r3.json()
    day_key = start.date().isoformat()
    day = next((d for d in data["days"] if d["date"] == day_key), None)
    assert day is not None
    assert event_id not in day["unseen_invite_event_ids"]


@pytest.mark.asyncio
async def test_staff_calendar_event_details_ack_fields_update(
    client,
    admin_auth: dict,
    doctor_auth: dict,
) -> None:
    headers_owner = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    headers_doctor = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
    doctor_id = doctor_auth["admin_id"]

    now = datetime.now(timezone.utc)
    base = now + timedelta(days=160)
    start = base.replace(hour=12, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)

    create_payload = {
        "title": "Staff calendar event (details ack fields)",
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
    event_id = r.json()["id"]

    # Before ack: doctor sees invitation_acknowledged_at=None.
    details_before = await client.get(f"/api/v1/admin/staff/calendar/events/{event_id}", headers=headers_doctor)
    assert details_before.status_code == 200, details_before.text
    details_before_json = details_before.json()
    assert details_before_json["invitation_acknowledged_at"] is None
    assert details_before_json["creator_ack_summary"] is None

    # Ack by doctor.
    ack = await client.post(
        f"/api/v1/admin/staff/calendar/events/{event_id}/invitations/ack",
        headers=headers_doctor,
    )
    assert ack.status_code == 200, ack.text
    ack_data = ack.json()
    assert ack_data["event_id"] == event_id
    assert ack_data["acknowledged_at"] is not None

    # After ack: doctor sees invitation_acknowledged_at != null.
    details_after = await client.get(f"/api/v1/admin/staff/calendar/events/{event_id}", headers=headers_doctor)
    assert details_after.status_code == 200, details_after.text
    details_after_json = details_after.json()
    assert details_after_json["invitation_acknowledged_at"] is not None
    assert details_after_json["creator_ack_summary"] is None

    # Owner sees creator_ack_summary updated (ack count among OTHER participants).
    owner_details = await client.get(f"/api/v1/admin/staff/calendar/events/{event_id}", headers=headers_owner)
    assert owner_details.status_code == 200, owner_details.text
    owner_details_json = owner_details.json()

    # Owner has not acknowledged his own invitation -> should stay null.
    assert owner_details_json["invitation_acknowledged_at"] is None

    creator_ack = owner_details_json["creator_ack_summary"]
    assert creator_ack is not None
    assert creator_ack["total_participants"] == 1
    assert creator_ack["acknowledged_participants"] == 1


@pytest.mark.asyncio
async def test_staff_calendar_ack_404_for_missing_event(client, doctor_auth: dict) -> None:
    headers_doctor = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
    missing_event_id = uuid.uuid4()

    ack = await client.post(
        f"/api/v1/admin/staff/calendar/events/{missing_event_id}/invitations/ack",
        headers=headers_doctor,
    )
    assert ack.status_code == 404, ack.text


@pytest.mark.asyncio
async def test_staff_calendar_ack_not_reset_on_participant_sync_patch(
    client,
    admin_auth: dict,
    doctor_auth: dict,
) -> None:
    headers_owner = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    headers_doctor = {"Authorization": f"Bearer {doctor_auth['access_token']}"}
    doctor_id = doctor_auth["admin_id"]

    now = datetime.now(timezone.utc)
    base = now + timedelta(days=190)
    start = base.replace(hour=12, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)

    create_payload = {
        "title": "Staff calendar event (ack persistence)",
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
    event_id = r.json()["id"]

    ack = await client.post(
        f"/api/v1/admin/staff/calendar/events/{event_id}/invitations/ack",
        headers=headers_doctor,
    )
    assert ack.status_code == 200, ack.text

    details_after_ack = await client.get(f"/api/v1/admin/staff/calendar/events/{event_id}", headers=headers_doctor)
    assert details_after_ack.status_code == 200, details_after_ack.text
    acked_at_before_patch = details_after_ack.json()["invitation_acknowledged_at"]
    assert acked_at_before_patch is not None

    # Patch participants with the same set -> ack must not reset.
    patch_payload = {
        "participant_admin_ids": [doctor_id],
    }
    r2 = await client.patch(f"/api/v1/admin/staff/calendar/events/{event_id}", json=patch_payload, headers=headers_owner)
    assert r2.status_code == 200, r2.text

    details_after_patch = await client.get(
        f"/api/v1/admin/staff/calendar/events/{event_id}",
        headers=headers_doctor,
    )
    assert details_after_patch.status_code == 200, details_after_patch.text
    acked_at_after_patch = details_after_patch.json()["invitation_acknowledged_at"]
    assert acked_at_after_patch == acked_at_before_patch

