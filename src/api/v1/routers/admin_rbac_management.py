"""Admin RBAC management: roles, user overrides, policies, audit."""

from __future__ import annotations

import uuid
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.clinic_scope import resolve_effective_clinic_id
from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.rbac_user_roles_write import replace_user_roles_for_clinic, user_has_owner_role
from src.application.dto.rbac_management_dto import (
    RbacAuditLogRead,
    RbacCatalogResponse,
    RbacMutationOk,
    RbacPermissionRead,
    RbacPolicyPatch,
    RbacPolicyRead,
    RbacRoleCreate,
    RbacRolePermissionsPatch,
    RbacRolePresetRead,
    RbacRoleRead,
    RbacUserPermissionOverrideRead,
    RbacUserPermissionsPatch,
    RbacUserRead,
    RbacUserRolesPatch,
    RbacUsersResponse,
)
from src.application.rbac_api_locale import (
    locale_from_accept_language,
    msg_delete_global_forbidden,
    msg_delete_owner_forbidden,
    msg_delete_role_in_use,
    msg_role_duplicate,
    msg_unknown_permissions,
    validate_clinic_role_code,
)
from src.application.rbac_matrix import ROLE_PERMISSIONS, ROLE_PRESET_SOURCE_CODES
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE
from src.domain.entities.clinic import Clinic
from src.domain.entities.owner_integration_settings import OwnerIntegrationSettings
from src.domain.entities.permission import Permission
from src.domain.entities.rbac_audit_log import RbacAuditLog
from src.domain.entities.role import Role
from src.domain.entities.role_permission import RolePermission
from src.domain.entities.user_permission_grant import UserPermissionGrant
from src.domain.entities.user_role import UserRole
from src.infrastructure.database.rbac_repo_impl import RbacRepositoryImpl

_DEFAULT_RBAC_USERS_LIMIT = 500
_MAX_RBAC_USERS_LIMIT = 2000

router = APIRouter(
    prefix="/admin/rbac",
    tags=["admin-rbac-management"],
    dependencies=[Depends(require_permissions("rbac.manage"))],
)


def _permission_domain(code: str) -> str:
    if "." in code:
        return code.split(".", 1)[0]
    if "_" in code:
        return code.split("_", 1)[0]
    return "general"


def _assert_admin_ctx(context: AdminContext) -> tuple[UUID, UUID]:
    if context.clinic_id is None or context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Требуется контекст клиники")
    return context.clinic_id, context.user_id


async def _effective_clinic_pair(
    session: AsyncSession,
    context: AdminContext,
    current_admin: AdminUser,
    effective_clinic_id: UUID | None,
) -> tuple[UUID, UUID]:
    base_clinic_id, actor_admin_id = _assert_admin_ctx(context)
    eff = await resolve_effective_clinic_id(session, current_admin, base_clinic_id, effective_clinic_id)
    return eff, actor_admin_id


async def _log_audit(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    actor_admin_id: UUID,
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


@router.get("/catalog", response_model=RbacCatalogResponse)
async def get_rbac_catalog(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions("rbac.manage")),
    current_admin: AdminUser = Depends(get_current_admin),
    effective_clinic_id: UUID | None = Query(
        None,
        description="Клиника для управления RBAC (владелец сети — другая клиника той же организации)",
    ),
) -> RbacCatalogResponse:
    clinic_id, _ = await _effective_clinic_pair(session, context, current_admin, effective_clinic_id)
    perms_res = await session.execute(select(Permission).order_by(Permission.code.asc()))
    role_res = await session.execute(
        select(Role)
        .where((Role.clinic_id == clinic_id) | (Role.clinic_id.is_(None)))
        .order_by(Role.code.asc())
    )
    roles = list(role_res.scalars().all())
    permissions = list(perms_res.scalars().all())

    role_ids = [r.id for r in roles]
    perm_ids_by_role: dict[UUID, list[UUID]] = defaultdict(list)
    if role_ids:
        rp_res = await session.execute(
            select(RolePermission.role_id, RolePermission.permission_id).where(
                RolePermission.role_id.in_(role_ids)
            )
        )
        for role_id, permission_id in rp_res.all():
            perm_ids_by_role[role_id].append(permission_id)
    code_by_perm_id = {p.id: p.code for p in permissions}
    role_rows = [
        RbacRoleRead(
            id=r.id,
            code=r.code,
            name=r.name,
            clinic_id=r.clinic_id,
            permission_codes=sorted(
                [code_by_perm_id[pid] for pid in perm_ids_by_role.get(r.id, []) if pid in code_by_perm_id]
            ),
        )
        for r in roles
    ]
    perm_rows = [
        RbacPermissionRead(
            id=p.id,
            code=p.code,
            description=p.description,
            domain=_permission_domain(p.code),
        )
        for p in permissions
    ]
    known_perm_codes = {p.code for p in permissions}
    role_presets = [
        RbacRolePresetRead(
            code=code,
            permission_codes=sorted({c for c in ROLE_PERMISSIONS.get(code, []) if c in known_perm_codes}),
        )
        for code in ROLE_PRESET_SOURCE_CODES
    ]

    return RbacCatalogResponse(roles=role_rows, permissions=perm_rows, role_presets=role_presets)


