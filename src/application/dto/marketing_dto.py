"""Marketing DTOs (PromoPost, Story)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PromoPostRead(BaseModel):
    id: UUID
    clinic_id: UUID
    title: str
    body: str
    image_url: str | None = None
    video_url: str | None = None
    additional_image_urls: list[str] | None = None
    link: str | None = None
    is_published: bool
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromoPostCreate(BaseModel):
    title: str = Field(..., max_length=500)
    body: str = Field(..., min_length=1)
    image_url: str | None = Field(None, max_length=1000)
    video_url: str | None = Field(None, max_length=1000)
    additional_image_urls: list[str] | None = None
    link: str | None = Field(None, max_length=1000)
    is_published: bool = False
    published_at: datetime | None = None


class PromoPostUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    body: str | None = None
    image_url: str | None = Field(None, max_length=1000)
    video_url: str | None = Field(None, max_length=1000)
    additional_image_urls: list[str] | None = None
    link: str | None = Field(None, max_length=1000)
    is_published: bool | None = None
    published_at: datetime | None = None


class StoryRead(BaseModel):
    id: UUID
    clinic_id: UUID
    media_type: str = "image"
    media_url: str
    caption: str | None = None
    order_index: int
    expires_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoryCreate(BaseModel):
    media_type: str = Field(default="image", pattern="^(image|video)$")
    media_url: str = Field(..., max_length=1000)
    caption: str | None = Field(None)
    order_index: int = 0
    expires_at: datetime | None = None


class StoryUpdate(BaseModel):
    media_type: str | None = Field(None, pattern="^(image|video)$")
    media_url: str | None = Field(None, max_length=1000)
    caption: str | None = None
    order_index: int | None = None
    expires_at: datetime | None = None
