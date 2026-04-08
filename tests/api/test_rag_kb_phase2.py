"""§24.3 RAG KB phase 2: quota, audit trail, FTS search mode (Postgres + migration)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select

from src.core.config import settings
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement
from src.domain.entities.organization_rag_kb_audit_log import OrganizationRagKbAuditLog


def _set_quota(n: int) -> int:
    prev = settings.rag_kb_quota_max_documents_per_org
    object.__setattr__(settings, "rag_kb_quota_max_documents_per_org", n)
    return prev


def _set_search_mode(mode: str) -> str:
    prev = settings.rag_kb_search_mode
    object.__setattr__(settings, "rag_kb_search_mode", mode)
    return prev


@pytest.mark.asyncio
async def test_admin_rag_kb_quota_blocks_second_document(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="RAG quota org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin_id = admin.id
    admin.organization_id = org_id
    for key in ("core.base", "omni.embed.bundle", "ai.rag.org_kb"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()
    prev_q = _set_quota(1)
    try:
        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
        r1 = await client.post(
            "/api/v1/admin/organization/rag-kb/documents",
            headers=headers,
            json={"title": "First", "body": "alpha"},
        )
        assert r1.status_code == 201, r1.text
        r2 = await client.post(
            "/api/v1/admin/organization/rag-kb/documents",
            headers=headers,
            json={"title": "Second", "body": "beta"},
        )
        assert r2.status_code == 409, r2.text
        assert r2.json().get("code") == "rag_kb_quota_exceeded"
    finally:
        object.__setattr__(settings, "rag_kb_quota_max_documents_per_org", prev_q)
        adm = await db_session.get(AdminUser, admin_id)
        if adm is not None:
            adm.organization_id = None
        from src.domain.entities.organization_rag_kb_document import OrganizationRagKbDocument

        await db_session.execute(
            delete(OrganizationRagKbAuditLog).where(OrganizationRagKbAuditLog.organization_id == org_id)
        )
        await db_session.execute(
            delete(OrganizationRagKbDocument).where(OrganizationRagKbDocument.organization_id == org_id)
        )
        await db_session.execute(
            delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == org_id)
        )
        await db_session.execute(delete(Organization).where(Organization.id == org_id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_admin_rag_kb_create_writes_audit_row(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="RAG audit org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin_id = admin.id
    admin.organization_id = org_id
    for key in ("core.base", "omni.embed.bundle", "ai.rag.org_kb"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()

    try:
        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
        r = await client.post(
            "/api/v1/admin/organization/rag-kb/documents",
            headers=headers,
            json={"title": "Audited", "body": "audit marker body"},
        )
        assert r.status_code == 201, r.text
        doc_id = uuid.UUID(r.json()["id"])
        cnt = await db_session.scalar(
            select(func.count())
            .select_from(OrganizationRagKbAuditLog)
            .where(
                OrganizationRagKbAuditLog.organization_id == org_id,
                OrganizationRagKbAuditLog.action == "rag_kb_document_created",
                OrganizationRagKbAuditLog.document_id == doc_id,
            )
        )
        assert int(cnt or 0) >= 1
    finally:
        adm = await db_session.get(AdminUser, admin_id)
        if adm is not None:
            adm.organization_id = None
        from src.domain.entities.organization_rag_kb_document import OrganizationRagKbDocument

        await db_session.execute(
            delete(OrganizationRagKbAuditLog).where(OrganizationRagKbAuditLog.organization_id == org_id)
        )
        await db_session.execute(
            delete(OrganizationRagKbDocument).where(OrganizationRagKbDocument.organization_id == org_id)
        )
        await db_session.execute(
            delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == org_id)
        )
        await db_session.execute(delete(Organization).where(Organization.id == org_id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_public_embed_rag_fts_mode_finds_document(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    """Требует миграцию `search_tsv` (20260425_rag_kb_audit_fts)."""
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="RAG fts org"))
    await db_session.flush()
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_id,
            entitlement_key="core.base",
            source="test",
        )
    )
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin_id = admin.id
    admin.organization_id = org_id
    for key in ("omni.embed.bundle", "ai.rag.org_kb"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()
    prev_m = _set_search_mode("fts")
    try:
        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
        r_doc = await client.post(
            "/api/v1/admin/organization/rag-kb/documents",
            headers=headers,
            json={"title": "FTS title", "body": "UNIQUE_TOKEN_FTS_RAG_PHASE2_X7"},
        )
        assert r_doc.status_code == 201, r_doc.text
        r_key = await client.post(
            "/api/v1/admin/organization/embed/api-keys",
            headers=headers,
            json={"label": "fts-rag"},
        )
        assert r_key.status_code == 200, r_key.text
        token = r_key.json()["token"]
        r_search = await client.post(
            "/api/v1/public/embed/v1/rag/search",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "UNIQUE_TOKEN_FTS"},
        )
        assert r_search.status_code == 200, r_search.text
        blob = " ".join(
            f"{i.get('title', '')} {i.get('snippet', '')}"
            for i in (r_search.json().get("items") or [])
        )
        assert "UNIQUE_TOKEN_FTS_RAG_PHASE2_X7" in blob
    finally:
        object.__setattr__(settings, "rag_kb_search_mode", prev_m)
        adm = await db_session.get(AdminUser, admin_id)
        if adm is not None:
            adm.organization_id = None
        from src.domain.entities.organization_rag_kb_document import OrganizationRagKbDocument

        await db_session.execute(
            delete(OrganizationRagKbAuditLog).where(OrganizationRagKbAuditLog.organization_id == org_id)
        )
        await db_session.execute(
            delete(OrganizationRagKbDocument).where(OrganizationRagKbDocument.organization_id == org_id)
        )
        await db_session.execute(
            delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == org_id)
        )
        await db_session.execute(delete(Organization).where(Organization.id == org_id))
        await db_session.commit()