@router.post("/roles", response_model=RbacRoleRead, status_code=status.HTTP_201_CREATED)
async def create_clinic_role(
    body: RbacRoleCreate,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions("rbac.manage")),
    current_admin: AdminUser = Depends(get_current_admin),
    effective_clinic_id: UUID | None = Query(
        None,
        description="Клиника для управления RBAC (владелец сети — другая клиника той же организации)",
    ),
    accept_language: str | None = Header(
        None,
        description="Язык сообщений об ошибках (ru|en). По умолчанию — английский.",
    ),
) -> RbacRoleRead:
    """Create a clinic-scoped custom role with an explicit permission set (audit-logged)."""
    locale = locale_from_accept_language(accept_language)
    clinic_id, actor_admin_id = await _effective_clinic_pair(session, context, current_admin, effective_clinic_id)

    normalized_code = body.code.strip().lower()
    try:
        validate_clinic_role_code(normalized_code, locale)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    dup_res = await session.execute(
        select(Role.id).where(Role.clinic_id == clinic_id, Role.code == normalized_code)
    )
    if dup_res.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg_role_duplicate(locale, normalized_code),
        )

    all_perms_res = await session.execute(select(Permission))
    all_perms = list(all_perms_res.scalars().all())
    perm_id_by_code = {p.code: p.id for p in all_perms}
    invalid_codes = [code for code in body.permission_codes if code not in perm_id_by_code]
    if invalid_codes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=msg_unknown_permissions(locale, invalid_codes),
        )

    role_id = uuid.uuid4()
    target_ids = {perm_id_by_code[c] for c in body.permission_codes}

    session.add(
        Role(
            id=role_id,
            clinic_id=clinic_id,
            code=normalized_code,
            name=body.name.strip(),
            description=(body.description.strip() if body.description else None) or None,
        )
    )
    for permission_id in sorted(target_ids):
        session.add(
            RolePermission(
                id=uuid.uuid4(),
                role_id=role_id,
                permission_id=permission_id,
            )
        )

    await _log_audit(
        session,
        clinic_id=clinic_id,
        actor_admin_id=actor_admin_id,
        action="role.create",
        entity_type="role",
        entity_id=str(role_id),
        before_payload=None,
        after_payload={
            "code": normalized_code,
            "name": body.name.strip(),
            "permission_codes": sorted(body.permission_codes),
        },
        note=body.note,
    )
    await session.commit()

    return RbacRoleRead(
        id=role_id,
        code=normalized_code,
        name=body.name.strip(),
        clinic_id=clinic_id,
        permission_codes=sorted(body.permission_codes),
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clinic_role(
    role_id: UUID,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions("rbac.manage")),
    current_admin: AdminUser = Depends(get_current_admin),
    effective_clinic_id: UUID | None = Query(
        None,
        description="Клиника для управления RBAC (владелец сети — другая клиника той же организации)",
    ),
    accept_language: str | None = Header(
        None,
        description="Язык сообщений об ошибках (ru|en). По умолчанию — английский.",
    ),
) -> None:
    """Delete a clinic-scoped custom role if no staff are assigned. Global roles cannot be deleted."""
    locale = locale_from_accept_language(accept_language)
    clinic_id, actor_admin_id = await _effective_clinic_pair(session, context, current_admin, effective_clinic_id)

    role_res = await session.execute(select(Role).where(Role.id == role_id))
    role = role_res.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.clinic_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=msg_delete_global_forbidden(locale),
        )
    if role.clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.code == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=msg_delete_owner_forbidden(locale),
        )

    cnt_res = await session.execute(
        select(func.count())
        .select_from(UserRole)
        .where(UserRole.role_id == role_id, UserRole.clinic_id == clinic_id)
    )
    if int(cnt_res.scalar_one() or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg_delete_role_in_use(locale),
        )

    await _log_audit(
        session,
        clinic_id=clinic_id,
        actor_admin_id=actor_admin_id,
        action="role.delete",
        entity_type="role",
        entity_id=str(role_id),
        before_payload={"code": role.code, "name": role.name},
        after_payload=None,
        note=None,
    )
    await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    await session.delete(role)
    await session.commit()


