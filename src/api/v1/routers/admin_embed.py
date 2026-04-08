"""Admin: embed API keys and webhook inbox secret (SaaS §24, Phase 1e)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_permissions
from src.api.v1.entitlement_dependencies import require_entitlement
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.embed_security_audit_service import log_organization_embed_audit
from src.application.services.organization_embed_service import (
    create_embed_api_key,
    get_or_create_embed_settings,
    list_embed_api_keys,
    revoke_embed_api_key,
    rotate_webhook_bearer,
)
from src.core.openapi_error_schemas import OPENAPI_403_ENTITLEMENT_GATE_RESPONSE
from src.domain.entities.admin_user import AdminUser

router = APIRouter(
    prefix="/admin/organization/embed",
    tags=["admin-embed"],
    dependencies=[Depends(require_entitlement("omni.embed.bundle"))],
    responses={403: OPENAPI_403_ENTITLEMENT_GATE_RESPONSE},
)


def _require_org(admin: AdminUser) -> uuid.UUID:
    if admin.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "organization_required", "message": "У администратора нет organization_id"},
        )
    return admin.organization_id


class EmbedApiKeyCreateBody(BaseModel):
    label: str | None = Field(None, max_length=128)


class EmbedApiKeyCreatedResponse(BaseModel):
    id: str
    token: str = Field(..., description="Показывается один раз; формат dceb.<uuid>.<secret>")
    key_prefix: str


class EmbedApiKeyItem(BaseModel):
    id: str
    label: str | None
    key_prefix: str
    created_at: str
    revoked_at: str | None


class EmbedApiKeyListResponse(BaseModel):
    items: list[EmbedApiKeyItem]


class EmbedSettingsResponse(BaseModel):
    inbound_route_token: str
    webhook_configured: bool
    webhook_bearer_prefix: str | None


class EmbedWebhookRotateResponse(BaseModel):
    webhook_secret: str = Field(..., description="Показывается один раз; передайте внешнему каналу как Bearer")


@router.get("/api-keys", response_model=EmbedApiKeyListResponse)
async def list_embed_keys(
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("view_embed_settings")),
) -> EmbedApiKeyListResponse:
    org_id = _require_org(admin)
    rows = await list_embed_api_keys(session, org_id)
    items = [
        EmbedApiKeyItem(
            id=str(r.id),
            label=r.label,
            key_prefix=r.key_prefix,
            created_at=r.created_at.isoformat(),
            revoked_at=r.revoked_at.isoformat() if r.revoked_at else None,
        )
        for r in rows
    ]
    return EmbedApiKeyListResponse(items=items)


@router.post("/api-keys", response_model=EmbedApiKeyCreatedResponse)
async def create_embed_key(
    body: EmbedApiKeyCreateBody,
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("manage_embed_settings")),
) -> EmbedApiKeyCreatedResponse:
    org_id = _require_org(admin)
    row, token = await create_embed_api_key(session, org_id, body.label)
    await log_organization_embed_audit(
        session,
        organization_id=org_id,
        actor_admin_id=admin.id,
        action="embed_api_key_create",
        embed_api_key_id=row.id,
        meta={"label": body.label},
    )
    await session.commit()
    return EmbedApiKeyCreatedResponse(id=str(row.id), token=token, key_prefix=row.key_prefix)


@router.post("/api-keys/{key_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_embed_key(
    key_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("manage_embed_settings")),
) -> None:
    org_id = _require_org(admin)
    ok = await revoke_embed_api_key(session, org_id, key_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "embed_api_key_not_found", "message": "Ключ не найден"},
        )
    await log_organization_embed_audit(
        session,
        organization_id=org_id,
        actor_admin_id=admin.id,
        action="embed_api_key_revoke",
        embed_api_key_id=key_id,
    )
    await session.commit()


@router.get("/settings", response_model=EmbedSettingsResponse)
async def get_embed_settings(
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("view_embed_settings")),
) -> EmbedSettingsResponse:
    org_id = _require_org(admin)
    settings = await get_or_create_embed_settings(session, org_id)
    await session.commit()
    return EmbedSettingsResponse(
        inbound_route_token=str(settings.inbound_route_token),
        webhook_configured=bool(settings.webhook_bearer_hash),
        webhook_bearer_prefix=settings.webhook_bearer_prefix,
    )


@router.post("/webhook-secret/rotate", response_model=EmbedWebhookRotateResponse)
async def rotate_embed_webhook_secret(
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("manage_embed_settings")),
) -> EmbedWebhookRotateResponse:
    org_id = _require_org(admin)
    _, secret = await rotate_webhook_bearer(session, org_id)
    await log_organization_embed_audit(
        session,
        organization_id=org_id,
        actor_admin_id=admin.id,
        action="embed_webhook_secret_rotate",
        embed_api_key_id=None,
    )
    await session.commit()
    return EmbedWebhookRotateResponse(webhook_secret=secret)
