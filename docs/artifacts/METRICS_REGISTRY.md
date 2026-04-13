# METRICS_REGISTRY — dental_booking

> **Версия:** 2026-04-06 (M-A1: contour A webhook failures + `rate_limited`, алерты invalid_secret burst)  
> **Статус:** строки добавляет **@ARCH** / **@QA_ARCH** при появлении новой метрики; карточки **M-*** — по `docs/METRICS_PROTOCOL.md` §5 (бэклог **1b-F11** для полного набора карточек контура B).

| ID | Название | Слой | Источник | Техн. имя / событие | Владелец | Статус | Карточка |
|----|----------|------|----------|---------------------|----------|--------|---------|
| M-B1 | Webhook B исходы (низкая кардинальность) | API | `platform_billing.py` / сервис | `platform_billing_webhook_total{result}` | OPS | active | backlog 1b-F11 |
| M-B2 | Жизненный цикл платежа YooKassa (контур B) | API | `platform_billing_service` | `platform_billing_payment_lifecycle_total{event}` | OPS | active | backlog 1b-F11 |
| M-B3 | Попытки провижининга после оплаты | app + Celery | `platform_billing_service` | `platform_provision_attempt_total{result}` (`success` / `failed` / `dlq` / **`permanent_block`**) | OPS | active | backlog 1b-F11 |
| M-B4 | Запланирован ретрай провижининга | Celery | `record_platform_provision_failure` | `platform_provision_retry_scheduled_total` | OPS | active | backlog 1b-F11 |
| M-B5 | Очередь провижининга (gauge, scrape /metrics) | API | `refresh_platform_billing_provision_gauges` | `platform_signup_intent_stuck` | OPS | active | backlog 1b-F11 |
| M-B6 | DLQ signup intent (gauge) | API | то же | `platform_signup_intent_dead_letter` | OPS | active | backlog 1b-F11 |
| M-B7 | Ошибка чтения БД для gauge контура B | API | то же | `platform_billing_gauge_refresh_failures_total` | OPS | active | backlog 1b-F11 |
| M-B8 | ADR-012 отзыв биллинга | API | `apply_platform_billing_revocation_after_refund` | `platform_billing_billing_revocation_total{result}` | OPS | active | backlog 1b-F11 |
| M-B9 | TTL job: intent переведён в `expired` | Celery | `expire_stale_platform_signup_intents` | `platform_signup_intent_ttl_expired_total` (без labels; `inc(n)` за батч) | OPS | active | backlog 1b-F11 |
| M-A1 | Ошибки webhook контура A (запись, YooKassa) | API | `payments.py` `payments_webhook` | `payment_webhook_failures_total{reason}` — `invalid_json` \| `invalid_secret` \| `processing_error` \| `rate_limited` | OPS | active | `PatientPaymentWebhookInvalidSecretBurst` + `PaymentWebhookFailures` в `dental_booking_alerts.yml` |
| M-R1 | Сверка ``local-pending`` YooKassa (A+B) | Celery | `payment_local_pending_reconcile_service` | `payment_local_pending_reconcile_total{contour,result}` | OPS | active | `PaymentLocalPendingReconcileErrors` |
| M-R2 | Итог ночного ERP sweep по клиникам | Celery | `erp_aggregate_service.refresh_all_clinics_erp_aggregates_nightly` | `erp_aggregate_nightly_run_total{result}` | OPS | active | `ERP_NightlyRunPartialFailures` |
| M-R3 | Webchat Redis fan-out | API | `webchat_push_manager` | `webchat_redis_fanout_total{op,result}` | OPS | active | `WebchatRedisFanoutPublishErrors` |
