"""Admin marketing API: promo posts and stories."""

import logging
from uuid import UUID
from datetime import datetime

from src.core.datetime_utils import utc_now_naive

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.api.v1.routers.admin_auth import get_current_admin

logger = logging.getLogger(__name__)
from src.application.dto.marketing_dto import (
    PromoPostCreate,
    PromoPostRead,
    PromoPostUpdate,
    StoryCreate,
    StoryRead,
    StoryUpdate,
)
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.promo_post import PromoPost
from src.domain.entities.story import Story

router = APIRouter(prefix="/admin/clinics", tags=["admin-marketing"])


@router.get("/{clinic_id}/marketing/posts", response_model=list[PromoPostRead])
async def list_promo_posts(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(PromoPost).where(PromoPost.clinic_id == clinic_id).order_by(PromoPost.created_at.desc())
    )
    return [PromoPostRead.model_validate(r) for r in result.scalars().all()]


@router.post(
    "/{clinic_id}/marketing/posts",
    response_model=PromoPostRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_promo_post(
    clinic_id: UUID,
    body: PromoPostCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        published_at_val = body.published_at
        if published_at_val is None and body.is_published:
            # Store UTC naive for PostgreSQL TIMESTAMP (promo_posts table)
            published_at_val = utc_now_naive()
        post = PromoPost(
            clinic_id=clinic_id,
            title=body.title,
            body=body.body,
            image_url=body.image_url or None,
            video_url=body.video_url or None,
            additional_image_urls=body.additional_image_urls,
            link=body.link or None,
            is_published=body.is_published,
            published_at=published_at_val,
        )
        session.add(post)
        await session.flush()
        await session.commit()
        await session.refresh(post)
        return PromoPostRead.model_validate(post)
    except Exception as e:  # noqa: BLE001
        logger.exception("create_promo_post failed: clinic_id=%s", clinic_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось создать пост: {e!s}",
        ) from e


@router.get(
    "/{clinic_id}/marketing/posts/{post_id}",
    response_model=PromoPostRead,
)
async def get_promo_post(
    clinic_id: UUID,
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(PromoPost).where(
            PromoPost.id == post_id,
            PromoPost.clinic_id == clinic_id,
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return PromoPostRead.model_validate(post)


@router.put(
    "/{clinic_id}/marketing/posts/{post_id}",
    response_model=PromoPostRead,
)
async def update_promo_post(
    clinic_id: UUID,
    post_id: UUID,
    body: PromoPostUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(PromoPost).where(
            PromoPost.id == post_id,
            PromoPost.clinic_id == clinic_id,
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = body.model_dump(exclude_unset=True)
    if data.get("is_published") and not post.published_at:
        data["published_at"] = utc_now_naive()
    for k, v in data.items():
        setattr(post, k, v)
    await session.flush()
    await session.commit()
    await session.refresh(post)
    return PromoPostRead.model_validate(post)


@router.delete(
    "/{clinic_id}/marketing/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_promo_post(
    clinic_id: UUID,
    post_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(PromoPost).where(
            PromoPost.id == post_id,
            PromoPost.clinic_id == clinic_id,
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(post)
    await session.commit()


# --- Stories ---
@router.get("/{clinic_id}/marketing/stories", response_model=list[StoryRead])
async def list_stories(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(Story).where(Story.clinic_id == clinic_id).order_by(Story.order_index, Story.created_at)
    )
    return [StoryRead.model_validate(r) for r in result.scalars().all()]


@router.post(
    "/{clinic_id}/marketing/stories",
    response_model=StoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_story(
    clinic_id: UUID,
    body: StoryCreate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        story = Story(
            clinic_id=clinic_id,
            media_type=body.media_type,
            media_url=body.media_url,
            caption=body.caption,
            order_index=body.order_index,
            expires_at=body.expires_at,
        )
        session.add(story)
        await session.flush()
        await session.commit()
        await session.refresh(story)
        return StoryRead.model_validate(story)
    except Exception as e:  # noqa: BLE001
        logger.exception("create_story failed: clinic_id=%s", clinic_id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось создать сторис: {e!s}",
        ) from e


@router.get(
    "/{clinic_id}/marketing/stories/{story_id}",
    response_model=StoryRead,
)
async def get_story(
    clinic_id: UUID,
    story_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(Story).where(
            Story.id == story_id,
            Story.clinic_id == clinic_id,
        )
    )
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return StoryRead.model_validate(story)


@router.put(
    "/{clinic_id}/marketing/stories/{story_id}",
    response_model=StoryRead,
)
async def update_story(
    clinic_id: UUID,
    story_id: UUID,
    body: StoryUpdate,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(Story).where(
            Story.id == story_id,
            Story.clinic_id == clinic_id,
        )
    )
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(story, k, v)
    await session.flush()
    await session.commit()
    await session.refresh(story)
    return StoryRead.model_validate(story)


@router.delete(
    "/{clinic_id}/marketing/stories/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_story(
    clinic_id: UUID,
    story_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
):
    if clinic_id != current_admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(Story).where(
            Story.id == story_id,
            Story.clinic_id == clinic_id,
        )
    )
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(story)
    await session.commit()
