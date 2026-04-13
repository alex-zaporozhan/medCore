# Публичные машинные коды ошибок API (`code` в JSON)

> **Назначение (1c-Q2 / §28):** единый контракт для клиентов, интеграций и SEC: поле **`code`** в теле ответа — **lowercase `snake_case`**, стабильное между релизами (меняется только при явной версии API).  
> **Источник нормализации:** `normalize_api_error_code` в [`src/core/api_error_codes.py`](../../src/core/api_error_codes.py); единое тело 4xx/5xx из `HTTPException` — [`src/core/http_exception_handler.py`](../../src/core/http_exception_handler.py) (`unified_http_exception_handler`), подключение в [`src/main.py`](../../src/main.py).

## Форма ответа (типовой 4xx/5xx из `HTTPException`)

```json
{
  "detail": "Человекочитаемое сообщение",
  "code": "entitlement_required",
  "details": { "field": "stream_id", "entitlement_key": "tasks.kanban" },
  "trace_id": "…"
}
```

- **`detail`** — всегда строка (не объект).
- **`details`** — опционально: дополнительные поля из исходного `HTTPException.detail` (например `site_key` для `captcha_required`, `field` для задач). Поля `code`, `message`, `detail`, **`trace_id`** в деталях не дублируются: `trace_id` выносится наверх.
- **`trace_id`** — сначала `request.state.trace_id` (middleware), иначе строка из тела `HTTPException.detail`, если роутер её положил в dict.
- **`code` и `Enum`:** в Python в `HTTPException.detail` иногда передаётся член перечисления (например `BookingErrorCode`). У `Enum` строковое представление — **не** API-значение; обработчик берёт **`.value`** и нормализует в `snake_case`.

## 422 (валидация Pydantic)

- **`code`:** `validation_error`
- **`errors`:** массив элементов FastAPI/Pydantic (без `ctx`).

## 500 (необработанное исключение)

- **`code`:** `internal_server_error`

## Коды по умолчанию (если в `HTTPException` не задан свой `code`)

| HTTP | `code` |
|------|--------|
| 400 | `bad_request` |
| 401 | `unauthorized` |
| 403 | `forbidden` |
| 404 | `not_found` |
| 405 | `method_not_allowed` |
| 409 | `conflict` |
| 422 | `validation_error` |
| 429 | `rate_limited` |

## Частые доменные коды (примеры; полный перечень — grep по `detail={"code":`)

| `code` | Контекст |
|--------|----------|
| `entitlement_required` | гейт опции (см. `organization_entitlement_access`) |
| `box_forbidden` | редакция Box / запрет SKU |
| `captcha_required` | Turnstile после soft rate limit (`auth`, `integrations_gateway`) |
| `clinic_forbidden` | несовпадение клиники и JWT |
| `platform_webhook_invalid_signature` | контур B, секрет webhook |
| `billing_revoked` | повтор провижининга при отозванном биллинге |

## Контур A — `POST /api/v1/payments/webhook` (YooKassa, запись на приём)

| `code` | HTTP | Контекст |
|--------|------|----------|
| `webhook_forbidden` | 403 | задан `PATIENT_PAYMENT_WEBHOOK_SECRET`, но заголовок **X-Patient-Payment-Webhook-Secret** отсутствует или неверен (U-006) |
| `rate_limited` | 429 | лимит по IP на contour A webhook (`RATE_PATIENT_PAYMENT_WEBHOOK_*`) |
| `invalid_json` | 400 | тело не JSON |
| `webhook_processing_failed` | 500 | ошибка после разбора JSON (обработка в сервисе) |

Успех: `200`, тело `{"status":"ok"}` — см. `PaymentWebhookOkResponse` в коде.

**Платежи и ошибки брони (create payment и др.):** каталог и коды — по необходимости сверять с [`PLATFORM_BILLING_ERROR_CATALOG.md`](./PLATFORM_BILLING_ERROR_CATALOG.md) (в основном контур checkout/биллинг платформы; не путать с webhook A выше).

## Omnichannel (admin API, примеры)

| `code` | Контекст |
|--------|----------|
| `omni_chat_already_claimed` | чат уже назначен другому админу |
| `omni_chat_not_claimed` | закрытие / resolve без claim |
| `omni_chat_active_lease` | активная lease-сессия оператора |
| `omni_reply_channel_unresolved` | нет канала для исходящего ответа |
| `omni_send_rate_limited` | лимит отправки сообщений |
| `omni_assignee_invalid` | неверный query `assignee` |
| `omni_channel_type_invalid` | неверный `channel_type` |
| `omni_closure_tag_invalid` | теги закрытия не из этой клиники |
| `omni_analytics_date_invalid` | формат дат аналитики |
| `omni_analytics_date_range_invalid` | `date_from` ≥ `date_to` |

## Public embed (`/api/v1/public/embed/v1/…`)

| `code` | HTTP | Контекст |
|--------|------|----------|
| `embed_ai_input_too_long` | 400 | превышен `embed_ai_max_input_tokens`; в **`details`**: `tokens_estimated_input`, `max_input_tokens` |
| `rate_limited` | 429 | лимит по IP на публичный контур embed |
| `entitlement_required` | 403 | нет `ai.assistant.chat` или `ai.rag.org_kb` у организации ключа |
| `unauthorized` | 401 | неверный или отсутствующий Bearer (embed API key) |

См. [`src/api/v1/routers/public_embed.py`](../../src/api/v1/routers/public_embed.py).

## OpenAPI (1c-Q4 — частично)

В `/openapi.json` (неprod) зарегистрированы общие схемы: **`ApiHttpErrorBody`**, **`ApiValidationErrorBody`**, **`ApiInternalErrorBody`** — см. [`src/core/openapi_error_schemas.py`](../../src/core/openapi_error_schemas.py). Для **всех** операций под префиксом API v1 к операциям добавлены стандартные `responses` (в т.ч. 403 с `$ref` на `ApiHttpErrorBody`, 422 на `ApiValidationErrorBody`, 500 на `ApiInternalErrorBody`) через `STANDARD_OPENAPI_ERROR_RESPONSES` и `app.include_router(api_router, ..., responses=...)`. **2026-04-07:** у `POST …/assistant/message` и `POST …/rag/search` — схемы успешного ответа (`EmbedAssistantMessageResponse`, `EmbedRagSearchResponse`) и **example** для 400 `embed_ai_input_too_long` (ассистент). Опционально: `example` для типовых 403 гейтов и прочих публичных путей.

## Правила расширения

1. Новые значения **`code`** — только `snake_case`, без пробелов; по возможности префикс домена (`commerce_`, `embed_`, …). В исходниках допускается временно `SCREAMING_SNAKE` в `HTTPException.detail`; **в JSON ответа** поле `code` всё равно приводится к `snake_case` — предпочтительно писать сразу каноничный литерал в коде (как для admin omni).
2. Не помещать **`organization_id` / PII** в `details` для публичных путей без политики SEC.
3. Крупные смены контракта — версия API ([`API_VERSIONING_POLICY.md`](./API_VERSIONING_POLICY.md)).
