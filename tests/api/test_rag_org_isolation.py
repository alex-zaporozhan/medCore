"""QA_ARCH §24.3: RAG KB must not leak across organizations (embed public search)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from src.domain.entities.admin_user import AdminUser
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement
from src.domain.entities.organization_rag_kb_document import OrganizationRagKbDocument


@pytest.mark.asyncio
async def test_public_embed_rag_search_no_cross_org_leak(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    db_session.add(Organization(id=org_a, name="RAG isolation org A"))
    db_session.add(Organization(id=org_b, name="RAG isolation org B"))
    await db_session.flush()

    db_session.add(
        OrganizationRagKbDocument(
            id=uuid.uuid4(),
            organization_id=org_a,
            title="Alpha doc",
            body="MARKER_ALPHA_ONLY_ORG_A_XQ9",
        )
    )
    db_session.add(
        OrganizationRagKbDocument(
            id=uuid.uuid4(),
            organization_id=org_b,
            title="Beta doc",
            body="MARKER_BETA_ONLY_ORG_B_YZ7",
        )
    )

    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin_id = admin.id
    admin.organization_id = org_a
    for key in ("core.base", "omni.embed.bundle", "ai.rag.org_kb"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_a,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()

    try:
        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
        r_key = await client.post(
            "/api/v1/admin/organization/embed/api-keys",
            headers=headers,
            json={"label": "rag-isolation-qa"},
        )
        assert r_key.status_code == 200, r_key.text
        embed_token = r_key.json()["token"]

        h_embed = {"Authorization": f"Bearer {embed_token}"}

        r_own = await client.post(
            "/api/v1/public/embed/v1/rag/search",
            headers=h_embed,
            json={"query": "MARKER_ALPHA"},
        )
        assert r_own.status_code == 200, r_own.text
        assert r_own.json().get("organization_id") == str(org_a)
        items_own = r_own.json().get("items") or []
        blob_a = " ".join(
            f"{i.get('title', '')} {i.get('snippet', '')}" for i in items_own
        )
        assert "MARKER_ALPHA_ONLY_ORG_A_XQ9" in blob_a

        r_leak = await client.post(
            "/api/v1/public/embed/v1/rag/search",
            headers=h_embed,
            json={"query": "MARKER_BETA"},
        )
        assert r_leak.status_code == 200, r_leak.text
        assert r_leak.json().get("organization_id") == str(org_a)
        items_b = r_leak.json().get("items") or []
        blob_b = " ".join(
            f"{i.get('title', '')} {i.get('snippet', '')}" for i in items_b
        )
        assert "MARKER_BETA_ONLY_ORG_B_YZ7" not in blob_b
    finally:
        adm = await db_session.get(AdminUser, admin_id)
        if adm is not None:
            adm.organization_id = None
        await db_session.execute(
            delete(OrganizationRagKbDocument).where(
                OrganizationRagKbDocument.organization_id.in_([org_a, org_b])
            )
        )
        await db_session.execute(
            delete(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id.in_([org_a, org_b])
            )
        )
        await db_session.execute(delete(Organization).where(Organization.id.in_([org_a, org_b])))
        await db_session.commit()


@pytest.mark.asyncio
async def test_public_embed_rag_search_treats_percent_as_literal_in_query(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    """Метасимвол `%` в запросе не должен матчить «всё подряд» (ILIKE + ESCAPE)."""
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="RAG ilike org"))
    await db_session.flush()
    db_session.add(
        OrganizationRagKbDocument(
            id=uuid.uuid4(),
            organization_id=org_id,
            title="Акция",
            body="Скидка 50% на профгигиену MARKER_FIFTY_PCT",
        )
    )
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
        r_key = await client.post(
            "/api/v1/admin/organization/embed/api-keys",
            headers=headers,
            json={"label": "rag-ilike-qa"},
        )
        assert r_key.status_code == 200, r_key.text
        embed_token = r_key.json()["token"]
        r = await client.post(
            "/api/v1/public/embed/v1/rag/search",
            headers={"Authorization": f"Bearer {embed_token}"},
            json={"query": "50%"},
        )
        assert r.status_code == 200, r.text
        blob = " ".join(
            f"{i.get('title', '')} {i.get('snippet', '')}"
            for i in (r.json().get("items") or [])
        )
        assert "MARKER_FIFTY_PCT" in blob
    finally:
        adm = await db_session.get(AdminUser, admin_id)
        if adm is not None:
            adm.organization_id = None
        await db_session.execute(
            delete(OrganizationRagKbDocument).where(
                OrganizationRagKbDocument.organization_id == org_id
            )
        )
        await db_session.execute(
            delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == org_id)
        )
        await db_session.execute(delete(Organization).where(Organization.id == org_id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_admin_rag_kb_delete_other_org_document_returns_404(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    """Админ org A не может удалить документ, физически лежащий в org B (§24.3)."""
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    doc_b_id = uuid.uuid4()
    db_session.add(Organization(id=org_a, name="RAG admin A"))
    db_session.add(Organization(id=org_b, name="RAG admin B"))
    await db_session.flush()
    db_session.add(
        OrganizationRagKbDocument(
            id=doc_b_id,
            organization_id=org_b,
            title="Secret B",
            body="ONLY_ORG_B_CONTENT",
        )
    )

    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin_id = admin.id
    admin.organization_id = org_a
    for key in ("core.base", "omni.embed.bundle", "ai.rag.org_kb"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_a,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()

    try:
        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
        r = await client.delete(
            f"/api/v1/admin/organization/rag-kb/documents/{doc_b_id}",
            headers=headers,
        )
        assert r.status_code == 404, r.text
        assert r.json().get("code") == "rag_document_not_found"
    finally:
        adm = await db_session.get(AdminUser, admin_id)
        if adm is not None:
            adm.organization_id = None
        await db_session.execute(
            delete(OrganizationRagKbDocument).where(
                OrganizationRagKbDocument.organization_id.in_([org_a, org_b])
            )
        )
        await db_session.execute(
            delete(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id.in_([org_a, org_b])
            )
        )
        await db_session.execute(delete(Organization).where(Organization.id.in_([org_a, org_b])))
        await db_session.commit()


@pytest.mark.asyncio
async def test_admin_rag_kb_get_other_org_document_returns_404(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    """Чтение по id не пересекает organization_id (§24.3)."""
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    doc_b_id = uuid.uuid4()
    db_session.add(Organization(id=org_a, name="RAG get A"))
    db_session.add(Organization(id=org_b, name="RAG get B"))
    await db_session.flush()
    db_session.add(
        OrganizationRagKbDocument(
            id=doc_b_id,
            organization_id=org_b,
            title="B only",
            body="SECRET_B_GET",
        )
    )

    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    admin_id = admin.id
    admin.organization_id = org_a
    for key in ("core.base", "omni.embed.bundle", "ai.rag.org_kb"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_a,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()

    try:
        headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
        r = await client.get(
            f"/api/v1/admin/organization/rag-kb/documents/{doc_b_id}",
            headers=headers,
        )
        assert r.status_code == 404, r.text
        assert r.json().get("code") == "rag_document_not_found"
    finally:
        adm = await db_session.get(AdminUser, admin_id)
        if adm is not None:
            adm.organization_id = None
        await db_session.execute(
            delete(OrganizationRagKbDocument).where(
                OrganizationRagKbDocument.organization_id.in_([org_a, org_b])
            )
        )
        await db_session.execute(
            delete(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id.in_([org_a, org_b])
            )
        )
        await db_session.execute(delete(Organization).where(Organization.id.in_([org_a, org_b])))
        await db_session.commit()
