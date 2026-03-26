import pytest


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_tasks_bulk_partial_success_reports_rejected_reason(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    ok_resp = await client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={"title": "Bulk ok task", "priority": "medium"},
    )
    blocked_resp = await client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={"title": "Bulk blocked task", "priority": "medium"},
    )
    assert ok_resp.status_code == 201, ok_resp.text
    assert blocked_resp.status_code == 201, blocked_resp.text
    ok_id = ok_resp.json()["id"]
    blocked_id = blocked_resp.json()["id"]

    ok_patch_resp = await client.patch(
        f"/api/v1/admin/tasks/{ok_id}",
        headers=headers,
        json={"checklist_done": True},
    )
    assert ok_patch_resp.status_code == 200, ok_patch_resp.text

    patch_resp = await client.patch(
        f"/api/v1/admin/tasks/{blocked_id}",
        headers=headers,
        json={"blocked": True, "checklist_done": False},
    )
    assert patch_resp.status_code == 200, patch_resp.text

    bulk_resp = await client.post(
        "/api/v1/admin/tasks/bulk/status",
        headers=headers,
        json={"task_ids": [ok_id, blocked_id], "to_status": "done"},
    )
    assert bulk_resp.status_code == 200, bulk_resp.text
    body = bulk_resp.json()
    assert ok_id in body["applied"]
    rejected = {row["task_id"]: row for row in body["rejected"]}
    assert blocked_id in rejected
    assert rejected[blocked_id]["code"] in {"TASK_BLOCKED", "CHECKLIST_REQUIRED"}


@pytest.mark.asyncio
async def test_admin_tasks_wip_limit_is_enforced_on_status_move(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    in_progress_ids: list[str] = []
    for i in range(6):
        create_resp = await client.post(
            "/api/v1/admin/tasks",
            headers=headers,
            json={"title": f"WIP source task {i}", "priority": "medium"},
        )
        assert create_resp.status_code == 201, create_resp.text
        task_id = create_resp.json()["id"]
        in_progress_ids.append(task_id)
        move_resp = await client.patch(
            f"/api/v1/admin/tasks/{task_id}",
            headers=headers,
            json={"status": "in_progress"},
        )
        assert move_resp.status_code == 200, move_resp.text

    extra_resp = await client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={"title": "WIP overflow task", "priority": "medium"},
    )
    assert extra_resp.status_code == 201, extra_resp.text
    overflow_id = extra_resp.json()["id"]
    move_overflow = await client.patch(
        f"/api/v1/admin/tasks/{overflow_id}",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert move_overflow.status_code == 409, move_overflow.text
    payload = move_overflow.json().get("detail", {})
    assert payload.get("code") == "WIP_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_admin_task_transitions_endpoint_includes_event_metadata(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    create_resp = await client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={"title": "Transitions metadata task", "priority": "medium"},
    )
    assert create_resp.status_code == 201, create_resp.text
    task_id = create_resp.json()["id"]

    block_resp = await client.patch(
        f"/api/v1/admin/tasks/{task_id}",
        headers=headers,
        json={"blocked": True, "blocked_reason": "Need external confirmation"},
    )
    assert block_resp.status_code == 200, block_resp.text

    transitions_resp = await client.get(
        f"/api/v1/admin/tasks/{task_id}/transitions?limit=50",
        headers=headers,
    )
    assert transitions_resp.status_code == 200, transitions_resp.text
    rows = transitions_resp.json()
    assert isinstance(rows, list)
    assert any((row.get("metadata") or {}).get("event") == "blocked" for row in rows)


@pytest.mark.asyncio
async def test_task_calendar_context_invite_and_ack_visible(client, admin_auth, doctor_auth):
    owner_headers = _auth_headers(admin_auth["access_token"])
    doctor_headers = _auth_headers(doctor_auth["access_token"])

    create_task_resp = await client.post(
        "/api/v1/admin/tasks",
        headers=owner_headers,
        json={
            "title": "Calendar invite for task",
            "priority": "medium",
            "assignee_ids": [doctor_auth["admin_id"]],
        },
    )
    assert create_task_resp.status_code == 201, create_task_resp.text
    task_id = create_task_resp.json()["id"]

    create_event_resp = await client.post(
        "/api/v1/admin/staff/calendar/events",
        headers=owner_headers,
        json={
            "title": "Task slot",
            "starts_at": "2030-01-10T10:00:00",
            "ends_at": "2030-01-10T11:00:00",
            "task_id": task_id,
            "participant_admin_ids": [admin_auth["admin_id"]],
        },
    )
    assert create_event_resp.status_code == 201, create_event_resp.text
    event_id = create_event_resp.json()["id"]

    invite_resp = await client.post(
        f"/api/v1/admin/tasks/{task_id}/calendar-events/{event_id}/invite",
        headers=owner_headers,
        json={"admin_ids": [doctor_auth["admin_id"]]},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    assert invite_resp.json()["participants_count"] >= 2

    ack_resp = await client.post(
        f"/api/v1/admin/staff/calendar/events/{event_id}/invitations/ack",
        headers=doctor_headers,
    )
    assert ack_resp.status_code == 200, ack_resp.text

    context_resp = await client.get(
        f"/api/v1/admin/tasks/{task_id}/calendar-context",
        headers=owner_headers,
    )
    assert context_resp.status_code == 200, context_resp.text
    rows = context_resp.json()
    assert rows
    doctor_row = None
    for p in rows[0]["participants"]:
        if p["admin_id"] == doctor_auth["admin_id"]:
            doctor_row = p
            break
    assert doctor_row is not None
    assert doctor_row["acknowledged_at"] is not None
