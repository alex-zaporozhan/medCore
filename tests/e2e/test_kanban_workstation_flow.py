"""E2E: Kanban workstation full path with calendar invite/ack."""

import pytest
from httpx import AsyncClient


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_kanban_task_flow_create_chat_block_unblock_done_with_invite_ack(
    client: AsyncClient,
    admin_auth: dict,
    doctor_auth: dict,
):
    owner_headers = _auth_headers(admin_auth["access_token"])
    doctor_headers = _auth_headers(doctor_auth["access_token"])

    # 1) Create task.
    create_task_resp = await client.post(
        "/api/v1/admin/tasks",
        headers=owner_headers,
        json={
            "title": "E2E task workstation flow",
            "priority": "high",
            "assignee_ids": [doctor_auth["admin_id"]],
        },
    )
    assert create_task_resp.status_code == 201, create_task_resp.text
    task_id = create_task_resp.json()["id"]

    # 2) Task chat.
    comment_resp = await client.post(
        f"/api/v1/admin/tasks/{task_id}/comments",
        headers=owner_headers,
        json={"text": "E2E hello in task room"},
    )
    assert comment_resp.status_code == 201, comment_resp.text

    # 3) Block with reason.
    block_resp = await client.patch(
        f"/api/v1/admin/tasks/{task_id}",
        headers=owner_headers,
        json={"blocked": True, "blocked_reason": "Awaiting patient confirmation"},
    )
    assert block_resp.status_code == 200, block_resp.text
    assert block_resp.json()["blocked"] is True

    # 4) Unblock + checklist done.
    unblock_resp = await client.patch(
        f"/api/v1/admin/tasks/{task_id}",
        headers=owner_headers,
        json={"blocked": False, "checklist_done": True},
    )
    assert unblock_resp.status_code == 200, unblock_resp.text
    assert unblock_resp.json()["blocked"] is False
    assert unblock_resp.json()["checklist_done"] is True

    # 5) Move to done.
    done_resp = await client.patch(
        f"/api/v1/admin/tasks/{task_id}",
        headers=owner_headers,
        json={"status": "done"},
    )
    assert done_resp.status_code == 200, done_resp.text
    assert done_resp.json()["status"] == "done"

    # 6) Create calendar slot linked to task.
    create_event_resp = await client.post(
        "/api/v1/admin/staff/calendar/events",
        headers=owner_headers,
        json={
            "title": "E2E task linked slot",
            "starts_at": "2030-03-10T10:00:00",
            "ends_at": "2030-03-10T11:00:00",
            "task_id": task_id,
            "participant_admin_ids": [admin_auth["admin_id"]],
        },
    )
    assert create_event_resp.status_code == 201, create_event_resp.text
    event_id = create_event_resp.json()["id"]

    # 7) Invite doctor to task slot via task endpoint.
    invite_resp = await client.post(
        f"/api/v1/admin/tasks/{task_id}/calendar-events/{event_id}/invite",
        headers=owner_headers,
        json={"admin_ids": [doctor_auth["admin_id"]]},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    assert invite_resp.json()["participants_count"] >= 2

    # 8) Doctor acknowledges invitation.
    ack_resp = await client.post(
        f"/api/v1/admin/staff/calendar/events/{event_id}/invitations/ack",
        headers=doctor_headers,
    )
    assert ack_resp.status_code == 200, ack_resp.text

    # 9) Verify ACK visible in task calendar context.
    context_resp = await client.get(
        f"/api/v1/admin/tasks/{task_id}/calendar-context",
        headers=owner_headers,
    )
    assert context_resp.status_code == 200, context_resp.text
    rows = context_resp.json()
    assert rows
    participants = rows[0]["participants"]
    doctor_row = next((p for p in participants if p["admin_id"] == doctor_auth["admin_id"]), None)
    assert doctor_row is not None
    assert doctor_row["acknowledged_at"] is not None
