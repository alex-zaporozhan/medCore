"""Public API: feed and stories for PWA/patient app."""

from uuid import UUID
from src.core.datetime_utils import to_iso8601_utc, utc_now_naive

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.domain.entities.promo_post import PromoPost
from src.domain.entities.story import Story

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