@router.get("/users", response_model=RbacUsersResponse)
async def get_rbac_users(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions("rbac.manage")),
    current_admin: AdminUser = Depends(get_current_admin),
    effective_clinic_id: UUID | None = Query(
        None,
        description="Клиника для управления RBAC (владелец сети — другая клиника той же организации)",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_RBAC_USERS_LIMIT, ge=1, le=_MAX_RBAC_USERS_LIMIT),
) -> RbacUsersResponse:
    clinic_id, _ = await _effective_clinic_pair(session, context, current_admin, effective_clinic_id)
    admins_res = await session.execute(
        select(AdminUser)
        .where(
            AdminUser.clinic_id == clinic_id,
            AdminUser.deleted_at.is_(None),
        )
        .order_by(func.coalesce(AdminUser.full_name, ""), AdminUser.email)
        .offset(skip)
        .limit(limit)
    )
    admins = list(admins_res.scalars().all())
    admin_ids = [a.id for a in admins]

    role_codes_by_admin: dict[UUID, list[str]] = defaultdict(list)
    if admin_ids:
        roles_res = await session.execute(
            select(UserRole.user_id, Role.code)
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.clinic_id == clinic_id, UserRole.user_id.in_(admin_ids))
        )
        for user_id, role_code in roles_res.all():
            role_codes_by_admin[user_id].append(role_code)

    override_rows_by_admin: dict[UUID, list[RbacUserPermissionOverrideRead]] = defaultdict(list)
    if admin_ids:
        ov_res = await session.execute(
            select(UserPermissionGrant.user_id, Permission.code, UserPermissionGrant.effect)
            .select_from(UserPermissionGrant)
            .join(Permission, Permission.id == UserPermissionGrant.permission_id)
            .where(
                UserPermissionGrant.clinic_id == clinic_id,
                UserPermissionGrant.user_id.in_(admin_ids),
            )
        )
        for user_id, permission_code, effect in ov_res.all():
            override_rows_by_admin[user_id].append(
                RbacUserPermissionOverrideRead(permission_code=permission_code, effect=effect)
            )

    rbac_repo = RbacRepositoryImpl(session)
    items: list[RbacUserRead] = []
    for admin in admins:
        effective = await rbac_repo.get_permission_codes_for_user(admin.id, clinic_id)
        items.append(
            RbacUserRead(
                admin_id=admin.id,
                full_name=admin.full_name,
                email=admin.email,
                role_codes=sorted(set(role_codes_by_admin.get(admin.id, []))),
                direct_overrides=sorted(
                    override_rows_by_admin.get(admin.id, []),
                    key=lambda x: x.permission_code,
                ),
                effective_permission_codes=sorted(effective),
            )
        )
    return RbacUsersResponse(items=items)


