# SEC_RBAC_SPEC — роли, permissions, инварианты (QA_ARCH W7 SR8)

Канонический список permissions и назначение по ролям живёт в коде: `src/application/rbac_matrix.py` (`PERMISSIONS`, `ROLE_PERMISSIONS`).

## Правила разработки (SR1)

- Новый чувствительный эндпоинт → `require_permissions(...)` в роутере и строка в `docs/artifacts/SEC_RBAC_ENDPOINTS_MAP.md` (или обновление карты в том же PR).
- После добавления нового permission в роутерах обновить **`docs/artifacts/sec_rbac_router_permissions.txt`**: `python scripts/audit_rbac_endpoints.py --write`; CI-регресс: `pytest tests/application/test_sec_rbac_router_permissions_inventory.py`.
- Матрица в Alembic seed должна оставаться согласованной с `rbac_matrix.py` (новые permissions — миграция `INSERT ... ON CONFLICT` + связи `role_permissions`).

## UI (SR2)

- Скрывать кнопки/действия без права (fail-closed); сервер остаётся источником истины.

## Immutable audit (SR4)

Критичные мутации покрываются доменными журналами и флагами, например:

- CRM: `compliance_crm_audit_enabled` → `CrmLeadEstimatedValueAudit` (см. CRM_MONEY H6).
- ERP: `ErpAggregateManualRefreshAudit` для ручного refresh витрин.
- Omni: `omni_audit_logs` для интеграций и модерации.

Универсальная таблица «все мутации» не заменяет эти контуры; новые критичные пути — по ADR.

## Фоновые задачи / Celery (SR7)

- Задачи не расширяют права `system_ai` сверх матрицы; контекст сервиса ограничен явным набором permissions в коде вызова.

## Временные делегирования (SR6)

Вне базового RBAC; отдельный эпик (см. `QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md` SR6).

## Связанные файлы

- Карта эндпоинтов: `docs/artifacts/SEC_RBAC_ENDPOINTS_MAP.md`
- Архив задач: `docs/artifacts/ARCH_DEV_SEC_RBAC_022_TASKS.md`
