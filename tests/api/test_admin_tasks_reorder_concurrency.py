import asyncio

import pytest


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_tasks_reorder_is_conflict_safe_under_concurrency(client, admin_auth):
    headers = _auth_headers(admin_auth["access_token"])

    created_ids: list[str] = []
    for idx in range(5):
        create_resp = await client.post(
            "/api/v1/admin/tasks",
            headers=headers,
            json={
                "title": f"Concurrent reorder task {idx + 1}",
                "priority": "medium",
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        created_ids.append(create_resp.json()["id"])

    # Make base ordering deterministic before race.
    base_reorder = await client.post(
        "/api/v1/admin/tasks/reorder",
        headers=headers,
        json={"status": "open", "ordered_task_ids": created_ids},
    )
    assert base_reorder.status_code == 200, base_reorder.text

    order_a = list(reversed(created_ids))
    order_b = created_ids[1:] + created_ids[:1]

    resp_a, resp_b = await asyncio.gather(
        client.post(
            "/api/v1/admin/tasks/reorder",
            headers=headers,
            json={"status": "open", "ordered_task_ids": order_a},
        ),
        client.post(
            "/api/v1/admin/tasks/reorder",
            headers=headers,
            json={"status": "open", "ordered_task_ids": order_b},
        ),
    )

    assert resp_a.status_code == 200, resp_a.text
    assert resp_b.status_code == 200, resp_b.text

    list_resp = await client.get(
        "/api/v1/admin/tasks?status=open",
        headers=headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    rows = [r for r in list_resp.json() if r["id"] in created_ids]
    assert len(rows) == len(created_ids)

    # Invariant: ranks in column are unique and contiguous after concurrent reorder.
    ranks = sorted(int(r["rank"]) for r in rows)
    assert ranks == [1, 2, 3, 4, 5]

    sorted_rows = sorted(rows, key=lambda r: int(r["rank"]))
    final_order = [r["id"] for r in sorted_rows]
    assert final_order in (order_a, order_b)
