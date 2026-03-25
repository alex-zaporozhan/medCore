"""Idempotent RBAC baseline: permissions, global roles, role_permissions.

Used by presentation seed and can be run after empty migrations that omitted
archive `rbac_tasks_0001_init` data inserts.

Run: poetry run python -m src.scripts.seed_rbac_baseline
"""

from __future__ import annotations

import asyncio
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.rbac_matrix import PERMISSIONS, ROLE_PERMISSIONS
from src.domain.entities.clinic import Clinic  # noqa: F401 — Role.clinic_id FK metadata
from src.domain.entities.permission import Permission
from src.domain.entities.role import Role
from src.domain.entities.role_permission import RolePermission
from src.domain.entities.user_role import UserRole
from src.infrastructure.database.base import AsyncSessionLocal


async def ensure_permissions(session: AsyncSession) -> dict[str, UUID]:
    """Upsert all Permission rows from rbac_matrix; return code -> id."""
    by_code: dict[str, UUID] = {}
    for pd in PERMISSIONS:
        res = await session.execute(select(Permission).where(Permission.code == pd.code))
        row = res.scalar_one_or_none()
        if row is None:
            row = Permission(id=uuid.uuid4(), code=pd.code, description=pd.description)
            session.add(row)
            await session.flush()
        by_code[pd.code] = row.id
    return by_code


async def ensure_global_roles(session: AsyncSession) -> dict[str, UUID]:
    """Ensure global roles (clinic_id IS NULL) owner/manager/admin/doctor exist."""
    out: dict[str, UUID] = {}
    for code in ("owner", "manager", "admin", "doctor"):
        res = await session.execute(
            select(Role).where(Role.clinic_id.is_(None), Role.code == code)
        )
        row = res.scalar_one_or_none()
        if row is None:
            row = Role(
                id=uuid.uuid4(),
                clinic_id=None,
                code=code,
                name=code.capitalize(),
                description=f"Global role {code}",
            )
            session.add(row)
            await session.flush()
        out[code] = row.id
    return out


async def ensure_role_permissions(session: AsyncSession) -> None:
    perm_by_code = await ensure_permissions(session)
    role_by_code = await ensure_global_roles(session)
    for role_code, perm_codes in ROLE_PERMISSIONS.items():
        rid = role_by_code.get(role_code)
        if not rid:
            continue
        for pc in perm_codes:
            pid = perm_by_code.get(pc)
            if not pid:
                continue
            res = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == rid,
                    RolePermission.permission_id == pid,
                )
            )
            if res.scalar_one_or_none() is None:
                session.add(
                    RolePermission(
                        id=uuid.uuid4(),
                        role_id=rid,
                        permission_id=pid,
                    )
                )
    await session.flush()


async def ensure_user_owner_role(
    session: AsyncSession,
    *,
    admin_id: UUID,
    clinic_id: UUID,
) -> None:
    """Attach global `owner` role to admin for the given clinic."""
    role_res = await session.execute(
        select(Role).where(Role.clinic_id.is_(None), Role.code == "owner")
    )
    owner_role = role_res.scalar_one_or_none()
    if owner_role is None:
        raise RuntimeError("Global owner role missing; run ensure_role_permissions first.")
    res = await session.execute(
        select(UserRole).where(
            UserRole.user_id == admin_id,
            UserRole.role_id == owner_role.id,
            UserRole.clinic_id == clinic_id,
        )
    )
    if res.scalar_one_or_none() is None:
        session.add(
            UserRole(
                id=uuid.uuid4(),
                user_id=admin_id,
                role_id=owner_role.id,
                clinic_id=clinic_id,
            )
        )
        await session.flush()


async def ensure_user_role_by_code(
    session: AsyncSession,
    *,
    admin_id: UUID,
    clinic_id: UUID,
    role_code: str,
) -> None:
    """Attach a global role (e.g. manager) to an admin for the given clinic."""
    role_res = await session.execute(
        select(Role).where(Role.clinic_id.is_(None), Role.code == role_code)
    )
    role_row = role_res.scalar_one_or_none()
    if role_row is None:
        raise RuntimeError(
            f"Global role {role_code!r} missing; run ensure_role_permissions first."
        )
    res = await session.execute(
        select(UserRole).where(
            UserRole.user_id == admin_id,
            UserRole.role_id == role_row.id,
            UserRole.clinic_id == clinic_id,
        )
    )
    if res.scalar_one_or_none() is None:
        session.add(
            UserRole(
                id=uuid.uuid4(),
                user_id=admin_id,
                role_id=role_row.id,
                clinic_id=clinic_id,
            )
        )
        await session.flush()


async def ensure_user_manager_role(
    session: AsyncSession,
    *,
    admin_id: UUID,
    clinic_id: UUID,
) -> None:
    """Attach global `manager` role to admin for the given clinic."""
    await ensure_user_role_by_code(
        session, admin_id=admin_id, clinic_id=clinic_id, role_code="manager"
    )


async def seed_rbac() -> None:
    async with AsyncSessionLocal() as session:
        await ensure_role_permissions(session)
        await session.commit()
        print("RBAC baseline: permissions + global roles + role_permissions OK.")


def main() -> None:
    asyncio.run(seed_rbac())


if __name__ == "__main__":
    main()