@router.patch("/roles/{role_id}/permissions", response_model=RbacMutationOk)
async def patch_role_permissions(
    role_id: UUID,
    body: RbacRolePermissionsPatch,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions("rbac.manage")),
    current_admin: AdminUser = Depends(get_current_admin),
    effective_clinic_id: UUID | None = Query(None),
) -> RbacMutationOk:
    clinic_id, actor_admin_id = await _effective_clinic_pair(session, context, current_admin, effective_clinic_id)
    role_res = await session.execute(select(Role).where(Role.id == role_id))
    role = role_res.scalar_one_or_none()
    if role is None or (role.clinic_id not in (None, clinic_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.code == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role 'owner' is immutable and cannot be edited",
        )

    all_perms_res = await session.execute(select(Permission))
    all_perms = list(all_perms_res.scalars().all())
    perm_id_by_code = {p.code: p.id for p in all_perms}
    invalid_codes = [code for code in body.permission_codes if code not in perm_id_by_code]
    if invalid_codes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown permission codes: {', '.join(sorted(invalid_codes))}",
        )

    current_res = await session.execute(
        select(RolePermission.permission_id).where(RolePermission.role_id == role_id)
    )
    current_ids = {row[0] for row in current_res.all()}
    target_ids = {perm_id_by_code[c] for c in body.permission_codes}
    if current_ids == target_ids:
        return RbacMutationOk(ok=True)

    await _log_audit(
        session,
        clinic_id=clinic_id,
        actor_admin_id=actor_admin_id,
        action="role.permissions.patch",
        entity_type="role",
        entity_id=str(role_id),
        before_payload={"permission_codes": sorted([p.code for p in all_perms if p.id in current_ids])},
        after_payload={"permission_codes": sorted(body.permission_codes)},
        note=body.note,
    )
    await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for permission_id in sorted(target_ids):
        session.add(
            RolePermission(
                id=uuid.uuid4(),
                role_id=role_id,
                permission_id=permission_id,
            )
        )
    await session.commit()
    return RbacMutationOk(ok=True)


@router.patch("/users/{user_id}/roles", response_model=RbacMutationOk)
async def patch_user_roles(
    user_id: UUID,
    body: RbacUserRolesPatch,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions("rbac.manage")),
    current_admin: AdminUser = Depends(get_current_admin),
    effective_clinic_id: UUID | None = Query(None),
) -> RbacMutationOk:
    clinic_id, actor_admin_id = await _effective_clinic_pair(session, context, current_admin, effective_clinic_id)
    admin_res = await session.execute(
        select(AdminUser).where(
            AdminUser.id == user_id,
            AdminUser.clinic_id == clinic_id,
            AdminUser.deleted_at.is_(None),
            AdminUser.employment_status == EMPLOYMENT_ACTIVE,
        )
    )
    admin = admin_res.scalar_one_or_none()
    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    is_owner_user = await user_has_owner_role(session, clinic_id, user_id)
    if is_owner_user and "owner" not in set(body.role_codes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner role cannot be removed from owner user",
        )

    await replace_user_roles_for_clinic(
        session,
        clinic_id=clinic_id,
        user_id=user_id,
        role_codes=body.role_codes,
        actor_admin_id=actor_admin_id,
        audit_action="user.roles.patch",
        entity_type="admin_user",
        entity_id=str(user_id),
        note=body.note,
        preserve_owner_role=False,
    )
    return RbacMutationOk(ok=True)


@router.patch("/users/{user_id}/permissions", response_model=RbacMutationOk)
async def patch_user_permissions(
    user_id: UUID,
    body: RbacUserPermissionsPatch,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions("rbac.manage")),
    current_admin: AdminUser = Depends(get_current_admin),
    effective_clinic_id: UUID | None = Query(None),
) -> RbacMutationOk:
    clinic_id, actor_admin_id = await _effective_clinic_pair(session, context, current_admin, effective_clinic_id)
    admin_res = await session.execute(
        select(AdminUser).where(
            AdminUser.id == user_id,
            AdminUser.clinic_id == clinic_id,
            AdminUser.deleted_at.is_(None),
        )
    )
    if admin_res.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    if await user_has_owner_role(session, clinic_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Personal permission overrides are not allowed for owner user",
        )

    perm_res = await session.execute(select(Permission))
    perm_by_code = {p.code: p.id for p in perm_res.scalars().all()}
    normalized: dict[str, str] = {}
    for row in body.overrides:
        if row.permission_code not in perm_by_code:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown permission code: {row.permission_code}",
            )
        if row.effect not in ("grant", "deny"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid effect for {row.permission_code}: {row.effect}",
            )
        normalized[row.permission_code] = row.effect

    current_res = await session.execute(
        select(UserPermissionGrant)
        .where(UserPermissionGrant.clinic_id == clinic_id, UserPermissionGrant.user_id == user_id)
    )
    current_rows = list(current_res.scalars().all())
    code_by_permission_id = {v: k for k, v in perm_by_code.items()}
    before = sorted(
        [
            {
                "permission_code": code_by_permission_id.get(r.permission_id, str(r.permission_id)),
                "effect": r.effect,
            }
            for r in current_rows
        ],
        key=lambda x: x["permission_code"],
    )
    await session.execute(
        delete(UserPermissionGrant).where(
            UserPermissionGrant.clinic_id == clinic_id,
            UserPermissionGrant.user_id == user_id,
        )
    )
    for permission_code, effect in sorted(normalized.items()):
        session.add(
            UserPermissionGrant(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                user_id=user_id,
                permission_id=perm_by_code[permission_code],
                effect=effect,
                created_by_admin_id=actor_admin_id,
            )
        )
    await _log_audit(
        session,
        clinic_id=clinic_id,
        actor_admin_id=actor_admin_id,
        action="user.permissions.patch",
        entity_type="admin_user",
        entity_id=str(user_id),
        before_payload={"overrides": before},
        after_payload={
            "overrides": [
                {"permission_code": c, "effect": e}
                for c, e in sorted(normalized.items())
            ]
        },
        note=body.note,
    )
    await session.commit()
    return RbacMutationOk(ok=True)


