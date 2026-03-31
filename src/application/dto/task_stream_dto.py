"""DTOs for task streams (semantic context) and tag definitions."""

from __future__ import annotations

import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

MantineColorOpt = Literal[
    "gray",
    "red",
    "pink",
    "grape",
    "violet",
    "indigo",
    "blue",
    "cyan",
    "teal",
    "green",
    "lime",
    "yellow",
    "orange",
]

PageTintOpt = Literal[
    "none",
    "subtle_gray",
    "subtle_violet",
    "subtle_blue",
    "subtle_green",
    "subtle_amber",
]


class TaskStreamTheme(BaseModel):
    """Allowed UI presets only — no arbitrary CSS."""

    mantine_color: MantineColorOpt = "blue"
    page_tint: PageTintOpt = "none"

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "mantine_color": self.mantine_color,
            "page_tint": self.page_tint,
        }

    @classmethod
    def from_json_dict(cls, raw: dict[str, Any] | None) -> TaskStreamTheme:
        if not raw:
            return cls()
        try:
            return cls.model_validate(raw)
        except Exception:
            return cls()


def slugify_stream_slug(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:64] if s else "stream"


class TaskStreamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str | None = Field(None, max_length=64)
    theme: TaskStreamTheme | None = None


class TaskStreamPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    theme: TaskStreamTheme | None = None
    is_archived: bool | None = None


class TaskStreamResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    slug: str
    sort_order: int
    is_archived: bool
    theme: dict[str, Any]

    model_config = {"from_attributes": True}


class TaskTagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str | None = Field(None, max_length=32)


class TaskTagPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    color: str | None = Field(None, max_length=32)


class TaskTagResponse(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    color: str | None

    model_config = {"from_attributes": True}
