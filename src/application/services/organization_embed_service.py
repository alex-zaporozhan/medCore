"""Embed API keys and webhook inbox (SaaS §24, Phase 1e)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from passlib.hash import pbkdf2_sha256
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.organization_entitlement_access import (
    ensure_org_entitlement_keys_for_public_client,
)
from src.domain.entities.organization_embed_api_key import OrganizationEmbedApiKey
from src.domain.entities.organization_embed_inbound_receipt import OrganizationEmbedInboundReceipt
from src.domain.entities.organization_embed_settings import OrganizationEmbedSettings

TOKEN_SCHEME = "dceb"
EMBED_ENTITLEMENT_KEY = "omni.embed.bundle"


def hash_embed_secret(secret: str) -> str:
    return pbkdf2_sha256.hash(secret)


def verify_embed_secret(plain: str, hashed: str) -> bool:
    return pbkdf2_sha256.verify(plain, hashed)


def parse_embed_api_token(authorization: str | None) -> tuple[uuid.UUID, str] | None:
    if not authorization or not authorization.strip():
        return None
    s = authorization.strip()
    if s.lower().startswith("bearer "):
        s = s[7:].strip()
    parts = s.split(".", 2)
    if len(parts) != 3 or parts[0] != TOKEN_SCHEME:
        return None
    try:
        key_id = uuid.UUID(parts[1])
    except ValueError:
        return None
    secret = parts[2]
    if len(secret) < 16:
        return None
    return key_id, secret


async def get_or_create_embed_settings(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> OrganizationEmbedSettings:
    row = await session.get(OrganizationEmbedSettings, organization_id)
    if row is not None:
        return row
    row = OrganizationEmbedSettings(
        organization_id=organization_id,
        inbound_route_token=uuid.uuid4(),
    )
    session.add(row)
    await session.flush()
    return row


async def create_embed_api_key(
    session: AsyncSession,
    organization_id: uuid.UUID,
    label: str | None,
) -> tuple[OrganizationEmbedApiKey, str]:
    key_id = uuid.uuid4()
    secret = secrets.token_urlsafe(32)
    token = f"{TOKEN_SCHEME}.{key_id}.{secret}"
    prefix = f"{TOKEN_SCHEME}_{secret[:8]}…"
    row = OrganizationEmbedApiKey(
        id=key_id,
        organization_id=organization_id,
        label=(label.strip()[:128] if label else None),
        key_prefix=prefix[:32],
        key_hash=hash_embed_secret(secret),
    )
    session.add(row)
    await session.flush()
    return row, token


async def list_embed_api_keys(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> list[OrganizationEmbedApiKey]:
    result = await session.execute(
        select(OrganizationEmbedApiKey)
        .where(OrganizationEmbedApiKey.organization_id == organization_id)
        .order_by(OrganizationEmbedApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_embed_api_key(
    session: AsyncSession,
    organization_id: uuid.UUID,
    key_id: uuid.UUID,
) -> bool:
    row = await session.get(OrganizationEmbedApiKey, key_id)
    if row is None or row.organization_id != organization_id:
        return False
    if row.revoked_at is not None:
        return True
    row.revoked_at = datetime.now(timezone.utc)
    await session.flush()
    return True


async def rotate_webhook_bearer(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> tuple[OrganizationEmbedSettings, str]:
    settings = await get_or_create_embed_settings(session, organization_id)
    secret = secrets.token_urlsafe(32)
    settings.webhook_bearer_hash = hash_embed_secret(secret)
    settings.webhook_bearer_prefix = secret[:12]
    settings.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return settings, secret


async def resolve_embed_api_key_from_request(
    session: AsyncSession,
    authorization: str | None,
) -> tuple[uuid.UUID, OrganizationEmbedApiKey]:
    parsed = parse_embed_api_token(authorization)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "embed_auth_required", "message": "Нужен заголовок Authorization: Bearer dceb.<id>.<secret>"},
        )
    key_id, secret = parsed
    row = await session.get(OrganizationEmbedApiKey, key_id)
    if row is None or row.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "embed_auth_invalid", "message": "Недействительный или отозванный ключ"},
        )
    if not verify_embed_secret(secret, row.key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "embed_auth_invalid", "message": "Недействительный или отозванный ключ"},
        )
    await ensure_org_entitlement_keys_for_public_client(
        session,
        row.organization_id,
        EMBED_ENTITLEMENT_KEY,
    )
    row.last_used_at = datetime.now(timezone.utc)
    await session.flush()
    return row.organization_id, row


async def get_embed_settings_by_route_token(
    session: AsyncSession,
    inbound_route_token: uuid.UUID,
) -> OrganizationEmbedSettings | None:
    result = await session.execute(
        select(OrganizationEmbedSettings).where(
            OrganizationEmbedSettings.inbound_route_token == inbound_route_token
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def verify_webhook_bearer_and_org(
    session: AsyncSession,
    settings: OrganizationEmbedSettings,
    authorization: str | None,
) -> tuple[uuid.UUID, str]:
    """Returns (organization_id, bearer_plain_secret) for optional HMAC over raw body."""
    if not settings.webhook_bearer_hash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "embed_webhook_not_configured",
                "message": "Webhook secret не выпущен. Используйте POST /admin/organization/embed/webhook-secret/rotate",
            },
        )
    if not authorization or not authorization.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "embed_webhook_auth_required", "message": "Нужен Authorization: Bearer <webhook_secret>"},
        )
    s = authorization.strip()
    if s.lower().startswith("bearer "):
        s = s[7:].strip()
    if not verify_embed_secret(s, settings.webhook_bearer_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "embed_webhook_auth_invalid", "message": "Неверный webhook secret"},
        )
    await ensure_org_entitlement_keys_for_public_client(
        session,
        settings.organization_id,
        EMBED_ENTITLEMENT_KEY,
    )
    return settings.organization_id, s


def parse_embed_webhook_signature_header(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    h = value.strip()
    lower = h.lower()
    for prefix in ("v1=", "sha256="):
        if lower.startswith(prefix):
            return h[len(prefix) :].strip().lower()
    return None


def verify_embed_webhook_hmac_if_present(
    body: bytes,
    bearer_plain: str,
    signature_header: str | None,
    *,
    signature_required: bool,
) -> None:
    hex_sig = parse_embed_webhook_signature_header(signature_header)
    if signature_required and not hex_sig:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "embed_webhook_signature_required",
                "message": "Требуется заголовок X-Embed-Signature: v1=<hmac_sha256_hex> (ключ = Bearer secret, тело = raw body)",
            },
        )
    if not hex_sig:
        return
    if len(hex_sig) != 64 or any(c not in "0123456789abcdef" for c in hex_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "embed_webhook_signature_malformed",
                "message": "Неверный формат X-Embed-Signature",
            },
        )
    mac = hmac.new(bearer_plain.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, hex_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "embed_webhook_signature_invalid",
                "message": "HMAC не совпадает с телом запроса",
            },
        )


async def record_embed_inbound_idempotency(
    session: AsyncSession,
    organization_id: uuid.UUID,
    idempotency_key: str | None,
    body_sha256_hex: str,
) -> tuple[bool, bool]:
    """
    (is_new_delivery, is_duplicate_same_body).

    Без ключа идемпотентности — считаем новой доставкой без записи в ledger.
    """
    if not idempotency_key or not idempotency_key.strip():
        return True, False
    key = idempotency_key.strip()[:128]
    result = await session.execute(
        select(OrganizationEmbedInboundReceipt).where(
            OrganizationEmbedInboundReceipt.organization_id == organization_id,
            OrganizationEmbedInboundReceipt.idempotency_key == key,
        ).limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.body_sha256 != body_sha256_hex:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "embed_webhook_idempotency_conflict",
                    "message": "Тот же Idempotency-Key уже использован с другим телом запроса",
                },
            )
        return False, True
    session.add(
        OrganizationEmbedInboundReceipt(
            id=uuid.uuid4(),
            organization_id=organization_id,
            idempotency_key=key,
            body_sha256=body_sha256_hex,
        )
    )
    await session.flush()
    return True, False
