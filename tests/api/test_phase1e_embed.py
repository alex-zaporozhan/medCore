"""Phase 1e: embed API keys, public session, webhook inbox (SaaS §24)."""

from __future__ import annotations

import hashlib
import hmac
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from src.domain.entities.admin_user import AdminUser
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement
from src.core import config as app_config
from src.core.config import settings
from src.core.edition import is_box_edition
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter
from src.main import app


@pytest.fixture(autouse=True)
async def _restore_seed_admin_after_embed_case(db_session, seed_data):
    yield
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one_or_none()
    if admin is None:
        return
    oid = admin.organization_id
    admin.organization_id = None
    if oid is not None:
        await db_session.execute(
            delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == oid)
        )
        await db_session.execute(delete(Organization).where(Organization.id == oid))
    await db_session.commit()


def _api_error_code(payload: dict) -> str | None:
    """main.py нормализует `code` на верхний уровень JSON."""
    c = payload.get("code")
    if c is not None:
        return str(c).lower()
    d = payload.get("detail")
    if isinstance(d, dict):
        c2 = d.get("code")
        if c2 is not None:
            return str(c2).lower()
    return None


@pytest.mark.asyncio
async def test_public_embed_health(client: AsyncClient) -> None:
    r = await client.get("/api/v1/public/embed/v1/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


@pytest.mark.asyncio
async def test_public_embed_health_rate_limited_by_ip(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PRC-C1 / матрица: embed public IP bucket → 429 (см. PUBLIC_PERIMETER_RATE_LIMIT_MATRIX.md)."""
    monkeypatch.setattr(settings, "rate_embed_public_ip_limit", 2)
    monkeypatch.setattr(settings, "rate_embed_public_ip_window_seconds", 600)

    class _CountingRl:
        def __init__(self) -> None:
            self.n = 0

        async def check_or_raise(self, key: str, limit: int, window: int) -> None:
            self.n += 1
            if self.n > 2:
                raise RateLimitExceeded(key=key, limit=limit, window=window)

    rl = _CountingRl()

    async def _fake_dep():
        return rl

    app.dependency_overrides[get_rate_limiter] = _fake_dep
    try:
        path = "/api/v1/public/embed/v1/health"
        assert (await client.get(path)).status_code == 200
        assert (await client.get(path)).status_code == 200
        r3 = await client.get(path)
        assert r3.status_code == 429
        assert _api_error_code(r3.json()) == "rate_limited"
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)


@pytest.mark.asyncio
async def test_public_embed_session_401_without_bearer(client: AsyncClient) -> None:
    r = await client.get("/api/v1/public/embed/v1/session")
    assert r.status_code == 401
    assert _api_error_code(r.json()) == "embed_auth_required"


@pytest.mark.asyncio
async def test_admin_embed_403_when_enforced_without_bundle(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Embed gate org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_id,
            entitlement_key="core.base",
            source="tariff_snapshot",
        )
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/organization/embed/settings", headers=headers)
    assert r.status_code == 403, r.text
    assert _api_error_code(r.json()) == "entitlement_required"


@pytest.mark.asyncio
async def test_embed_api_key_and_public_session_and_webhook(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Embed full org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    for key in ("core.base", "omni.embed.bundle"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="tariff_snapshot",
            )
        )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    r_settings = await client.get("/api/v1/admin/organization/embed/settings", headers=headers)
    assert r_settings.status_code == 200, r_settings.text
    route_token = r_settings.json()["inbound_route_token"]

    r_create = await client.post(
        "/api/v1/admin/organization/embed/api-keys",
        headers=headers,
        json={"label": "e2e"},
    )
    assert r_create.status_code == 200, r_create.text
    token = r_create.json()["token"]
    assert token.startswith("dceb.")

    r_sess = await client.get(
        "/api/v1/public/embed/v1/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_sess.status_code == 200, r_sess.text
    body = r_sess.json()
    assert body.get("organization_id") == str(org_id)

    r_wh = await client.post(
        "/api/v1/admin/organization/embed/webhook-secret/rotate",
        headers=headers,
    )
    assert r_wh.status_code == 200, r_wh.text
    wh_secret = r_wh.json()["webhook_secret"]

    r_inbox = await client.post(
        f"/api/v1/public/embed/v1/hooks/{route_token}/inbox",
        headers={"Authorization": f"Bearer {wh_secret}"},
        json={"event": "ping"},
    )
    assert r_inbox.status_code == 200, r_inbox.text
    inbox = r_inbox.json()
    assert inbox.get("received") is True
    assert inbox.get("duplicate") is False


@pytest.mark.asyncio
async def test_embed_webhook_idempotency_duplicate_and_conflict(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Embed idem org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    for key in ("core.base", "omni.embed.bundle"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="tariff_snapshot",
            )
        )
    await db_session.commit()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r_settings = await client.get("/api/v1/admin/organization/embed/settings", headers=headers)
    route_token = r_settings.json()["inbound_route_token"]
    r_wh = await client.post(
        "/api/v1/admin/organization/embed/webhook-secret/rotate",
        headers=headers,
    )
    wh_secret = r_wh.json()["webhook_secret"]
    url = f"/api/v1/public/embed/v1/hooks/{route_token}/inbox"
    auth_h = {"Authorization": f"Bearer {wh_secret}", "X-Embed-Idempotency-Key": "idem-1"}

    r1 = await client.post(url, headers=auth_h, json={"n": 1})
    assert r1.status_code == 200, r1.text
    j1 = r1.json()
    assert j1.get("idempotency_recorded") is True
    assert j1.get("duplicate") is False

    r2 = await client.post(url, headers=auth_h, json={"n": 1})
    assert r2.status_code == 200, r2.text
    j2 = r2.json()
    assert j2.get("duplicate") is True
    assert j2.get("idempotency_recorded") is False

    r3 = await client.post(url, headers=auth_h, json={"n": 2})
    assert r3.status_code == 409, r3.text
    assert _api_error_code(r3.json()) == "embed_webhook_idempotency_conflict"


@pytest.mark.asyncio
async def test_embed_webhook_hmac_optional_valid_and_invalid(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Embed hmac org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    for key in ("core.base", "omni.embed.bundle"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="tariff_snapshot",
            )
        )
    await db_session.commit()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r_settings = await client.get("/api/v1/admin/organization/embed/settings", headers=headers)
    route_token = r_settings.json()["inbound_route_token"]
    r_wh = await client.post(
        "/api/v1/admin/organization/embed/webhook-secret/rotate",
        headers=headers,
    )
    wh_secret = r_wh.json()["webhook_secret"]
    url = f"/api/v1/public/embed/v1/hooks/{route_token}/inbox"
    raw = b'{"hmac":true}'
    good = hmac.new(wh_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()

    r_ok = await client.post(
        url,
        headers={
            "Authorization": f"Bearer {wh_secret}",
            "Content-Type": "application/json",
            "X-Embed-Signature": f"v1={good}",
        },
        content=raw,
    )
    assert r_ok.status_code == 200, r_ok.text

    r_bad = await client.post(
        url,
        headers={
            "Authorization": f"Bearer {wh_secret}",
            "Content-Type": "application/json",
            "X-Embed-Signature": "v1=" + "0" * 64,
        },
        content=raw,
    )
    assert r_bad.status_code == 401, r_bad.text
    assert _api_error_code(r_bad.json()) == "embed_webhook_signature_invalid"


@pytest.mark.asyncio
async def test_embed_webhook_404_when_secret_not_rotated(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Embed webhook no secret"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    for key in ("core.base", "omni.embed.bundle"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="tariff_snapshot",
            )
        )
    await db_session.commit()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r_settings = await client.get("/api/v1/admin/organization/embed/settings", headers=headers)
    route_token = r_settings.json()["inbound_route_token"]

    r_inbox = await client.post(
        f"/api/v1/public/embed/v1/hooks/{route_token}/inbox",
        headers={"Authorization": "Bearer anything"},
        json={},
    )
    assert r_inbox.status_code == 404, r_inbox.text
    assert _api_error_code(r_inbox.json()) == "embed_webhook_not_configured"


@pytest.mark.asyncio
async def test_embed_webhook_413_payload_too_large(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    monkeypatch.setattr(app_config.settings, "embed_webhook_max_body_bytes", 32)
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Embed payload org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    for key in ("core.base", "omni.embed.bundle"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="tariff_snapshot",
            )
        )
    await db_session.commit()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r_settings = await client.get("/api/v1/admin/organization/embed/settings", headers=headers)
    route_token = r_settings.json()["inbound_route_token"]
    r_wh = await client.post(
        "/api/v1/admin/organization/embed/webhook-secret/rotate",
        headers=headers,
    )
    wh_secret = r_wh.json()["webhook_secret"]
    url = f"/api/v1/public/embed/v1/hooks/{route_token}/inbox"
    big = b'{"x":"' + b"y" * 64 + b'"}'
    r = await client.post(
        url,
        headers={"Authorization": f"Bearer {wh_secret}"},
        content=big,
    )
    assert r.status_code == 413, r.text
    assert _api_error_code(r.json()) == "embed_webhook_payload_too_large"


@pytest.mark.asyncio
async def test_admin_embed_revoke_unknown_key_returns_structured_404(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Embed revoke org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    for key in ("core.base", "omni.embed.bundle"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="tariff_snapshot",
            )
        )
    await db_session.commit()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    fake_id = uuid.uuid4()
    r = await client.post(
        f"/api/v1/admin/organization/embed/api-keys/{fake_id}/revoke",
        headers=headers,
    )
    assert r.status_code == 404, r.text
    assert _api_error_code(r.json()) == "embed_api_key_not_found"


@pytest.mark.asyncio
async def test_embed_public_rag_search_requires_bearer(client: AsyncClient) -> None:
    r = await client.post("/api/v1/public/embed/v1/rag/search", json={"query": "ab"})
    assert r.status_code == 401, r.text


@pytest.mark.skipif(
    is_box_edition(),
    reason="Box/basic edition: ensure_org_entitlement_keys_for_public_client не гейтит публичный embed",
)
@pytest.mark.asyncio
async def test_embed_public_rag_search_403_without_rag_entitlement_when_enforced(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    """§24.3: публичный RAG требует ai.rag.org_kb при включённом SaaS-gate по организации."""
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="RAG entitlement gate org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin.organization_id = org_id
    for key in ("core.base", "omni.embed.bundle"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="tariff_snapshot",
            )
        )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r_key = await client.post(
        "/api/v1/admin/organization/embed/api-keys",
        headers=headers,
        json={"label": "rag-ent-gate"},
    )
    assert r_key.status_code == 200, r_key.text
    embed_token = r_key.json()["token"]

    r = await client.post(
        "/api/v1/public/embed/v1/rag/search",
        headers={"Authorization": f"Bearer {embed_token}"},
        json={"query": "ab"},
    )
    assert r.status_code == 403, r.text
    assert _api_error_code(r.json()) == "entitlement_required"


@pytest.mark.asyncio
async def test_embed_public_assistant_requires_bearer(client: AsyncClient) -> None:
    r = await client.post("/api/v1/public/embed/v1/assistant/message", json={"message": "hi"})
    assert r.status_code == 401, r.text
