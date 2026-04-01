"""DTOs for owner RBAC control center."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RbacPermissionRead(BaseModel):
    id: UUID
    code: str
    description: str | None = None
    domain: str


class RbacRoleRead(BaseModel):
    id: UUID
    code: str
    name: str
    clinic_id: UUID | None = None
    permission_codes: list[str] = Field(default_factory=list)


class RbacRolePresetRead(BaseModel):
    """Named permission bundle from rbac_matrix (for UI presets when creating a clinic role)."""

    code: str
    permission_codes: list[str] = Field(default_factory=list)


class RbacCatalogResponse(BaseModel):
    roles: list[RbacRoleRead] = Field(default_factory=list)
    permissions: list[RbacPermissionRead] = Field(default_factory=list)
    role_presets: list[RbacRolePresetRead] = Field(default_factory=list)


class RbacRoleCreate(BaseModel):
    """Create a clinic-scoped role. Requires an explicit non-empty permission set.

    Code shape and reserved names are validated in the router with ``Accept-Language`` messages.
    """

    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    permission_codes: list[str] = Field(..., min_length=1)
    note: str | None = Field(None, max_length=1000)

    @field_validator("code")
    @classmethod
    def strip_role_code(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Role code is required")
        return s

    @field_validator("permission_codes")
    @classmethod
    def dedupe_sorted_permissions(cls, v: list[str]) -> list[str]:
        return sorted(set(v))


class RbacUserPermissionOverrideRead(BaseModel):
    permission_code: str
    effect: str  # grant|deny


class RbacUserRead(BaseModel):
    admin_id: UUID
    full_name: str | None = None
    email: str
    role_codes: list[str] = Field(default_factory=list)
    direct_overrides: list[RbacUserPermissionOverrideRead] = Field(default_factory=list)
    effective_permission_codes: list[str] = Field(default_factory=list)


class RbacUsersResponse(BaseModel):
    items: list[RbacUserRead] = Field(default_factory=list)


class RbacRolePermissionsPatch(BaseModel):
    permission_codes: list[str] = Field(default_factory=list)
    note: str | None = Field(None, max_length=1000)


class RbacUserRolesPatch(BaseModel):
    role_codes: list[str] = Field(default_factory=list)
    note: str | None = Field(None, max_length=1000)


class RbacUserPermissionOverridePatchItem(BaseModel):
    permission_code: str
    effect: str  # grant|deny


class RbacUserPermissionsPatch(BaseModel):
    overrides: list[RbacUserPermissionOverridePatchItem] = Field(default_factory=list)
    note: str | None = Field(None, max_length=1000)


class RbacMutationOk(BaseModel):
    ok: bool = True


class RbacPolicyRead(BaseModel):
    allow_patient_disable_discount_notifications: bool
    allow_patient_disable_reminders: bool
    allow_patient_disable_all_notifications: bool
    owner_morning_brief_enabled: bool
    morning_brief_send_at_utc: str | None = None
    owner_telegram_chat_id: str | None = None
    ai_supervisor_enabled: bool
    ai_supervisor_send_at_utc: str | None = None
    ai_supervisor_recipient_chat_ids: list[str] = Field(default_factory=list)


class RbacPolicyPatch(BaseModel):
    allow_patient_disable_discount_notifications: bool | None = None
    allow_patient_disable_reminders: bool | None = None
    allow_patient_disable_all_notifications: bool | None = None
    owner_morning_brief_enabled: bool | None = None
    morning_brief_send_at_utc: str | None = None
    owner_telegram_chat_id: str | None = None
    ai_supervisor_enabled: bool | None = None
    ai_supervisor_send_at_utc: str | None = None
    ai_supervisor_recipient_chat_ids: list[str] | None = None
    note: str | None = Field(None, max_length=1000)


class RbacAuditLogRead(BaseModel):
    id: UUID
    actor_admin_id: UUID | None = None
    actor_admin_name: str | None = None
    action: str
    entity_type: str
    entity_id: str
    before_payload: dict | None = None
    after_payload: dict | None = None
    note: str | None = None
    created_at: datetime
