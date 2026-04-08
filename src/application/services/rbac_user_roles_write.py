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


async def replace_user_roles_for_users_in_clinic(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    user_ids: list[UUID],
    role_codes: list[str],
    actor_admin_id: UUID | None,
    audit_action: str,
    entity_type: str,
    entity_id: str,
    note: str | None = None,
    preserve_owner_role: bool = False,
    audit_after_payload_extra: dict | None = None,
) -> int:
    """
    Batch variant of role replacement for many users.

    Enterprise goal: avoid per-user role resolution and per-user roundtrips.
    Returns affected user count (attempted).
    """
    uniq_user_ids = list(dict.fromkeys([u for u in user_ids if u is not None]))
    if not uniq_user_ids:
        return 0

    effective_codes = list(dict.fromkeys(role_codes))
    # Preserve owner role: detect which users currently have owner.
    owner_user_ids: set[UUID] = set()
    if preserve_owner_role:
        owner_rows = await session.execute(
            select(UserRole.user_id)
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                UserRole.clinic_id == clinic_id,
                UserRole.user_id.in_(uniq_user_ids),
                Role.code == "owner",
            )
        )
        owner_user_ids = {row[0] for row in owner_rows.all()}

    # Resolve role ids once.
    role_ids: list[UUID] = []
    for code in effective_codes:
        role = await get_role_by_code(session, clinic_id, code)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown role code: {code}",
            )
        role_ids.append(role.id)
    # Ensure owner role exists if needed.
    owner_role_id: UUID | None = None
    if preserve_owner_role and owner_user_ids:
        owner_role = await get_role_by_code(session, clinic_id, "owner")
        if owner_role is not None:
            owner_role_id = owner_role.id

    # Load current roles for all users (for audit; cheap map).
    current_rows = await session.execute(
        select(UserRole.user_id, Role.code)
        .select_from(UserRole)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.clinic_id == clinic_id, UserRole.user_id.in_(uniq_user_ids))
    )
    cur_by_user: dict[UUID, set[str]] = {}
    for uid, code in current_rows.all():
        cur_by_user.setdefault(uid, set()).add(str(code))

    # Prepare target codes per user (owner preserved).
    target_codes_base = sorted(effective_codes)
    target_codes_by_user: dict[UUID, list[str]] = {}
    for uid in uniq_user_ids:
        if preserve_owner_role and uid in owner_user_ids and "owner" not in target_codes_base:
            target_codes_by_user[uid] = sorted([*target_codes_base, "owner"])
        else:
            target_codes_by_user[uid] = target_codes_base

    # Audit per user (batch insert via session.add in loop; still OK; heavy work was avoided).
    for uid in uniq_user_ids:
        before_codes = sorted(list(cur_by_user.get(uid, set())))
        after_codes = target_codes_by_user[uid]
        if before_codes == after_codes:
            continue
        await log_rbac_audit(
            session,
            clinic_id=clinic_id,
            actor_admin_id=actor_admin_id,
            action=audit_action,
            entity_type=entity_type,
            entity_id=str(uid) if entity_type == "admin_user" else entity_id,
            before_payload={"role_codes": before_codes},
            after_payload={
                "role_codes": after_codes,
                "affected_user_count": len(uniq_user_ids),
                **(audit_after_payload_extra or {}),
            },
            note=note,
        )

    # Bulk delete roles for these users.
    await session.execute(
        delete(UserRole).where(UserRole.clinic_id == clinic_id, UserRole.user_id.in_(uniq_user_ids))
    )

    # Bulk insert new roles.
    for uid in uniq_user_ids:
        # base roles
        for rid in sorted(set(role_ids)):
            session.add(UserRole(id=uuid.uuid4(), clinic_id=clinic_id, user_id=uid, role_id=rid))
        # preserved owner if needed and not included in base
        if preserve_owner_role and owner_role_id and uid in owner_user_ids and owner_role_id not in set(role_ids):
            session.add(UserRole(id=uuid.uuid4(), clinic_id=clinic_id, user_id=uid, role_id=owner_role_id))

    return len(uniq_user_ids)


async def attach_global_role_if_missing(
    session: AsyncSession,
    *,
    user_id: UUID,
    clinic_id: UUID,
    role_code: str,
) -> None:
    """Idempotent UserRole row for a global (clinic_id NULL) or clinic-local role."""
    role = await get_role_by_code(session, clinic_id, role_code)
    if role is None:
        return
    res = await session.execute(
        select(UserRole.id).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id,
            UserRole.clinic_id == clinic_id,
        ).limit(1)
    )
    if res.scalar_one_or_none() is None:
        session.add(
            UserRole(
                id=uuid.uuid4(),
                user_id=user_id,
                role_id=role.id,
                clinic_id=clinic_id,
            )
        )
