"""RBAC service for resolving roles and permissions for current admin users."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.domain.interfaces.repositories.rbac_repository import RbacRepository


@dataclass
class UserRbacInfo:
    roles: list[str]
    permissions: list[str]


class RbacService(Protocol):
    async def get_roles_for_user(self, user_id: UUID, clinic_id: UUID) -> list[str]:
        ...

    async def get_permissions_for_user(self, user_id: UUID, clinic_id: UUID) -> list[str]:
        ...

    async def get_rbac_info_for_user(self, user_id: UUID, clinic_id: UUID) -> UserRbacInfo:
        ...

    async def user_has_any_permission(
        self, user_id: UUID, clinic_id: UUID, permission_codes: Iterable[str]
    ) -> bool:
        ...


class RbacServiceImpl:
    """Default RBAC service implementation."""

    def __init__(self, repo: RbacRepository) -> None:
        self._repo = repo

    async def get_roles_for_user(self, user_id: UUID, clinic_id: UUID) -> list[str]:
        return await self._repo.get_role_codes_for_user(user_id=user_id, clinic_id=clinic_id)

    async def get_permissions_for_user(self, user_id: UUID, clinic_id: UUID) -> list[str]:
        return await self._repo.get_permission_codes_for_user(user_id=user_id, clinic_id=clinic_id)

    async def get_rbac_info_for_user(self, user_id: UUID, clinic_id: UUID) -> UserRbacInfo:
        roles = await self.get_roles_for_user(user_id=user_id, clinic_id=clinic_id)
        permissions = await self.get_permissions_for_user(user_id=user_id, clinic_id=clinic_id)
        return UserRbacInfo(roles=roles, permissions=permissions)

    async def user_has_any_permission(
        self, user_id: UUID, clinic_id: UUID, permission_codes: Iterable[str]
    ) -> bool:
        if not permission_codes:
            return True
        user_permissions = await self.get_permissions_for_user(user_id=user_id, clinic_id=clinic_id)
        user_perm_set = set(user_permissions)
        for code in permission_codes:
            if code in user_perm_set:
                return True
        return False

