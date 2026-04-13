# Фаза 1e — жизненный цикл арендатора и embed-монопродукт (Phase_1e_Lifecycle_Embed)

**Узлы МП mermaid:** `Offboarding_export_tenant`, `Embed_chat_Bitrix_AI_RAG`.  
**Связь МП:** §24, §15b 1e, §2d M7, [TENANT_OFFBOARDING_AND_EXPORT.md](../../operations/TENANT_OFFBOARDING_AND_EXPORT.md).

## Архитектурный целевой образ

### Offboarding и экспорт

1. Процедура **приостановки / архивации / удаления** по политике; отзыв API keys (МП §24.4, §7).
2. **Экспорт** machine-readable, сроки, объём; связь с правом субъекта до активации (privacy) — операционный документ + продуктовый бэклог автоматизации (МП §2d п.7).

### Embed / моно-пакет (§24)

1. **Виджет** + документация встраивания; **API key** с ротацией и отзывом (МП §24.1).
2. **Битрикс24** и прочие каналы — подпись webhook, идемпотентность, rate limits.
3. **AI в чате** — Sanitizer, лимиты «Tokenizer», флаги org/канал (МП §24.2).
4. **RAG** — отдельный эпик: индекс строго per `organization_id`, негативные тесты утечки (МП §24.3).
5. Все публичные маршруты embed — **rate limiting**, защита от replay (МП §24.4, §17).

## Порядок работ @DEV

1. Убедиться, что ключи **`omni.embed.bundle`**, **`ai.assistant.chat`**, **`ai.rag.org_kb`** согласованы с БД entitlements (после 1c) или временной политикой.
2. Реализовать/дополнить backend для API keys и webhook-инбокса с учётом §24.1–24.2.
3. **RAG §24.3:** v1 — хранение и поиск по `organization_id` без vector store ([STREAM_PRODUCT_RAG_24_EPIC.md](./STREAM_PRODUCT_RAG_24_EPIC.md)); выбор vector store и SEC-углубление — следующий эпик, не блокирует остальной 1e.
4. Связать операционный экспорт с UI Основателя/Владельца по продуктовому скоупу.

## DoD (МП §15b 1e)

- Черновик **offboarding + export** в `docs/operations` (файл или раздел DR_RUNBOOK) + ссылка из INDEX/RELEASE.
- Ключи §24 отражены в каталоге и гейтах API (когда 1c доступна).

## Связка QA_ARCH (наследие 1c — публичный/embed периметр)

