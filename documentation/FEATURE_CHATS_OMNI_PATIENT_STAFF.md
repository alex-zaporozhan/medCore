# Чаты: омни-инбокс, пациент, admin chat и внутренний чат персонала

> **Версия:** 2026-04-02. **Важно:** четыре разных контура; в текстах для пользователя их не смешивать.

## Внутренний чат персонала (staff)

- **Назначение:** общение сотрудников, лента, календарь, база знаний (staff collaboration).
- **API:** модуль `admin_staff_collab`, префикс `/admin/staff`. Детали путей: [router_surface/INDEX.md](./router_surface/INDEX.md).
- **UI:** `ROUTE_PATHS.admin.staffChat` → `/admin/staff-chat`. В `routePaths.ts` явно сказано: это не омниканальный инбокс пациентов.
- **Метрики в роутере:** например `chat_rate_limited_total`, `chat_upload_rejected_total` (см. INDEX).

## Омниканальный инбокс

- **API:** `admin_omni_chat` — префикс `/admin/omni-chats`; также `admin_omni_chat_closure_tags`, `admin_omni_tools`, `integrations_gateway`, модули `owner_omni_*`.
- **UI:** `/admin/omni-chat`, настройки — сегменты `omni-channels`, `omni-ai-settings` и др.
- **Метрики:** семейство `omni_*` в `src/core/metrics.py`.

## Чат пациента (PWA)

- **API:** `patient_chat` — `/patient/chat`.
- **UI:** `/app/chat`.

## Admin chat (отдельный контур)

- **API:** `admin_chat` — `/admin/chat`. Не называть «омни» без проверки кода и OpenAPI.

## Сводка

| Контур | Префикс v1 | Пример UI |
|--------|------------|-----------|
| Персонал | `/admin/staff` | `/admin/staff-chat` |
| Омни | `/admin/omni-chats` + смежные | `/admin/omni-chat` |
| Пациент | `/patient/chat` | `/app/chat` |
| Admin chat | `/admin/chat` | по факту во фронте |

---

Reference: [PRODUCT_KNOWLEDGE_BASE.md](./PRODUCT_KNOWLEDGE_BASE.md) · [SCRIBE_ROUTER_CHECKLIST.md](./SCRIBE_ROUTER_CHECKLIST.md)
