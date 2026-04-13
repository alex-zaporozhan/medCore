# QA_REPORT — 1b-E3b (контур B, реестр веток YooKassa + reconcile)

**Дата:** 2026-04-07. **Эпик:** [STREAM_1B_COMMERCE_EPICS.md](../architecture/arch_plan/STREAM_1B_COMMERCE_EPICS.md) **1b-E3b**. **Модуль:** [platform_subscription_billing.md](../architecture/modules/platform_subscription_billing.md).

## Реестр веток (источник истины в репозитории)

| Артефакт | Назначение |
|----------|------------|
| [platform_yookassa_webhook_b_branches.yaml](../architecture/contracts/platform_yookassa_webhook_b_branches.yaml) | Событие / статус API → действие → HTTP-ответ |
| [platform_subscription_billing.md](../architecture/modules/platform_subscription_billing.md) §12.1 | Матрица статусов Payment → обработчик |
| OpenAPI `POST .../platform/billing/webhooks/{provider}` | Примеры тел уведомлений (`platform_billing.py`) |
| [SEC_PRODUCT_CONTOUR_B_REGISTRY.md](./SEC_PRODUCT_CONTOUR_B_REGISTRY.md) | Реестр SEC + Product, подписи приёмки (PRC-B2) |

## Покрытие pytest (ветки, не только unknown provider)

Файл: `tests/api/test_platform_billing.py`.

| Сценарий | Тест |
|----------|------|
| Секрет / 403 | `test_platform_billing_webhook_requires_secret` |
| `succeeded` идемпотентность | `test_platform_billing_webhook_succeeded_twice_idempotent` |
| `canceled` | `test_platform_billing_webhook_canceled_updates_payment_only` |
| `refunded` / ADR-012 | `test_platform_billing_refund_*`, `test_platform_retry_provision_409_when_billing_revoked` |
| `pending` (игнор lifecycle) | косвенно ветки non-success; явный `waiting_for_capture` — `test_platform_billing_webhook_waiting_for_capture_updates_payment_only` |
| Гейт каталога (webhook) | `test_platform_webhook_tariff_gate_*` |
| Гейт при retry (1b-E5) | `test_platform_force_retry_409_when_execute_catalog_gate_blocks` |
| Rate limit (1b-E6 app-layer) | `test_platform_billing_webhook_rate_limit_second_request_429` |
| Unknown provider 404 | `test_platform_billing_webhook_unknown_provider_returns_404` |

## Reconcile UI

- Маршрут: `/platform/provision-queue` → `PlatformFounderProvisionQueuePage.tsx`.
- API: `GET /api/v1/platform/internal/provision-queue`, `POST .../retry-provision`.
- Очередь включает intent с `pending_payment` и `provision_last_error` вида `tariff_gate:*` (после 1b-E3b).

## Метрики / алерты (связка 1b-E4)

- Счётчики: `platform_billing_webhook_total`, `platform_provision_attempt_total` (в т.ч. **`result=permanent_block`** при «вечных» ошибках гейта), `platform_provision_retry_scheduled_total`, и др. (см. модуль §10).
- Gauges на `/metrics`: `platform_signup_intent_stuck`, `platform_signup_intent_dead_letter` (обновление при scrape + throttle `PLATFORM_BILLING_METRICS_DB_REFRESH_MIN_INTERVAL_SECONDS`).
- Алерты: `deploy/prometheus/dental_booking_alerts.yml` (backlog / DLQ).
- Панели Grafana: ряд **Platform SaaS — contour B** в `deploy/grafana/dashboards/dental_booking_observability_w1_w2.json`.

**Поведение permanent_block:** см. [platform_subscription_billing.md](../architecture/modules/platform_subscription_billing.md) §6; тесты `test_platform_record_provision_permanent_block_no_retry_increment`, `test_platform_run_due_skips_provision_blocked_intent`.

## Два секрета A/B (пациент vs платформа)

Пациентский webhook и `PLATFORM_BILLING_WEBHOOK_SECRET` разделены по путям и конфигу; grep-обоснование: `PLATFORM_BILLING_WEBHOOK_SECRET` в `src/core/config.py`, пациентские ключи — `yookassa_*` / клиника.

## Итог

Реестр YAML + матрица в модуле согласованы с кодом `apply_platform_yookassa_notification` и OpenAPI-примерами; pytest покрывает согласованные ветки; reconcile UI и метрики «stuck/DLQ» зафиксированы для OPS.
