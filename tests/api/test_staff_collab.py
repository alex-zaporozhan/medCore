"""P1 staff collaboration API: RBAC, membership, routing."""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient

from src.core.config import settings
from src.main import app


@pytest.fixture(scope="module", autouse=True)
def ensure_test_db_engine():
    from src.infrastructure.database import base as db_base

    if getattr(db_base, "init_engine_for_testing", None):
        db_base.init_engine_for_testing()


@pytest.mark.asyncio
async def test_staff_chat_rooms_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/staff/chat/rooms")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_staff_feed_requires_auth():
    async with AsyncClient(app=app, base_url="http://test") as client:
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
