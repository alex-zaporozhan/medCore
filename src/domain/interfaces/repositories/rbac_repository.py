"""RBAC repository interface."""

from typing import Protocol
from uuid import UUID


class RbacRepository(Protocol):
    """Contract for RBAC-related queries."""

    async def get_role_codes_for_user(self, user_id: UUID, clinic_id: UUID) -> list[str]:
        ...

    async def get_permission_codes_for_user(self, user_id: UUID, clinic_id: UUID) -> list[str]:
        ...

