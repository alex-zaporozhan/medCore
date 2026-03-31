"""Staff directory: profession categories and admin rows per clinic."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.staff_directory_dto import (
    StaffDirectoryAdminRead,
    StaffProfessionCategoryRead,
)
from src.application.services.rbac_user_roles_write import (
    replace_user_roles_for_clinic,
)
from src.application.services.staff_directory_cache import invalidate_staff_profession_categories_cache
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.staff_profession_category import StaffProfessionCategory


class StaffDirectoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_profession_categories(self, clinic_id: UUID) -> list[StaffProfessionCategoryRead]:
        result = await self._session.execute(
            select(StaffProfessionCategory)
            .where(
                StaffProfessionCategory.clinic_id == clinic_id,
                StaffProfessionCategory.deleted_at.is_(None),
            )
            .order_by(StaffProfessionCategory.sort_order.asc(), StaffProfessionCategory.name.asc())
        )
        rows = list(result.scalars().all())
        return [StaffProfessionCategoryRead.model_validate(r) for r in rows]

    async def create_profession_category(
        self, clinic_id: UUID, name: str, sort_order: int, default_role_codes: list[str]
    ) -> StaffProfessionCategoryRead:
        normalized = name.strip()
        if not normalized:
            raise ValueError("empty_name")
        dup = await self._session.execute(
            select(StaffProfessionCategory.id).where(
                StaffProfessionCategory.clinic_id == clinic_id,
                StaffProfessionCategory.deleted_at.is_(None),
                func.lower(StaffProfessionCategory.name) == normalized.lower(),
            )
        )
        if dup.scalar_one_or_none():
            raise ValueError("duplicate_name")
        codes = list(dict.fromkeys(default_role_codes))
        row = StaffProfessionCategory(
            clinic_id=clinic_id,
            name=normalized,
            sort_order=sort_order,
            default_role_codes=codes,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        await invalidate_staff_profession_categories_cache(clinic_id)
        return StaffProfessionCategoryRead.model_validate(row)

    async def patch_profession_category(
        self,
        clinic_id: UUID,
        category_id: UUID,
        *,
        name: str | None,
        sort_order: int | None,
        default_role_codes: list[str] | None,
        actor_admin_id: UUID,
    ) -> StaffProfessionCategoryRead | None:
        result = await self._session.execute(
            select(StaffProfessionCategory).where(
                StaffProfessionCategory.id == category_id,
                StaffProfessionCategory.clinic_id == clinic_id,
                StaffProfessionCategory.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if name is not None:
            normalized = name.strip()
            if not normalized:
                raise ValueError("empty_name")
            dup = await self._session.execute(
                select(StaffProfessionCategory.id).where(
                    StaffProfessionCategory.clinic_id == clinic_id,
                    StaffProfessionCategory.deleted_at.is_(None),
                    StaffProfessionCategory.id != category_id,
                    func.lower(StaffProfessionCategory.name) == normalized.lower(),
                )
            )
            if dup.scalar_one_or_none():
                raise ValueError("duplicate_name")
            row.name = normalized
        if sort_order is not None:
            row.sort_order = sort_order
        prev_codes = list(row.default_role_codes) if row.default_role_codes else []
        if default_role_codes is not None:
            row.default_role_codes = list(dict.fromkeys(default_role_codes))
        await self._session.flush()
        await self._session.refresh(row)
        if default_role_codes is not None and sorted(prev_codes) != sorted(row.default_role_codes):
            await self._sync_category_template_roles(
                clinic_id=clinic_id,
                category_id=category_id,
                template_codes=list(row.default_role_codes),
                actor_admin_id=actor_admin_id,
            )
        await invalidate_staff_profession_categories_cache(clinic_id)
        return StaffProfessionCategoryRead.model_validate(row)

    async def _sync_category_template_roles(
        self,
        *,
        clinic_id: UUID,
        category_id: UUID,
        template_codes: list[str],
        actor_admin_id: UUID,
    ) -> None:
        res = await self._session.execute(
            select(AdminUser.id).where(
                AdminUser.clinic_id == clinic_id,
                AdminUser.profession_category_id == category_id,
                AdminUser.deleted_at.is_(None),
            )
        )
        for (uid,) in res.all():
            await replace_user_roles_for_clinic(
                self._session,
                clinic_id=clinic_id,
                user_id=uid,
                role_codes=template_codes,
                actor_admin_id=actor_admin_id,
                audit_action="staff.category_roles.sync",
                entity_type="admin_user",
                entity_id=str(uid),
                note=None,
                preserve_owner_role=True,
            )

    async def soft_delete_profession_category(self, clinic_id: UUID, category_id: UUID) -> bool:
        from src.core.datetime_utils import utc_now

        result = await self._session.execute(
            select(StaffProfessionCategory).where(
                StaffProfessionCategory.id == category_id,
                StaffProfessionCategory.clinic_id == clinic_id,
                StaffProfessionCategory.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self._session.execute(
            update(AdminUser)
            .where(AdminUser.profession_category_id == category_id)
            .values(profession_category_id=None)
        )
        row.deleted_at = utc_now()
        await self._session.flush()
        await invalidate_staff_profession_categories_cache(clinic_id)
        return True

    async def list_admins_with_profession(self, clinic_id: UUID) -> list[StaffDirectoryAdminRead]:
        result = await self._session.execute(
            select(AdminUser)
            .where(
                AdminUser.clinic_id == clinic_id,
                AdminUser.deleted_at.is_(None),
            )
            .order_by(AdminUser.created_at.asc())
        )
        admins = list(result.scalars().all())
        pc_ids = {a.profession_category_id for a in admins if a.profession_category_id}
        names: dict[UUID, str] = {}
        if pc_ids:
            r2 = await self._session.execute(
                select(StaffProfessionCategory).where(
                    StaffProfessionCategory.id.in_(pc_ids),
                    StaffProfessionCategory.deleted_at.is_(None),
                )
            )
            for pc in r2.scalars().all():
                names[pc.id] = pc.name
        out: list[StaffDirectoryAdminRead] = []
        for admin in admins:
            pid = admin.profession_category_id
            out.append(
                StaffDirectoryAdminRead(
                    id=str(admin.id),
                    clinic_id=str(admin.clinic_id),
                    email=admin.email,
                    full_name=admin.full_name,
                    birth_date=admin.birth_date.isoformat() if admin.birth_date else None,
                    employment_status=admin.employment_status,
                    profession_category_id=str(pid) if pid else None,
                    profession_category_name=names.get(pid) if pid else None,
                )
            )
        return out
