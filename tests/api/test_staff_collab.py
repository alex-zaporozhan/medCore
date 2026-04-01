"""P1 staff collaboration API: RBAC, membership, routing."""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.config import settings
from src.main import app


@pytest.fixture(scope="module", autouse=True)
def ensure_test_db_engine():
    from src.infrastructure.database import base as db_base

    if getattr(db_base, "init_engine_for_testing", None):
        db_base.init_engine_for_testing()


@pytest.mark.asyncio
async def test_staff_chat_rooms_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/staff/chat/rooms")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_staff_feed_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/staff/feed/posts")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_staff_chat_rooms_lists_general_for_member(
    client: AsyncClient, admin_auth: dict
) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    resp = await client.get("/api/v1/admin/staff/chat/rooms", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert any(r.get("kind") == "GENERAL" for r in data)


@pytest.mark.asyncio
async def test_staff_chat_messages_unknown_room_404(client: AsyncClient, admin_auth: dict) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    fake = str(uuid.UUID("00000000-0000-0000-0000-000000000042"))
    resp = await client.get(f"/api/v1/admin/staff/chat/rooms/{fake}/messages", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_staff_chat_attachment_unknown_404(client: AsyncClient, admin_auth: dict) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    fake = str(uuid.UUID("00000000-0000-0000-0000-000000000043"))
    resp = await client.get(f"/api/v1/admin/staff/attachments/{fake}/file", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_staff_calendar_events_list_ok(client: AsyncClient, admin_auth: dict) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    now = datetime.now(timezone.utc)
    frm = (now - timedelta(days=1)).isoformat()
    to = (now + timedelta(days=7)).isoformat()
    resp = await client.get(
        "/api/v1/admin/staff/calendar/events",
        params={"from": frm, "to": to},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_staff_feed_list_skips_missing_attachment_file(client: AsyncClient, admin_auth: dict) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    create = await client.post(
        "/api/v1/admin/staff/feed/posts",
        json={"title": "Attachment resilience", "body": "Body"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]

    files = {"file": ("sample.jpg", b"fake-image-bytes", "image/jpeg")}
    upload = await client.post(
        f"/api/v1/admin/staff/feed/posts/{post_id}/attachments",
        files=files,
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    att = upload.json()
    att_id = att["id"]
    rel = f"feed_posts/{admin_auth['clinic_id']}/{att_id}_sample.jpg"
    path = Path(settings.staff_chat_upload_root) / rel.replace("/", "\\")
    if not path.exists():
        # Cross-platform fallback for non-Windows path separator in tests.
        path = Path(settings.staff_chat_upload_root) / rel
    assert path.is_file()

    # Simulate lost file after infra restart/recreate.
    path.unlink()
    assert not path.exists()

    listed = await client.get("/api/v1/admin/staff/feed/posts", headers=headers)
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    row = next((r for r in rows if r["id"] == post_id), None)
    assert row is not None
    # Broken attachment is suppressed from API list, so UI won't show dead hyperlink.
    assert row["attachments"] == []


@pytest.mark.asyncio
async def test_staff_feed_liked_by_me_and_comment_reply(client: AsyncClient, admin_auth: dict) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    create = await client.post(
        "/api/v1/admin/staff/feed/posts",
        json={"title": "Social", "body": "Тест ленты"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]
    assert create.json().get("liked_by_me") is False
    assert create.json().get("likes_count") == 0

    listed_before = await client.get("/api/v1/admin/staff/feed/posts", headers=headers)
    assert listed_before.status_code == 200, listed_before.text
    row0 = next(r for r in listed_before.json() if r["id"] == post_id)
    assert row0.get("liked_by_me") is False

    like = await client.post(f"/api/v1/admin/staff/feed/posts/{post_id}/like", headers=headers)
    assert like.status_code == 200, like.text
    assert like.json()["liked"] is True

    listed_after = await client.get("/api/v1/admin/staff/feed/posts", headers=headers)
    row1 = next(r for r in listed_after.json() if r["id"] == post_id)
    assert row1.get("liked_by_me") is True

    c1 = await client.post(
        f"/api/v1/admin/staff/feed/posts/{post_id}/comments",
        json={"body": "Первый комментарий"},
        headers=headers,
    )
    assert c1.status_code == 201, c1.text
    parent_id = c1.json()["id"]

    c2 = await client.post(
        f"/api/v1/admin/staff/feed/posts/{post_id}/comments",
        json={"body": "Согласен", "parent_comment_id": parent_id},
        headers=headers,
    )
    assert c2.status_code == 201, c2.text
    assert c2.json()["parent_comment_id"] == parent_id
    assert c2.json().get("in_reply_to") is not None

    listed_comments = await client.get(
        f"/api/v1/admin/staff/feed/posts/{post_id}/comments", headers=headers
    )
    assert listed_comments.status_code == 200, listed_comments.text
    replies = [x for x in listed_comments.json() if x.get("parent_comment_id")]
    assert len(replies) == 1
    assert replies[0]["body"] == "Согласен"
    assert replies[0]["in_reply_to"]["id"] == admin_auth["admin_id"]


@pytest.mark.asyncio
async def test_staff_feed_comment_attachment_empty_body_ok(client: AsyncClient, admin_auth: dict) -> None:
    """Комментарий без текста + загрузка вложения отдельным multipart (как в UI ленты)."""
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    create = await client.post(
        "/api/v1/admin/staff/feed/posts",
        json={"title": "Вложения к комментарию", "body": "Пост"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]

    c = await client.post(
        f"/api/v1/admin/staff/feed/posts/{post_id}/comments",
        json={"body": ""},
        headers=headers,
    )
    assert c.status_code == 201, c.text
    comment_id = c.json()["id"]

    files = {"file": ("snap.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/jpeg")}
    up = await client.post(
        f"/api/v1/admin/staff/feed/comments/{comment_id}/attachments",
        files=files,
        headers=headers,
    )
    assert up.status_code == 201, up.text
    att = up.json()
    assert att.get("file_name")

    listed = await client.get(
        f"/api/v1/admin/staff/feed/posts/{post_id}/comments",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    row = next(r for r in rows if r["id"] == comment_id)
    assert len(row.get("attachments") or []) >= 1


@pytest.mark.asyncio
async def test_staff_feed_comment_invalid_parent_400(client: AsyncClient, admin_auth: dict) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    create = await client.post(
        "/api/v1/admin/staff/feed/posts",
        json={"body": "Пост"},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]
    fake_parent = str(uuid.uuid4())
    bad = await client.post(
        f"/api/v1/admin/staff/feed/posts/{post_id}/comments",
        json={"body": "Нет такого родителя", "parent_comment_id": fake_parent},
        headers=headers,
    )
    assert bad.status_code == 400, bad.text


@pytest.mark.asyncio
async def test_staff_feed_comment_edit_and_soft_delete_owner_only_visibility(
    client: AsyncClient, admin_auth: dict, doctor_auth: dict
) -> None:
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    doctor_headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}

    create = await client.post(
        "/api/v1/admin/staff/feed/posts",
        json={"title": "Soft delete comments", "body": "Post"},
        headers=owner_headers,
    )
    assert create.status_code == 201, create.text
    post_id = create.json()["id"]

    c1 = await client.post(
        f"/api/v1/admin/staff/feed/posts/{post_id}/comments",
        json={"body": "hello"},
        headers=owner_headers,
    )
    assert c1.status_code == 201, c1.text
    comment_id = c1.json()["id"]

    # Author can edit
    upd = await client.patch(
        f"/api/v1/admin/staff/feed/comments/{comment_id}",
        json={"body": "hello edited"},
        headers=owner_headers,
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["body"] == "hello edited"

    # Non-author can't edit or delete
    upd2 = await client.patch(
        f"/api/v1/admin/staff/feed/comments/{comment_id}",
        json={"body": "hijack"},
        headers=doctor_headers,
    )
    assert upd2.status_code == 404

    del2 = await client.delete(
        f"/api/v1/admin/staff/feed/comments/{comment_id}",
        headers=doctor_headers,
    )
    assert del2.status_code == 404

    # Author deletes (soft)
    d1 = await client.delete(
        f"/api/v1/admin/staff/feed/comments/{comment_id}",
        headers=owner_headers,
    )
    assert d1.status_code == 204, d1.text

    # Owner sees deleted comments with deleted_at
    listed_owner = await client.get(
        f"/api/v1/admin/staff/feed/posts/{post_id}/comments",
        headers=owner_headers,
    )
    assert listed_owner.status_code == 200, listed_owner.text
    rows_owner = listed_owner.json()
    row = next(r for r in rows_owner if r["id"] == comment_id)
    assert row.get("deleted_at") is not None

    # Doctor doesn't see deleted comments at all
    listed_doctor = await client.get(
        f"/api/v1/admin/staff/feed/posts/{post_id}/comments",
        headers=doctor_headers,
    )
    assert listed_doctor.status_code == 200, listed_doctor.text
    assert all(r["id"] != comment_id for r in listed_doctor.json())

    # Editing deleted comment is rejected
    upd3 = await client.patch(
        f"/api/v1/admin/staff/feed/comments/{comment_id}",
        json={"body": "try edit after delete"},
        headers=owner_headers,
    )
    assert upd3.status_code == 409


@pytest.mark.asyncio
async def test_staff_announcement_publish_policy_denies_doctor(
    client: AsyncClient, admin_auth: dict, doctor_auth: dict
) -> None:
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    doctor_headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}

    put = await client.put(
        "/api/v1/admin/staff/feed/announcements/publish-policy",
        json=[{"scope_type": "role", "scope_value": "doctor", "can_publish": False}],
        headers=owner_headers,
    )
    assert put.status_code == 200, put.text

    # Doctor can still post a normal wall post
    normal = await client.post(
        "/api/v1/admin/staff/feed/posts",
        json={"title": "Normal", "body": "ok", "is_announcement": False},
        headers=doctor_headers,
    )
    assert normal.status_code == 201, normal.text

    # Doctor is denied from announcements
    ann = await client.post(
        "/api/v1/admin/staff/feed/posts",
        json={"title": "Ann", "body": "no", "is_announcement": True},
        headers=doctor_headers,
    )
    assert ann.status_code == 403, ann.text

    # Announcements list endpoint exists and is separate from feed/posts
    ann_list = await client.get("/api/v1/admin/staff/feed/announcements", headers=owner_headers)
    assert ann_list.status_code == 200, ann_list.text
    assert isinstance(ann_list.json(), list)


@pytest.mark.asyncio
async def test_staff_feed_posts_excludes_announcements_by_default(
    client: AsyncClient, admin_auth: dict
) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    a = await client.post(
        "/api/v1/admin/staff/feed/posts",
        json={"title": "Announcement", "body": "A", "is_announcement": True},
        headers=headers,
    )
    assert a.status_code == 201, a.text

    f = await client.get("/api/v1/admin/staff/feed/posts", headers=headers)
    assert f.status_code == 200, f.text
    assert all(not r.get("is_announcement") for r in f.json())

    ann = await client.get("/api/v1/admin/staff/feed/announcements", headers=headers)
    assert ann.status_code == 200, ann.text
    assert any(r.get("is_announcement") for r in ann.json())


@pytest.mark.asyncio
async def test_staff_announcement_policy_audit_access_owner_vs_granted(
    client: AsyncClient, admin_auth: dict, doctor_auth: dict, seed_data: dict
) -> None:
    owner_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    doctor_headers = {"Authorization": f"Bearer {doctor_auth['access_token']}"}

    # Trigger an audit row by saving publish-policy once.
    put = await client.put(
        "/api/v1/admin/staff/feed/announcements/publish-policy",
        json=[{"scope_type": "role", "scope_value": "doctor", "can_publish": False}],
        headers=owner_headers,
    )
    assert put.status_code == 200, put.text

    # Doctor cannot see audit by default.
    a0 = await client.get(
        "/api/v1/admin/staff/feed/announcements/publish-policy/audit?limit=50",
        headers=doctor_headers,
    )
    assert a0.status_code == 403

    # Owner grants the view permission to doctor individually via RBAC management API.
    patch = await client.patch(
        f"/api/v1/admin/rbac/users/{seed_data['doctor_admin_id']}/permissions",
        json={"overrides": [{"permission_code": "staff.announcements.policy.audit.view", "effect": "grant"}]},
        headers=owner_headers,
    )
    assert patch.status_code == 200, patch.text

    # Doctor can now see audit list.
    a1 = await client.get(
        "/api/v1/admin/staff/feed/announcements/publish-policy/audit?limit=50",
        headers=doctor_headers,
    )
    assert a1.status_code == 200, a1.text
    data = a1.json()
    assert isinstance(data.get("items"), list)
    assert len(data["items"]) >= 1
