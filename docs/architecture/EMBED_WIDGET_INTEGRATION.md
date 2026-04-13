# Встраивание виджета и внешние webhooks (Phase 1e, §24)

> **Связь:** [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) §24; фаза [arch_plan/06_PHASE_1E_LIFECYCLE_EMBED.md](./arch_plan/06_PHASE_1E_LIFECYCLE_EMBED.md); гейт тарифа **`omni.embed.bundle`**.

## Предварительные условия

1. У организации в SaaS-режиме есть entitlement **`omni.embed.bundle`** (строки в `organization_entitlements`), либо установка в **legacy** / **box** без enforcement (см. `organization_entitlement_access`).
2. Администратор с `organization_id` открывает раздел API (реализовано как префикс **`/api/v1/admin/organization/embed`**).

## API keys (виджет / сервер-сервер)

1. `POST /api/v1/admin/organization/embed/api-keys` — в ответе поле **`token`** показывается **один раз**, формат `dceb.<uuid>.<secret>`.
2. Проверка ключа: `GET /api/v1/public/embed/v1/session` с заголовком `Authorization: Bearer <token>`.
3. Список и отзыв: `GET .../api-keys`, `POST .../api-keys/{id}/revoke`.

## Webhook-инбокс (каналы вроде Bitrix24)

1. Узнать сегмент пути: `GET /api/v1/admin/organization/embed/settings` → **`inbound_route_token`** (UUID).
2. Выпустить секрет: `POST /api/v1/admin/organization/embed/webhook-secret/rotate` → **`webhook_secret`** (один раз).
3. Принимающий endpoint (пример):

   `POST /api/v1/public/embed/v1/hooks/{inbound_route_token}/inbox`

   Заголовок: `Authorization: Bearer <webhook_secret>`. Тело: JSON (сырой body участвует в HMAC и в SHA256 для идемпотентности).

4. Пока секрет не выпущен, inbox отвечает **404** с кодом `embed_webhook_not_configured`.

5. **Опционально `X-Embed-Signature: v1=<hex>`** — HMAC-SHA256 от **raw body**, ключ = тот же plaintext, что и Bearer secret. Если в окружении задано **`EMBED_WEBHOOK_SIGNATURE_REQUIRED=true`**, заголовок обязателен.

6. **Идемпотентность:** заголовки **`X-Embed-Idempotency-Key`** или **`Idempotency-Key`** (до 128 символов). Повтор с тем же ключом и тем же телом → ответ `duplicate: true`; тот же ключ и другое тело → **409** `embed_webhook_idempotency_conflict`.

7. **Админка:** раздел **«Встраивание (embed)»** — `/admin/embed` (SPA): URL inbox, ротация secret, список/создание/отзыв API keys. В SaaS enforcement пункт виден при наличии **`omni.embed.bundle`**; в редакции **Box** сегмент скрыт (сервер также отдаёт `box_forbidden` на API).

## Ограничения и дальнейшая работа

- **Rate limit:** `rate_embed_public_*`, `rate_embed_webhook_token_*`; для **GET session** опционально отдельно **`rate_embed_session_ip_*`** (0 = тот же потолок, что у `rate_embed_public_*`). См. `Settings` / `.env`.
- **Размер тела inbox:** `embed_webhook_max_body_bytes` (по умолчанию 1 MiB); превышение → **413** `embed_webhook_payload_too_large`. При корректном заголовке **`Content-Length`** отказ возможен до чтения тела; без CL проверка после `read()` (для жёсткого лимита на периметре используйте reverse-proxy).
- **Метрики (Prometheus):** `embed_public_request_total{endpoint,result}` — `endpoint` ∈ `health` | `session` | `webhook_inbox`.
- **Стабильные нижний регистр `code` в JSON** для всех публичных клиентов — см. бэклог 1c B2/B4 (`main.py` может нормализовать регистр в ответе).
- **RAG / AI** по ключам `ai.assistant.chat`, `ai.rag.org_kb` — отдельные эпики после выбора vector store (фаза 1e, п.3 плана).

**Версия:** 2026-04-06 (@DEV) · **2026-04-13** — UI админки, HMAC, ledger идемпотентности.
