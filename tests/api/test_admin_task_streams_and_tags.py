"""API tests: task streams, tags, and task list/create with stream_id / tag_ids."""

from __future__ import annotations

import uuid

import pytest


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_task_streams_list_includes_general_and_create_stream(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    list_resp = await client.get("/api/v1/admin/task-streams", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    rows = list_resp.json()
    assert isinstance(rows, list)
    assert any(r.get("slug") == "general" for r in rows)
    general_id = next(r["id"] for r in rows if r.get("slug") == "general")

    create_resp = await client.post(
        "/api/v1/admin/task-streams",
        headers=headers,
        json={"name": "Design flow"},
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["name"] == "Design flow"
    assert created["slug"] == "design-flow"
    assert created["id"] != general_id


@pytest.mark.asyncio
async def test_admin_tasks_filter_by_stream_and_create_with_stream_and_tags(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])

    streams_resp = await client.get("/api/v1/admin/task-streams", headers=headers)
    assert streams_resp.status_code == 200, streams_resp.text
    streams = streams_resp.json()
    general_id = next(s["id"] for s in streams if s.get("slug") == "general")

    new_stream = await client.post(
        "/api/v1/admin/task-streams",
        headers=headers,
        json={"name": "Marketing"},
    )
    assert new_stream.status_code == 201, new_stream.text
    marketing_id = new_stream.json()["id"]

    tag_resp = await client.post(
        "/api/v1/admin/task-tags",
        headers=headers,
        json={"name": "Q1"},
    )
    assert tag_resp.status_code == 201, tag_resp.text
    tag_id = tag_resp.json()["id"]

    task_a = await client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={
            "title": "Stream marketing only",
            "priority": "medium",
            "stream_id": marketing_id,
        },
    )
    assert task_a.status_code == 201, task_a.text
    assert task_a.json()["stream_id"] == marketing_id

    task_b = await client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={
            "title": "General with tag",
            "priority": "low",
            "stream_id": general_id,
            "tag_ids": [tag_id],
        },
    )
    assert task_b.status_code == 201, task_b.text
    body_b = task_b.json()
    assert body_b["stream_id"] == general_id
    assert tag_id in (body_b.get("tag_ids") or [])

    filtered_m = await client.get(
        f"/api/v1/admin/tasks?stream_id={marketing_id}",
        headers=headers,
    )
    assert filtered_m.status_code == 200, filtered_m.text
    ids_m = {t["id"] for t in filtered_m.json()}
    assert task_a.json()["id"] in ids_m
    assert task_b.json()["id"] not in ids_m

    filtered_tags = await client.get(
        f"/api/v1/admin/tasks?tag_ids={tag_id}",
        headers=headers,
    )
    assert filtered_tags.status_code == 200, filtered_tags.text
    ids_t = {t["id"] for t in filtered_tags.json()}
    assert task_b.json()["id"] in ids_t
    assert task_a.json()["id"] not in ids_t


@pytest.mark.asyncio
async def test_admin_tasks_list_rejects_unknown_stream_id(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    bad = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/admin/tasks?stream_id={bad}", headers=headers)
    assert resp.status_code == 400, resp.text
    err = resp.json().get("detail") or {}
    assert err.get("code") == "STREAM_NOT_IN_CLINIC"
    assert err.get("field") == "stream_id"


@pytest.mark.asyncio
async def test_admin_tasks_list_rejects_unknown_tag_ids(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    bad = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/admin/tasks?tag_ids={bad}", headers=headers)
    assert resp.status_code == 400, resp.text
    err = resp.json().get("detail") or {}
    assert err.get("code") == "TAG_INVALID"
    assert err.get("field") == "tag_ids"


@pytest.mark.asyncio
async def test_admin_task_stream_slug_conflict(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    first = await client.post(
        "/api/v1/admin/task-streams",
        headers=headers,
        json={"name": "Unique slug row"},
    )
    assert first.status_code == 201, first.text
    dup = await client.post(
        "/api/v1/admin/task-streams",
        headers=headers,
        json={"name": "Unique slug row"},
    )
    assert dup.status_code == 409, dup.text
    assert dup.json().get("detail", {}).get("code") == "STREAM_SLUG_CONFLICT"


@pytest.mark.asyncio
async def test_admin_tasks_list_allows_archived_stream_filter(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    created = await client.post(
        "/api/v1/admin/task-streams",
        headers=headers,
        json={"name": "To archive stream"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["id"]

    task_resp = await client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={"title": "In archivable stream", "priority": "medium", "stream_id": sid},
    )
    assert task_resp.status_code == 201, task_resp.text

    patch = await client.patch(
        f"/api/v1/admin/task-streams/{sid}",
        headers=headers,
        json={"is_archived": True},
    )
    assert patch.status_code == 200, patch.text

    listed = await client.get(f"/api/v1/admin/tasks?stream_id={sid}", headers=headers)
    assert listed.status_code == 200, listed.text
    ids = {t["id"] for t in listed.json()}
    assert task_resp.json()["id"] in ids


@pytest.mark.asyncio
async def test_admin_task_patch_rejects_archived_stream(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    created = await client.post(
        "/api/v1/admin/task-streams",
        headers=headers,
        json={"name": "Archive me"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["id"]

    task_resp = await client.post(
        "/api/v1/admin/tasks",
        headers=headers,
        json={"title": "Move target", "priority": "medium"},
    )
    assert task_resp.status_code == 201, task_resp.text
    tid = task_resp.json()["id"]

    await client.patch(
        f"/api/v1/admin/task-streams/{sid}",
        headers=headers,
        json={"is_archived": True},
    )

    move = await client.patch(
        f"/api/v1/admin/tasks/{tid}",
        headers=headers,
        json={"stream_id": sid},
    )
    assert move.status_code == 422, move.text
    assert move.json().get("detail", {}).get("code") == "STREAM_INVALID"


@pytest.mark.asyncio
async def test_doctor_can_list_streams_and_get_task_list_filter_errors(client, doctor_auth):
    headers = _auth_headers(doctor_auth["access_token"])
    streams = await client.get("/api/v1/admin/task-streams", headers=headers)
    assert streams.status_code == 200, streams.text

    bad_stream = str(uuid.uuid4())
    tasks = await client.get(f"/api/v1/admin/tasks?stream_id={bad_stream}", headers=headers)
    assert tasks.status_code == 400, tasks.text
    assert tasks.json().get("detail", {}).get("code") == "STREAM_NOT_IN_CLINIC"
