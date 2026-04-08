"""Organization entitlement checks (SaaS catalog vs legacy installs). See SAAS_STRENGTHENING_MASTER_PLAN §12, §15b 1c."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.edition import is_box_edition
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement

# Optional paid modules: unavailable in box edition (same product boundary as CRM/retention before 1c).
BOX_BLOCKED_ENTITLEMENT_KEYS: frozenset[str] = frozenset(
    {
        "crm.pipeline",
        "retention.bundle",
        "tasks.kanban",
        "marketing.attribution",
        "omni.embed.bundle",
        "ai.assistant.chat",
        "ai.rag.org_kb",
        "import.crm_v1",
        "import.enterprise_migrator",
        "commerce.store_network",
    }
)


def _strict_org_ids_from_settings() -> frozenset[UUID]:
    raw = (settings.entitlement_enforcement_strict_org_ids or "").strip()
    if not raw:
        return frozenset()
    out: set[UUID] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            out.add(UUID(token))
        except ValueError:
            continue
    return frozenset(out)


async def org_entitlement_enforcement_state(
    session: AsyncSession,
    organization_id: UUID | None,
) -> tuple[bool, frozenset[str]]:
    """
    Returns (enforced, keys).

    enforced=True when the organization has at least one row in organization_entitlements
    (SaaS tariff applied). Otherwise legacy: optional modules follow Enterprise/box rules without DB gate.
    """
    mode = (settings.entitlement_enforcement_mode or "auto").strip().lower()
    if organization_id is None:
        return False, frozenset()
    if mode == "legacy":
        return False, frozenset()
    result = await session.execute(
        select(OrganizationEntitlement.entitlement_key).where(
            OrganizationEntitlement.organization_id == organization_id
        )
    )
    keys = frozenset(row[0] for row in result.all())
    if mode == "strict":
        return True, keys
    if mode == "auto":
        strict_org_ids = _strict_org_ids_from_settings()
        if organization_id in strict_org_ids:
            return True, keys
    if not keys:
        return False, frozenset()
    return True, keys


async def list_legacy_organizations_without_entitlements(
    session: AsyncSession,
    *,
    limit: int = 500,
) -> list[UUID]:
    """
    Phase 3 backfill inventory: organizations with no rows in organization_entitlements.
    """
    subq = (
        select(OrganizationEntitlement.organization_id)
        .where(OrganizationEntitlement.organization_id.isnot(None))
        .distinct()
    )
    rows = await session.execute(
        select(Organization.id).where(~Organization.id.in_(subq)).limit(limit)
    )
    return [row[0] for row in rows.all()]


async def ensure_org_has_any_entitlement(
    session: AsyncSession,
    admin: AdminUser,
    *required_keys: str,
) -> None:
    """403 if box blocks module, or SaaS org lacks any of the required entitlement keys."""
    if not required_keys:
        raise ValueError("ensure_org_has_any_entitlement requires at least one key")
    if is_box_edition():
        if any(k in BOX_BLOCKED_ENTITLEMENT_KEYS for k in required_keys):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "box_forbidden",
                    "message": "This module is not available in Box edition.",
                    "keys": list(required_keys),
                },
            )
        return

    enforced, owned = await org_entitlement_enforcement_state(session, admin.organization_id)
    if not enforced:
        return
    if not any(k in owned for k in required_keys):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "entitlement_required",
                "message": "Требуется активная опция тарифа для этой организации.",
                "keys": list(required_keys),
            },
        )


async def ensure_org_has_any_entitlement_for_organization(
    session: AsyncSession,
    organization_id: UUID,
    *required_keys: str,
) -> None:
    """
    Same SaaS/box rules as ensure_org_has_any_entitlement, but enforcement is keyed on
    explicit organization_id (e.g. resolved from clinic when admin.organization_id is unset).
    """
    if not required_keys:
        raise ValueError("ensure_org_has_any_entitlement_for_organization requires at least one key")
    if is_box_edition():
        if any(k in BOX_BLOCKED_ENTITLEMENT_KEYS for k in required_keys):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "box_forbidden",
                    "message": "This module is not available in Box edition.",
                    "keys": list(required_keys),
                },
            )
        return

    enforced, owned = await org_entitlement_enforcement_state(session, organization_id)
    if not enforced:
        return
    if not any(k in owned for k in required_keys):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "entitlement_required",
                "message": "Требуется активная опция тарифа для этой организации.",
                "keys": list(required_keys),
            },
        )


async def ensure_org_entitlement_keys_for_public_client(
    session: AsyncSession,
    organization_id: UUID,
    *required_keys: str,
) -> None:
    """
    Public/embed routes: same SaaS gate as admin modules, without AdminUser.

    Box edition: allow (deploy without per-org tariff rows).
    Legacy (no org entitlement rows): allow.
    """
    if not required_keys:
        raise ValueError("ensure_org_entitlement_keys_for_public_client requires at least one key")
    if is_box_edition():
        return
    enforced, owned = await org_entitlement_enforcement_state(session, organization_id)
    if not enforced:
        return
    if not any(k in owned for k in required_keys):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "entitlement_required",
                "message": "Требуется активная опция тарифа для этой организации.",
                "keys": list(required_keys),
            },
        )


async def session_entitlement_view(
    session: AsyncSession,
    admin: AdminUser,
) -> tuple[bool, list[str]]:
    """Payload for /admin/auth/session: enforced flag + sorted keys (empty when not enforced)."""
    enforced, keys = await org_entitlement_enforcement_state(session, admin.organization_id)
    return enforced, sorted(keys)
