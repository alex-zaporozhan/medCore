# Метрики и наблюдаемость

## Как это работает (от запроса до алерта)

1. **HTTP:** после `trace_id_middleware` срабатывает `prometheus_http_duration_middleware` в `src/main.py`: для каждого запроса (кроме `/metrics`, `/health`, `/health/replica`) в гистограмму `http_request_duration_seconds` пишутся `method`, шаблон пути (`metrics_path_for_request` предпочитает route template Starlette) и агрегированный класс статуса `status_class` (`2xx`, `4xx`, `5xx`).
2. **Бизнес-метрики:** модули сервисов и core увеличивают счётчики при ошибках цепочек, booking, webhooks и т.д. (имена перечислены ниже в разделе Prometheus).
3. **Скрапинг:** `GET /metrics` вызывает `render_prometheus_metrics()` из `src/core/metrics.py` и отдаёт текст в формате Prometheus.
4. **Алерты:** файл `deploy/prometheus/dental_booking_alerts.yml` задаёт правила на те же имена метрик; при срабатывании Alertmanager (вне репозитория) шлёт уведомления. Пороги в YAML — стартовые, комментарии отсылают к `docs/METRICS_PROTOCOL.md`.
5. **Дашборды:** JSON в `deploy/grafana/dashboards/` визуализируют ряды из Prometheus; связь панель ↔ метрика поддерживается вручную при изменениях.

## Код приложения

- `src/core/metrics.py` — счётчики, гистограммы, нормализация пути для лейблов (`normalize_metrics_path`, `metrics_path_for_request`), безопасный fallback если нет `prometheus_client`. **Outbox (ADR-009, фаза 2):** `domain_outbox_dispatch_total{result,event_type}`, `domain_outbox_pending_rows`, `domain_outbox_oldest_pending_age_seconds`, `domain_outbox_gauge_refresh_failures_total`, `domain_outbox_blocked_by_attempt_cap_rows` (gauge refresh на `GET /metrics` с throttle, см. `DOMAIN_OUTBOX_METRICS_DB_REFRESH_MIN_INTERVAL_SECONDS`; после dispatch — принудительно). **Логический экспорт клиники (не кластерный BCP):** `backup_logical_export_completed_total{result}`, `backup_logical_export_last_success_timestamp_seconds` (ADR-008 partial). **Сквозная безопасность / антиспам (МП §27–§28, `arch_plan/10`):** `spam_blocked_total{channel}` (HTTP 429 по грубому каналу), `security_auth_failure_total{reason}` (401/403 без `organization_id`), `security_suspicious_request_total{path_class,reason}` (дёшевые эвристики до хендлера) — учёт в `security_soc_metrics_middleware` (`src/main.py`), классификация в `src/core/security_observability.py`; новые значения лейблов — только через этот реестр и согласование @ARCH. **Redis rate limiter (fail-open):** `rate_limiter_redis_fail_open_total` — при ошибке Redis счётчик фиксирует «пропущенный» лимит (см. `src/infrastructure/rate_limiter.py`, `documentation/OBSERVABILITY.md`). **Omnichannel (аудит §8.1–8.3):** `omni_outbound_dispatch_failed_total{reason}` — исходящая доставка в провайдер не удалась (`omnichannel_outbound_dispatcher.py`); `omni_realtime_publish_failed_total{event}` — сбой Redis publish для admin SSE (`omni_pubsub.py`).
- `src/core/prometheus_labels.py` — соглашения по низкой кардинальности лейблов (импортируется из метрик и тестов).
- Экспорт для Prometheus: эндпоинт подключается из приложения (см. `src/main.py` и `tests/api/test_health_wave5.py` для связки health/metrics).

**SaaS / кардинальность:** при введении метрик под платформу и тенантов — [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) §11 M1; ориентиры SLO — [../operations/SLO_CRITICAL_PATHS.md](../operations/SLO_CRITICAL_PATHS.md).

Протокол именования и порогов: [../METRICS_PROTOCOL.md](../METRICS_PROTOCOL.md) — этот файл не дублирует протокол.

## Deploy: Prometheus