@router.get("/policies", response_model=RbacPolicyRead)
async def get_rbac_policies(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions("rbac.manage")),
    current_admin: AdminUser = Depends(get_current_admin),
    effective_clinic_id: UUID | None = Query(None),
) -> RbacPolicyRead:
    clinic_id, _ = await _effective_clinic_pair(session, context, current_admin, effective_clinic_id)
    clinic_res = await session.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = clinic_res.scalar_one_or_none()
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    owner_res = await session.execute(
        select(OwnerIntegrationSettings).where(OwnerIntegrationSettings.clinic_id == clinic_id)
    )
    owner_settings = owner_res.scalar_one_or_none()
    if owner_settings is None:
        owner_settings = OwnerIntegrationSettings(clinic_id=clinic_id)
    owner_brief_enabled = bool(owner_settings.owner_morning_brief_enabled)
    ai_supervisor_enabled = bool(owner_settings.ai_supervisor_enabled)
    return RbacPolicyRead(
        allow_patient_disable_discount_notifications=clinic.allow_patient_disable_discount_notifications,
        allow_patient_disable_reminders=clinic.allow_patient_disable_reminders,
        allow_patient_disable_all_notifications=clinic.allow_patient_disable_all_notifications,
        owner_morning_brief_enabled=owner_brief_enabled,
        morning_brief_send_at_utc=owner_settings.morning_brief_send_at_utc,
        owner_telegram_chat_id=owner_settings.owner_telegram_chat_id,
        ai_supervisor_enabled=ai_supervisor_enabled,
        ai_supervisor_send_at_utc=owner_settings.ai_supervisor_send_at_utc,
        ai_supervisor_recipient_chat_ids=list(owner_settings.ai_supervisor_recipient_chat_ids or []),
    )


