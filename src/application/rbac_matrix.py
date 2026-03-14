"""Explicit RBAC roles/permissions matrix used across the backend.

This module documents the canonical list of permissions and which base
roles (`owner`, `manager`, `admin`, `doctor`) should have them.

The initial seed in Alembic migration `rbac_tasks_0001_init` mirrors
the same matrix.

Procedure when matrix evolves:
1. Update PERMISSIONS and ROLE_PERMISSIONS in this file.
2. Add a new Alembic migration that:
   - inserts any new permissions (INSERT ... ON CONFLICT (code) DO NOTHING);
   - for new roles: insert into roles, then link permissions;
   - for existing roles: INSERT new role_permissions for new permission codes,
     or run a data migration that syncs from this module (e.g. script that
     reads ROLE_PERMISSIONS and upserts role_permissions).
3. Keep require_permissions(...) usage in routers aligned with these codes
   (see DEV_PROMPTS_RBAC_AND_TASKS.md and ARCH_RBAC_AND_TASKS.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class PermissionDef:
    code: str
    description: str


# Full list of system permissions.
PERMISSIONS: Final[list[PermissionDef]] = [
    PermissionDef("view_dashboard", "Просмотр дашборда"),
    PermissionDef("view_reports", "Просмотр отчётов"),
    PermissionDef("view_finance", "Просмотр финансовых данных"),
    PermissionDef("manage_finance", "Управление финансовыми настройками и операциями"),
    PermissionDef("view_payroll", "Просмотр данных по зарплате"),
    PermissionDef("manage_payroll", "Управление зарплатными политиками и выплатами"),
    PermissionDef("view_inventory", "Просмотр склада и остатков"),
    PermissionDef("manage_inventory", "Управление складом и остатками"),
    PermissionDef("view_crm", "Просмотр CRM и лидов"),
    PermissionDef("manage_crm", "Управление стадиями и данными CRM"),
    PermissionDef("view_tasks", "Просмотр задач"),
    PermissionDef("manage_tasks", "Создание и изменение задач"),
    PermissionDef("assign_tasks", "Назначение задач другим пользователям"),
    PermissionDef("view_loyalty", "Просмотр модулей лояльности"),
    PermissionDef("manage_loyalty", "Управление программами лояльности"),
    PermissionDef("view_forms", "Просмотр форм и подписей"),
    PermissionDef("manage_forms", "Управление шаблонами форм"),
    PermissionDef("export_forms", "Экспорт форм и подписей пациента"),
    PermissionDef("view_marketing_analytics", "Просмотр маркетинговой аналитики"),
    PermissionDef("manage_marketing_campaigns", "Управление маркетинговыми кампаниями"),
    PermissionDef("view_ai_settings", "Просмотр AI-настроек"),
    PermissionDef("manage_ai_settings", "Управление AI-настройками"),
]


# Role → permissions mapping.
# NOTE: `owner` is defined as "all permissions".
ROLE_PERMISSIONS: Final[dict[str, list[str]]] = {
    # Owner: all permissions.
    "owner": [p.code for p in PERMISSIONS],
    # Manager: everything except the most critical global/financial AI & ERP settings.
    "manager": [
        "view_dashboard",
        "view_reports",
        "view_finance",
        "view_payroll",
        "view_inventory",
        "view_crm",
        "view_tasks",
        "manage_tasks",
        "assign_tasks",
        "view_loyalty",
        "manage_loyalty",
        "view_forms",
        "manage_forms",
        "export_forms",
        "view_marketing_analytics",
        "manage_marketing_campaigns",
        "view_ai_settings",
    ],
    # Admin: no finance and no global settings.
    "admin": [
        "view_dashboard",
        "view_crm",
        "manage_crm",
        "view_tasks",
        "manage_tasks",
        "assign_tasks",
        "view_inventory",
        "view_loyalty",
        "view_forms",
        "view_marketing_analytics",
    ],
    # Doctor: minimal read-only access to tasks (scoped by visibility rules).
    "doctor": [
        "view_tasks",
    ],
}


ALL_PERMISSION_CODES: Final[set[str]] = {p.code for p in PERMISSIONS}

