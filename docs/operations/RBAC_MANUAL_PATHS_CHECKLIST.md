# Чеклист: RBAC в обход `require_permissions` (SSE, webhooks, query-токены)

> **Назначение (10-Q6 / §28):** пути, где токен передаётся иначе (query, короткий JWT), часто **не** проходят через стандартный `Depends(require_permissions(...))`. Любая ручная проверка должна вызывать **актуальные** методы `RbacServiceImpl`.

## Перед merge нового такого маршрута

1. Права читаются через `RbacServiceImpl` + `RbacRepositoryImpl` и **существующие** методы (например `get_permissions_for_user(user_id, clinic_id)`), а не устаревшие или выдуманные имена.
2. `clinic_id` / контекст тенанта взят из того же источника доверия, что и для обычного admin JWT (не из необоснованного query).
3. Добавлен **интеграционный** тест с HTTP-клиентом: 403 без права, 200 с правом.
4. При изменении `RbacServiceImpl` — grep по репозиторию на вызовы из SSE/webhook/gateway.

## Известные точки (поддерживать в актуальном состоянии)

- `GET /api/v1/admin/omni-chats/events` — SSE; проверка `omni.inbox.manage` через `get_permissions_for_user`.

## Ссылки

- [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](../architecture/arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md)
- `src/application/services/rbac_service.py`