@router.patch("/policies", response_model=RbacMutationOk)
async def patch_rbac_policies(
    body: RbacPolicyPatch,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions("rbac.manage")),
    current_admin: AdminUser = Depends(get_current_admin),
    effective_clinic_id: UUID | None = Query(None),
) -> RbacMutationOk:
    clinic_id, actor_admin_id = await _effective_clinic_pair(session, context, current_admin, effective_clinic_id)
    clinic_res = await session.execute(select(Clinic).where(Clinic.id == clinic_id))
    clinic = clinic_res.scalar_one_or_none()
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    owner_res = await session.execute(
        select(OwnerIntegrationSettings).where(OwnerIntegrationSettings.clinic_id == clinic_id)
    )
    owner_settings = owner_res.scalar_one_or_none()
    if owner_settings is None:
        owner_settings = OwnerIntegrationSettings(clinic_id=clinic_id)
        session.add(owner_settings)
        await session.flush()
    before = {
        "allow_patient_disable_discount_notifications": clinic.allow_patient_disable_discount_notifications,
        "allow_patient_disable_reminders": clinic.allow_patient_disable_reminders,
        "allow_patient_disable_all_notifications": clinic.allow_patient_disable_all_notifications,
        "owner_morning_brief_enabled": bool(owner_settings.owner_morning_brief_enabled),
        "morning_brief_send_at_utc": owner_settings.morning_brief_send_at_utc,
        "owner_telegram_chat_id": owner_settings.owner_telegram_chat_id,
        "ai_supervisor_enabled": bool(owner_settings.ai_supervisor_enabled),
        "ai_supervisor_send_at_utc": owner_settings.ai_supervisor_send_at_utc,
        "ai_supervisor_recipient_chat_ids": list(owner_settings.ai_supervisor_recipient_chat_ids or []),
    }
    if body.allow_patient_disable_discount_notifications is not None:
        clinic.allow_patient_disable_discount_notifications = body.allow_patient_disable_discount_notifications
    if body.allow_patient_disable_reminders is not None:
        clinic.allow_patient_disable_reminders = body.allow_patient_disable_reminders
    if body.allow_patient_disable_all_notifications is not None:
        clinic.allow_patient_disable_all_notifications = body.allow_patient_disable_all_notifications
    if body.owner_morning_brief_enabled is not None:
        owner_settings.owner_morning_brief_enabled = body.owner_morning_brief_enabled
    if body.morning_brief_send_at_utc is not None:
        owner_settings.morning_brief_send_at_utc = body.morning_brief_send_at_utc or None
    if body.owner_telegram_chat_id is not None:
        owner_settings.owner_telegram_chat_id = body.owner_telegram_chat_id or None
    if body.ai_supervisor_enabled is not None:
        owner_settings.ai_supervisor_enabled = body.ai_supervisor_enabled
    if body.ai_supervisor_send_at_utc is not None:
        owner_settings.ai_supervisor_send_at_utc = body.ai_supervisor_send_at_utc or None
    if body.ai_supervisor_recipient_chat_ids is not None:
        owner_settings.ai_supervisor_recipient_chat_ids = [
            x.strip() for x in body.ai_supervisor_recipient_chat_ids if x and x.strip()
        ]
    await _log_audit(
        session,
        clinic_id=clinic_id,
        actor_admin_id=actor_admin_id,
        action="policies.patch",
        entity_type="clinic",
        entity_id=str(clinic_id),
        before_payload=before,
        after_payload={
            "allow_patient_disable_discount_notifications": clinic.allow_patient_disable_discount_notifications,
            "allow_patient_disable_reminders": clinic.allow_patient_disable_reminders,
            "allow_patient_disable_all_notifications": clinic.allow_patient_disable_all_notifications,
            "owner_morning_brief_enabled": bool(owner_settings.owner_morning_brief_enabled),
            "morning_brief_send_at_utc": owner_settings.morning_brief_send_at_utc,
            "owner_telegram_chat_id": owner_settings.owner_telegram_chat_id,
            "ai_supervisor_enabled": bool(owner_settings.ai_supervisor_enabled),
            "ai_supervisor_send_at_utc": owner_settings.ai_supervisor_send_at_utc,
            "ai_supervisor_recipient_chat_ids": list(owner_settings.ai_supervisor_recipient_chat_ids or []),
        },
        note=body.note,
    )
    await session.commit()
    return RbacMutationOk(ok=True)


@router.get("/audit", response_model=list[RbacAuditLogRead])
async def get_rbac_audit(
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(require_permissions("rbac.manage")),
    current_admin: AdminUser = Depends(get_current_admin),
    effective_clinic_id: UUID | None = Query(None),
) -> list[RbacAuditLogRead]:
    clinic_id, _ = await _effective_clinic_pair(session, context, current_admin, effective_clinic_id)
    rows_res = await session.execute(
        select(RbacAuditLog)
        .where(RbacAuditLog.clinic_id == clinic_id)
        .order_by(RbacAuditLog.created_at.desc())
        .limit(limit)
    )
    rows = list(rows_res.scalars().all())
    actor_ids = [r.actor_admin_id for r in rows if r.actor_admin_id is not None]
    names_by_id: dict[UUID, str | None] = {}
    if actor_ids:
        actors_res = await session.execute(select(AdminUser.id, AdminUser.full_name).where(AdminUser.id.in_(actor_ids)))
        names_by_id = {row[0]: row[1] for row in actors_res.all()}
    return [
        RbacAuditLogRead(
            id=r.id,
            actor_admin_id=r.actor_admin_id,
            actor_admin_name=names_by_id.get(r.actor_admin_id) if r.actor_admin_id else None,
            action=r.action,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            before_payload=r.before_payload,
            after_payload=r.after_payload,
            note=r.note,
            created_at=r.created_at,
        )
        for r in rows
    ]

