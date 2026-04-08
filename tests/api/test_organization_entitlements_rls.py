"""1a-E5: PostgreSQL RLS on organization_entitlements (GUC-gated; default bypass)."""

import uuid

import pytest
from sqlalchemy import select, text

from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_organization_entitlements_rls_filters_when_enforced(init_db):
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    async with db_base.AsyncSessionLocal() as session:
        session.add(Organization(id=org_a, name="RLS Org A"))
        session.add(Organization(id=org_b, name="RLS Org B"))
        session.add(
            OrganizationEntitlement(
                organization_id=org_a,
                entitlement_key="core.base",
            )
        )
        session.add(
            OrganizationEntitlement(
                organization_id=org_b,
                entitlement_key="tasks.kanban",
            )
        )
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        res = await session.execute(select(OrganizationEntitlement))
        all_rows = list(res.scalars().all())
        assert len(all_rows) >= 2

    async with db_base.AsyncSessionLocal() as session:
        await session.execute(text("SET LOCAL app.rls_org_entitlements = 'on'"))
        await session.execute(text(f"SET LOCAL app.effective_organization_id = '{org_a}'"))
        res2 = await session.execute(select(OrganizationEntitlement))
        visible = list(res2.scalars().all())
        assert all(r.organization_id == org_a for r in visible)
        keys = {r.entitlement_key for r in visible}
        assert "core.base" in keys
        assert "tasks.kanban" not in keys
