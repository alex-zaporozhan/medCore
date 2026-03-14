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