- `deploy/prometheus/dental_booking_alerts.yml` — правила группы `dental_booking_observability`, в т.ч. метрики:
  - `erp_aggregate_read_fallback_total`
  - `erp_aggregate_nightly_kind_failures_total`
  - `http_request_duration_seconds_count` с лейблом `status_class`
  - `business_chain_booking_erp_errors_total`, `business_chain_omni_ai_errors_total`
  - `crm_lead_actual_value_erp_missing_fact_total`
  - `erp_aggregate_parity_sample_total`
  - `booking_errors_total`, `payment_webhook_failures_total`, `platform_billing_webhook_total{result}`, `platform_billing_billing_revocation_total{result}` (ADR-012), `platform_founder_auth_total{result}` (результаты без UUID в лейблах); **контур B провижининг:** `platform_signup_intent_stuck`, `platform_signup_intent_dead_letter` (gauges на `/metrics`), `platform_billing_gauge_refresh_failures_total`. Для контура B после гейта каталога (§4.3 [platform_subscription_billing.md](./modules/platform_subscription_billing.md)) к `result` относятся в т.ч. **`invalid_billing_period`**, **`billing_period_requires_plan_slug`**, **`unknown_plan_slug`**, **`amount_mismatch_catalog`**, **`missing_payment_amount`** — низкая кардинальность; при росте всплесков настроить алерт/runbook к reconcile Основателя.
  - **Алерты контура B (ADR-012, фаза 1d):** `PlatformBillingWebhookRefundPathElevated`, `PlatformBillingRevocationAppliedBurst`, `PlatformBillingWebhookProcessingErrorBurst` — только низкокардинальные лейблы `result`; пороги настраивать под OPS; `runbook_url` в аннотациях → `docs/architecture/modules/platform_subscription_billing.md` §12.
  - **Фаза 2 (ADR-009 / ADR-008):** `DomainOutboxOldestPendingStale`, `DomainOutboxPendingBacklog`, `DomainOutboxBlockedByAttemptCap` (при `DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS > 0`), `BackupLogicalExportSuccessStale` (info; заглушить если логический экспорт клиники не планируется) — `runbook_url` → `arch_plan/07_PHASE_2_RELIABILITY.md` или `DR_RUNBOOK.md` §8.
  - **Сквозное §27–§28 (`arch_plan/10`):** `SpamBlockedTotalElevated`, `SecuritySuspiciousRequestBurst`, `SecurityAuthFailureBurst` — `runbook_url` → `arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md`. Дашборд: `deploy/grafana/dashboards/dental_booking_security_soc_w10.json`.
  - **Omnichannel (аудит §8):** `OmniRealtimeRedisPublishFailureBurst` (`omni_realtime_publish_failed_total`), `OmniOutboundDispatchFailureBurst` (`omni_outbound_dispatch_failed_total`).
- **Compose (фаза 1d):** профиль `observability` в корневом `docker-compose.yml` — Prometheus, Alertmanager, Grafana (порты на `127.0.0.1`), тестовый HTTP-приёмник для webhook Alertmanager; конфиги в `deploy/prometheus/prometheus.yml`, `deploy/alertmanager/alertmanager.yml`. Подробности — `deploy/grafana/README.md`.

Комментарий в начале YAML отсылает к `docs/METRICS_PROTOCOL.md` и `deploy/grafana/README.md`.

## Deploy: Grafana

- `deploy/grafana/dashboards/dental_booking_observability_w1_w2.json`
- `deploy/grafana/dashboards/dental_booking_booking_errors_w7.json` (упоминается в аннотации алерта `BookingServiceUnavailableBurst`)
- `deploy/grafana/dashboards/dental_booking_domain_errors.json`
- `deploy/grafana/dashboards/dental_booking_security_soc_w10.json` (§27–§28: spam / security auth / suspicious probes)

Подробности подключения дашбордов: `deploy/grafana/README.md`.

## Статус

- Метрики в коде и алерты в репозитории: реализовано.
- Соответствие каждой панели JSON каждому имени метрики: сверять вручную при изменении дашбордов.

## Непонятное

Фактические значения SLA в проде документом не заявляются.

### Enterprise-аудит (честная оценка)

- **Критические риски:** наличие `/metrics` и YAML алертов не означает, что в проде настроены Prometheus/Alertmanager и on-call ([ось «Наблюдаемость»](./ENTERPRISE_SAAS_RUBRIC.md) уровень 1 vs 2).
- **Средние риски:** распределённая трассировка (OpenTelemetry) в коде не зафиксирована; есть `X-Trace-Id` и логи.
- **Формально / недоделано:** дашборды JSON могли разойтись с именами метрик после рефакторинга; SOC §27–§28 — см. `dental_booking_security_soc_w10.json` (сверять с `metrics.py` при изменениях).
- **Рекомендуемые доработки:** CI-проверка или документированный чеклист соответствия `dental_booking_alerts.yml` и кода метрик.

### Соответствие фактам (проверка)

- `metrics.py`, `main.py` middleware, `deploy/prometheus/dental_booking_alerts.yml` — статическое чтение; прод-скрейп не проверялся.

### Кардинальность новых правил (1d)

Правила на `platform_billing_*` агрегируют `sum(rate(...))` без `organization_id` в лейблах серии — соответствие [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) §11 M1. На staging после включения профиля `observability` сверить `/api/v1/query?query=...` на рост числа временных рядов при типичной нагрузке (чеклист OPS).

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** метрики без on-call и дашбордов в проде не дают SLO; `trace_id` без OTel — ограниченная корреляция.
- **Что усилить:** CI или чеклист соответствия имён метрик в коде и в `dental_booking_alerts.yml`.
- **С нуля:** распределённая трассировка — при multi-replica отладке.
- **БД:** косвенно — алерты на ERP/платежи указывают на цепочки к БД.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) (§4).
