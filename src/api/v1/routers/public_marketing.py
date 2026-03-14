"""Public API: feed, stories and landing leads for PWA/patient app."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.dto.marketing_attribution_dto import (
    LandingLeadRequest,
    LandingLeadResponse,
)
from src.application.services.lead_service import LeadService
from src.core.datetime_utils import to_iso8601_utc, utc_now_naive
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.promo_post import PromoPost
from src.domain.entities.story import Story
from src.domain.entities.visit_attribution import VisitAttribution

router = APIRouter(prefix="/public/clinics", tags=["public"])


@router.get("/{clinic_id}/feed")
async def get_public_feed(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Published promo posts for clinic feed (PWA)."""
    now = utc_now_naive()
    result = await session.execute(
        select(PromoPost)
        .where(
            PromoPost.clinic_id == clinic_id,
            PromoPost.is_published.is_(True),
            (PromoPost.published_at.is_(None)) | (PromoPost.published_at <= now),
        )
        .order_by(PromoPost.published_at.desc().nulls_last(), PromoPost.created_at.desc())
    )
    posts = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "clinic_id": str(p.clinic_id),
            "title": p.title,
            "body": p.body,
            "image_url": p.image_url,
            "link": p.link,
            "published_at": to_iso8601_utc(p.published_at) if p.published_at else None,
            "created_at": (to_iso8601_utc(p.created_at) or ""),
        }
        for p in posts
    ]


@router.get("/{clinic_id}/stories")
async def get_public_stories(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Active stories for clinic (not expired). PWA stories strip."""
    now = utc_now_naive()
    result = await session.execute(
        select(Story)
        .where(
            Story.clinic_id == clinic_id,
            (Story.expires_at.is_(None)) | (Story.expires_at > now),
        )
        .order_by(Story.order_index, Story.created_at)
    )
    stories = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "clinic_id": str(s.clinic_id),
            "media_url": s.media_url,
            "caption": s.caption,
            "order_index": s.order_index,
            "expires_at": to_iso8601_utc(s.expires_at) if s.expires_at else None,
            "created_at": to_iso8601_utc(s.created_at) or "",
        }
        for s in stories
    ]


@router.post(
    "/{clinic_id}/leads",
    response_model=LandingLeadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_landing_lead(
    clinic_id: UUID,
    body: LandingLeadRequest,
    session: AsyncSession = Depends(get_session),
) -> LandingLeadResponse:
    """Public landing endpoint: create VisitAttribution + LeadCard from marketing form.
    Idempotent: if session_id is provided and a VisitAttribution with that session_id
    already has a lead, returns existing lead_id and visit_attribution_id.
    """
    if body.session_id:
        existing = await session.execute(
            select(VisitAttribution).where(
                VisitAttribution.clinic_id == clinic_id,
                VisitAttribution.session_id == body.session_id,
                VisitAttribution.lead_id.isnot(None),
            ).limit(1)
        )
        va = existing.scalar_one_or_none()
        if va is not None:
            return LandingLeadResponse(lead_id=va.lead_id, visit_attribution_id=va.id)

    service = LeadService(session)

    visit = VisitAttribution(
        clinic_id=clinic_id,
        patient_id=None,
        lead_id=None,
        traffic_source_id=None,
        campaign_id=None,
        session_id=body.session_id,
        landing_page=body.landing_page,
        anchor=body.anchor,
        utm_source=body.utm_source,
        utm_medium=body.utm_medium,
        utm_campaign=body.utm_campaign,
        utm_content=body.utm_content,
        utm_term=body.utm_term,
    )
    session.add(visit)
    await session.flush()

    title = body.full_name or body.phone
    source = body.utm_source or "landing"

    lead = await service.create_lead_from_contact(
        clinic_id=clinic_id,
        omnichannel_contact_id=None,
        patient_id=None,
        title=title,
        source=source,
        estimated_value=None,
    )

    visit.lead_id = lead.id
    lead.visit_attribution_id = visit.id
    lead.utm_source = visit.utm_source
    lead.utm_medium = visit.utm_medium
    lead.utm_campaign = visit.utm_campaign
    lead.utm_content = visit.utm_content
    lead.utm_term = visit.utm_term

    session.add(visit)
    session.add(lead)
    await session.flush()
    await session.commit()

    return LandingLeadResponse(lead_id=lead.id, visit_attribution_id=visit.id)
