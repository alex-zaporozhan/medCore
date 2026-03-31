"""RBAC repository implementation using SQLAlchemy."""

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.role import Role
from src.domain.entities.role_permission import RolePermission
from src.domain.entities.permission import Permission
from src.domain.entities.user_role import UserRole
from src.domain.entities.user_permission_grant import UserPermissionGrant
from src.domain.interfaces.repositories.rbac_repository import RbacRepository
from src.application.rbac_matrix import ALL_PERMISSION_CODES


class RbacRepositoryImpl(RbacRepository):
    """RBAC repository over SQLAlchemy models."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_role_codes_for_user(self, user_id: UUID, clinic_id: UUID) -> list[str]:
        stmt: Select = (
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                UserRole.clinic_id == clinic_id,
            )
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_permission_codes_for_user(self, user_id: UUID, clinic_id: UUID) -> list[str]:
        role_codes = await self.get_role_codes_for_user(user_id=user_id, clinic_id=clinic_id)
        # Hard guarantee: owner always keeps full permission set.
        if "owner" in set(role_codes):
            return sorted(ALL_PERMISSION_CODES)

        role_stmt: Select = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                UserRole.clinic_id == clinic_id,
            )
        )
        role_result = await self._session.execute(role_stmt)
        role_codes: set[str] = {row[0] for row in role_result.all()}

        override_stmt: Select = (
            select(Permission.code, UserPermissionGrant.effect)
            .join(Permission, Permission.id == UserPermissionGrant.permission_id)
            .where(
                UserPermissionGrant.user_id == user_id,
                UserPermissionGrant.clinic_id == clinic_id,
            )
        )
        override_result = await self._session.execute(override_stmt)
        grant_codes: set[str] = set()
        deny_codes: set[str] = set()
        for code, effect in override_result.all():
            if effect == "deny":
                deny_codes.add(code)
            else:
                grant_codes.add(code)

        # Effective permissions: role-based + explicit grants - explicit denies
        codes = (role_codes | grant_codes) - deny_codes
        return sorted(codes)

