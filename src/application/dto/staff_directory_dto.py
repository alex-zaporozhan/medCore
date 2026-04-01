"""Staff directory DTOs (profession categories, admin rows)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class StaffProfessionCategoryRead(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    sort_order: int
    default_role_codes: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("id", "clinic_id")
    def _uuid_str(self, v: UUID) -> str:
        return str(v)


class StaffProfessionCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sort_order: int = Field(0, ge=0, le=1_000_000)
    default_role_codes: list[str] = Field(..., min_length=1, max_length=32)


class StaffProfessionCategoryPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=255)
    sort_order: int | None = Field(None, ge=0, le=1_000_000)
    default_role_codes: list[str] | None = Field(None, min_length=1, max_length=32)


class StaffDirectoryAdminRead(BaseModel):
    id: str
    clinic_id: str
    email: str
    full_name: str | None
    birth_date: str | None
    employment_status: str
    profession_category_id: str | None
    profession_category_name: str | None
    bio: str | None = None
    avatar_url: str | None = None