"""Tests for admin CRM Kanban API (pipelines, leads, notes)."""

import pytest
from httpx import AsyncClient

from src.infrastructure.database import base as db_base
from src.domain.entities.lead_pipeline import LeadPipeline
from src.domain.entities.lead_stage import LeadStage
from src.domain.entities.lead_card import LeadCard


@pytest.mark.asyncio
async def test_admin_crm_leads_listing_and_details(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    """Admin can list CRM leads, get details and add notes."""

    clinic_id = seed_data["clinic_id"]

    # Prepare one pipeline, stage and lead in DB
    async with db_base.AsyncSessionLocal() as session:
        pipeline = LeadPipeline(
            clinic_id=clinic_id,
            name="Default sales pipeline",
            description="Test pipeline for admin CRM",
            is_default=True,
        )
        session.add(pipeline)
        await session.flush()

        stage = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=1,
            code="new",
            name="Новое обращение",
            probability=10,
            color="blue",
        )
        session.add(stage)
        await session.flush()

        lead = LeadCard(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            stage_id=stage.id,
            omnichannel_contact_id=None,
            patient_id=seed_data["patient_id"],
            primary_booking_id=None,
            title="Test CRM lead",
            source="test",
        )
        session.add(lead)
        await session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # List leads
    r = await client.get("/api/v1/admin/crm/leads", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1

    lead_id = data["items"][0]["id"]

    # Get lead details
    r_detail = await client.get(f"/api/v1/admin/crm/leads/{lead_id}", headers=headers)
    assert r_detail.status_code == 200, r_detail.text
    detail = r_detail.json()
    assert detail["lead"]["id"] == lead_id
    assert isinstance(detail.get("notes"), list)

    # Add a note
    r_note = await client.post(
        f"/api/v1/admin/crm/leads/{lead_id}/notes",
        json={"text": "Note from admin test"},
        headers=headers,
    )
    assert r_note.status_code == 201, r_note.text
    note = r_note.json()
    assert note["lead_id"] == lead_id
    assert note["text"] == "Note from admin test"


@pytest.mark.asyncio
async def test_admin_crm_leads_kanban_projection(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    """Kanban projection returns lighter lead objects (no UTM block)."""
    clinic_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        pipeline = LeadPipeline(
            clinic_id=clinic_id,
            name="P2",
            description=None,
            is_default=True,
        )
        session.add(pipeline)
        await session.flush()
        stage = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=1,
            code="new",
            name="Новое",
            probability=10,
            color="blue",
        )
        session.add(stage)
        await session.flush()
        lead = LeadCard(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            stage_id=stage.id,
            omnichannel_contact_id=None,
            patient_id=seed_data["patient_id"],
            primary_booking_id=None,
            title="Kanban projection lead",
            source="test",
        )
        session.add(lead)
        await session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get("/api/v1/admin/crm/leads", headers=headers, params={"projection": "kanban"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] >= 1
    item = next(x for x in data["items"] if x["title"] == "Kanban projection lead")
    assert "utm_source" not in item
    assert item["id"]
    assert item["stage_id"] == str(stage.id)


@pytest.mark.asyncio
async def test_admin_crm_leads_cursor_pagination(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    """Cursor mode returns next_cursor and second page is consistent."""
    clinic_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        pipeline = LeadPipeline(
            clinic_id=clinic_id,
            name="P-cursor",
            description=None,
            is_default=True,
        )
        session.add(pipeline)
        await session.flush()
        stage = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=1,
            code="new",
            name="Новое",
            probability=10,
            color="blue",
        )
        session.add(stage)
        await session.flush()
        for i in range(3):
            session.add(
                LeadCard(
                    clinic_id=clinic_id,
                    pipeline_id=pipeline.id,
                    stage_id=stage.id,
                    omnichannel_contact_id=None,
                    patient_id=seed_data["patient_id"],
                    primary_booking_id=None,
                    title=f"Cursor lead {i}",
                    source="test",
                )
            )
        await session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r1 = await client.get(
        "/api/v1/admin/crm/leads",
        headers=headers,
        params={
            "projection": "kanban",
            "pagination": "cursor",
            "stage_id": str(stage.id),
            "page_size": 2,
        },
    )
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert len(d1["items"]) == 2
    assert d1.get("next_cursor")
    assert d1.get("total") == 3

    r2 = await client.get(
        "/api/v1/admin/crm/leads",
        headers=headers,
        params={
            "projection": "kanban",
            "pagination": "cursor",
            "stage_id": str(stage.id),
            "page_size": 2,
            "cursor": d1["next_cursor"],
        },
    )
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert len(d2["items"]) == 1
    ids = {x["id"] for x in d1["items"]} | {x["id"] for x in d2["items"]}
    assert len(ids) == 3


@pytest.mark.asyncio
async def test_admin_crm_leads_cursor_invalid_returns_400(
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        "/api/v1/admin/crm/leads",
        headers=headers,
        params={
            "projection": "kanban",
            "pagination": "cursor",
            "stage_id": "00000000-0000-0000-0000-000000000001",
            "cursor": "not-a-valid-cursor",
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_admin_crm_stage_semantics_includes_resolved(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    """GET stage-semantics returns resolved_stage_semantics (mapping + infer)."""
    clinic_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        pipeline = LeadPipeline(
            clinic_id=clinic_id,
            name="P-sem",
            description=None,
            is_default=True,
        )
        session.add(pipeline)
        await session.flush()
        stage_new = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=1,
            code="new",
            name="Новое",
            probability=10,
            color="blue",
        )
        session.add(stage_new)
        await session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        f"/api/v1/admin/crm/pipelines/{pipeline.id}/stage-semantics",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "resolved_stage_semantics" in data
    assert isinstance(data["resolved_stage_semantics"], list)
    row = next(x for x in data["resolved_stage_semantics"] if x["stage_id"] == str(stage_new.id))
    assert row["semantic"] == "start"


@pytest.mark.asyncio
async def test_admin_crm_change_lead_stage_enforce_semantic_blocks_invalid(
    init_db,
    seed_data,
    client: AsyncClient,
    admin_auth: dict,
) -> None:
    """PATCH with enforce_semantic_transition rejects start -> won (invalid)."""
    clinic_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        pipeline = LeadPipeline(
            clinic_id=clinic_id,
            name="P-enf",
            description=None,
            is_default=True,
        )
        session.add(pipeline)
        await session.flush()
        stage_start = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=1,
            code="new",
            name="Новое",
            probability=10,
            color="blue",
        )
        stage_won = LeadStage(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            order=2,
            code="won",
            name="Успех",
            probability=100,
            color="green",
        )
        session.add(stage_start)
        session.add(stage_won)
        await session.flush()
        lead = LeadCard(
            clinic_id=clinic_id,
            pipeline_id=pipeline.id,
            stage_id=stage_start.id,
            omnichannel_contact_id=None,
            patient_id=seed_data["patient_id"],
            primary_booking_id=None,
            title="Enforce semantic lead",
            source="test",
        )
        session.add(lead)
        await session.commit()
        lead_id = lead.id

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.patch(
        f"/api/v1/admin/crm/leads/{lead_id}/stage",
        headers=headers,
        json={
            "new_stage_id": str(stage_won.id),
            "enforce_semantic_transition": True,
        },
    )
    assert r.status_code == 400, r.text
    err = r.json()
    assert err.get("detail", {}).get("code") == "semantic_transition_invalid"

    r_ok = await client.patch(
        f"/api/v1/admin/crm/leads/{lead_id}/stage",
        headers=headers,
        json={
            "new_stage_id": str(stage_won.id),
            "enforce_semantic_transition": False,
        },
    )
    assert r_ok.status_code == 200, r_ok.text
    assert r_ok.json()["stage_id"] == str(stage_won.id)