Перед расширением публичных маршрутов embed закрыть **контракт ошибок** (форма 403, стабильные `code`, предпочтительно lower-case в JSON), иначе внешние интеграции зафиксируют расхождения. Якоря: [04_PHASE_1C_ENTITLEMENTS.md](./04_PHASE_1C_ENTITLEMENTS.md) B2/B4, [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **1c-Q2**, **1c-Q4**; [backend/api_layer.md](../backend/api_layer.md).

## Ссылки

- [frontend/shared_ui_and_pwa.md](../frontend/shared_ui_and_pwa.md)
- [LEAD_RF_PACKAGES_AND_PRICING_FIRST_LAUNCH.md](../LEAD_RF_PACKAGES_AND_PRICING_FIRST_LAUNCH.md) (пресеты РФ)
- [EMBED_WIDGET_INTEGRATION.md](../EMBED_WIDGET_INTEGRATION.md) — черновик интеграции API key + webhook inbox.

## Статус @DEV (2026-04-13)

- **Каталог:** миграция `20260412_phase1e_embed_catalog_and_keys` — в `platform_catalog_options` добавлены **`omni.embed.bundle`**, **`ai.assistant.chat`**, **`ai.rag.org_kb`**, а также **`marketing.attribution`** и **`retention.bundle`** (согласование с конструктором планов и гейтами 1c).
- **Бэкенд:** таблицы `organization_embed_settings`, `organization_embed_api_keys`, **`organization_embed_inbound_receipts`** (миграция `20260413_phase1e_embed_inbound_idempotency`); роутеры `admin_embed`, `public_embed`; опциональный **HMAC** (`X-Embed-Signature`), **идемпотентность** inbox; `embed_webhook_signature_required` в config.
- **Фронт:** `/admin/embed` — ключи, webhook URL, ротация secret; навигация + **`omni.embed.bundle`** в `adminEntitlementNav`; сегмент **скрыт в Box** (`VITE_EDITION`).
- **Тесты:** `tests/api/test_phase1e_embed.py`; workflow entitlements включает этот файл.
- **DoD документ:** [TENANT_OFFBOARDING_AND_EXPORT.md](../../operations/TENANT_OFFBOARDING_AND_EXPORT.md) (шаг отзыва ключей через UI/API) + ссылки в INDEX / DR / RELEASE.

## Усиления @QA_ARCH (2026-04-13)

- Порядок **webhook inbox:** аутентификация Bearer **до** чтения тела; лимит **`embed_webhook_max_body_bytes`** + 413 `embed_webhook_payload_too_large`; опционально отдельный rate limit **`rate_embed_session_ip_limit`** для GET `/session`.
- Метрика **`embed_public_request_total`**; структурированный 404 на revoke ключа (`embed_api_key_not_found`).
- Бэклог полного закрытия: [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (**1e-F1…F7**).

## Срез Stream 1e + Phase 3+ @DEV / @QA_ARCH (2026-04-07)

- **Эпик RAG §24.3:** [STREAM_PRODUCT_RAG_24_EPIC.md](./STREAM_PRODUCT_RAG_24_EPIC.md) — контракт изоляции по `organization_id`; v1 без vector store; негативный тест `tests/api/test_rag_org_isolation.py`.
- **Миграция:** `20260424_stream_1e_phase3_plus_tables` (аудит embed, RAG KB, industry/import/export audit и пр.).
- **Наблюдаемость:** алерты в `deploy/prometheus/dental_booking_alerts.yml`, ряд «Public embed» в `deploy/grafana/dashboards/dental_booking_observability_w1_w2.json`.
- **Сводный отчёт приёмки:** [STREAM_PRODUCT_RAG_24_EPIC.md](./STREAM_PRODUCT_RAG_24_EPIC.md), [08_PHASE_3_PLUS.md](./08_PHASE_3_PLUS.md). **Колонка «Статус» по строкам 1e-F1…F7** — в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (обновлено 2026-04-07).

## Следующие этапы (зафиксировано QA_ARCH)

**Источник истины по статусу строк** — таблица «Фаза 1e» в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (**1e-F1…1e-F7**). Ниже — навигация «что делаем потом», без дублирования колонок таблицы.

| Фокус | ID в бэклоге | Смысл |
|--------|----------------|--------|
| RAG / vector store | **1e-F1** | v1: per-org KB + SQL + негативный тест ([STREAM_PRODUCT_RAG_24_EPIC](./STREAM_PRODUCT_RAG_24_EPIC.md)); хвост: vector store, audit KB |
| AI в чате | **1e-F2** | Sanitizer и tokenizer-лимиты §24.2 — закрыто в срезе 2026-04-07 (см. бэклог) |
| Экспорт / offboarding в продукте | **1e-F3** | UI/API заявок — **partial**; полная автоматизация PII — бэклог |
| Аудит embed | **1e-F4** | БД-аудит ключей/webhook — закрыто в срезе 2026-04-07 |
| RBAC embed | **1e-F5** | Узкие permissions — закрыто в срезе 2026-04-07 |
| Наблюдаемость embed | **1e-F6** | Prometheus + Grafana — закрыто в срезе 2026-04-07 |
| Защита inbox на edge | **1e-F7** | Потолок в приложении + nginx-фрагмент — закрыто в срезе 2026-04-07 |

**Сквозное до расширения публичного/embed API:** **1c-Q2** (единый регистр стабильных `code`) — **done**. **1c-Q4:** глобальные `responses` на все v1-операции — **done**; для `POST …/public/embed/v1/assistant/message` и `POST …/rag/search` добавлены схемы успеха и пример `embed_ai_input_too_long` в OpenAPI — остаток **1c-Q4** (примеры на остальные публичные пути, в т.ч. 403 гейтов) — в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md), секция 1c.

**Связка с импортом / §25:** полный конвейер данных и аудит — **3-F1…3-F6** в бэклоге и [08_PHASE_3_PLUS.md](./08_PHASE_3_PLUS.md) (пересечение с экспортом арендателя через **1e-F3** и порядок работ в Phase 3+).

**Вне минимального DoD 1e (напоминание):** RAG §24.3; полный UI экспорта; единый регистр `code` — всё перечислено в строках таблицы выше, не считать закрытым без обновления **Статус** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md).
