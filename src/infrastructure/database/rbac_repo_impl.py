"""RBAC repository implementation using SQLAlchemy."""

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.role import Role
from src.domain.entities.role_permission import RolePermission
from src.domain.entities.permission import Permission
from src.domain.entities.user_role import UserRole
from src.domain.interfaces.repositories.rbac_repository import RbacRepository


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
        stmt: Select = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user_id,
                UserRole.clinic_id == clinic_id,
            )
        )
        result = await self._session.execute(stmt)
        # Deduplicate in Python to avoid DISTINCT overhead
        codes: set[str] = {row[0] for row in result.all()}
        return sorted(codes)

