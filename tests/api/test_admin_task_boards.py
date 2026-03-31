"""Task board API (Kanban column layout)."""

import pytest


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_task_boards_list_ensures_default_clinic_board(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    r = await client.get("/api/v1/admin/task-boards", headers=headers)
    assert r.status_code == 200, r.text
    boards = r.json()
    assert isinstance(boards, list)
    assert len(boards) >= 1
    clinic_wide = [b for b in boards if b.get("kind") == "clinic_wide"]
    assert len(clinic_wide) >= 1
    cols = clinic_wide[0]["columns"]
    mapped = {c["mapped_status"] for c in cols}
    assert mapped == {"open", "in_progress", "on_hold", "review", "done", "cancelled"}


@pytest.mark.asyncio
async def test_task_boards_replace_columns_requires_full_status_set(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])
    r = await client.get("/api/v1/admin/task-boards", headers=headers)
    board_id = next(b["id"] for b in r.json() if b["kind"] == "clinic_wide")
    bad = await client.put(
        f"/api/v1/admin/task-boards/{board_id}/columns",
        headers=headers,
        json={
            "columns": [
                {"mapped_status": "open", "label": None},
                {"mapped_status": "in_progress", "label": None},
            ]
        },
    )
    assert bad.status_code == 422, bad.text
    assert bad.json().get("detail", {}).get("code") == "INVALID_COLUMN_SET"
