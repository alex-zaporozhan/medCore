"""Centralized UserRole replacement + audit (RBAC management + staff directory)."""

from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.rbac_audit_log import RbacAuditLog
from src.domain.entities.role import Role
from src.domain.entities.user_role import UserRole


async def ensure_role_codes_exist(session: AsyncSession, clinic_id: UUID, codes: list[str]) -> None:
    for code in codes:
        if await get_role_by_code(session, clinic_id, code) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown role code: {code}",
            )


async def get_role_by_code(session: AsyncSession, clinic_id: UUID, code: str) -> Role | None:
    clinic_row = await session.execute(
        select(Role).where(Role.clinic_id == clinic_id, Role.code == code).limit(1)
    )
    role = clinic_row.scalar_one_or_none()
    if role is not None:
        return role
    global_row = await session.execute(
        select(Role).where(Role.clinic_id.is_(None), Role.code == code).limit(1)
    )
    return global_row.scalar_one_or_none()


async def user_has_owner_role(session: AsyncSession, clinic_id: UUID, user_id: UUID) -> bool:
    rows = await session.execute(
        select(Role.code)
        .select_from(UserRole)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.clinic_id == clinic_id, UserRole.user_id == user_id)
    )
    return "owner" in {str(r[0]) for r in rows.all() if r[0]}


async def log_rbac_audit(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    actor_admin_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before_payload: dict | None = None,
    after_payload: dict | None = None,
    note: str | None = None,
) -> None:
    session.add(
        RbacAuditLog(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            actor_admin_id=actor_admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_payload=before_payload,
            after_payload=after_payload,
            note=note,
        )
    )


async def replace_user_roles_for_clinic(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    user_id: UUID,
    role_codes: list[str],
    actor_admin_id: UUID | None,
    audit_action: str,
    entity_type: str,
    entity_id: str,
    note: str | None = None,
    preserve_owner_role: bool = False,
) -> None:
    """Replace all UserRole rows for (clinic_id, user_id) with resolved roles.

    If preserve_owner_role is True and the user currently has the owner role, \"owner\" is merged
    into the effective role set (category template sync).
    If False, caller must enforce owner rules (e.g. forbid removing owner from owner user).
    """
    effective_codes = list(dict.fromkeys(role_codes))
    if preserve_owner_role and await user_has_owner_role(session, clinic_id, user_id):
        if "owner" not in effective_codes:
            effective_codes = [*effective_codes, "owner"]

    target_roles: list[Role] = []
    for code in effective_codes:
        role = await get_role_by_code(session, clinic_id, code)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown role code: {code}",
            )
        target_roles.append(role)
    target_role_ids = {r.id for r in target_roles}

    current_res = await session.execute(
        select(UserRole.role_id).where(UserRole.clinic_id == clinic_id, UserRole.user_id == user_id)
    )
    current_role_ids = {row[0] for row in current_res.all()}
    if current_role_ids == target_role_ids:
        return

    current_codes: list[str] = []
    if current_role_ids:
        current_codes_res = await session.execute(select(Role.code).where(Role.id.in_(list(current_role_ids))))
        current_codes = sorted([row[0] for row in current_codes_res.all()])

    await log_rbac_audit(
        session,
        clinic_id=clinic_id,
        actor_admin_id=actor_admin_id,
        action=audit_action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_payload={"role_codes": current_codes},
        after_payload={"role_codes": sorted(effective_codes)},
        note=note,
    )
    await session.execute(
        delete(UserRole).where(
            UserRole.clinic_id == clinic_id,
            UserRole.user_id == user_id,
        )
    )
    for role_id in sorted(target_role_ids):
        session.add(
            UserRole(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                user_id=user_id,
                role_id=role_id,
            )
        )
