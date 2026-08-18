# NONFUNCTIONAL_AUDIT_NEXT — наблюдаемость, SRE, лимиты (backend)

> **Назначение:** единая точка для порогов алертов, кардинальности метрик и runbook-заметок, на которые ссылаются `deploy/prometheus/dental_booking_alerts.yml`, `DEV_EXECUTION_TRACKER_NEXT.md` и эпики Engine L2.  
> **Роль:** @QA_ARCH / @OPS / @DEV при изменении метрик или деплоя.

---

## §5 ERP L2 (витрины отчётов)

- **RBAC:** `GET` ERP-отчётов — `erp.owner_reports.read`; ROI/attribution — дополнительно `attribution.reports.read`; unified `POST .../erp-aggregates/refresh` для `kind=all` или `attribution` — см. `ARCH_DEV_ERP_VITRINES_026.md`.
- **Свежесть:** `ERP_AGGREGATE_STALE_MAX_SECONDS` (по умолчанию 7200) — при превышении лага `max(updated_at)` по диапазону read-path уходит в **raw** (`reason=stale_range`).
- **Пустая витрина:** без watermark — fallback на raw (`empty_vitrine`). С **watermark** (`erp_aggregate_coverage_watermark`, ревизия `q3r4s5t6u7v8`) и `trust_empty_if` — возможен ответ **пустой список из витрины** без raw; см. §5.1.

### §5.1 Watermark и риск «ложного нуля»

Инвариант: watermark обновляется **в той же транзакции**, что и запись витрины после успешного refresh. Если сырые факты появляются **в обход** штатного refresh (ручное вмешательство в БД, дефект загрузки), теоретически возможен ноль в витрине при ненулевом raw — **низкая вероятность** в нормальной эксплуатации.

**Митигация:** алерты по `erp_aggregate_read_fallback_total`; мониторинг **`erp_aggregate_empty_trusted_total`** (см. §6); при подозрении — ручной `POST .../erp-aggregates/refresh` на окно дат.

### §5.2 Выборочная сверка raw ↔ витрина (visit_revenue)

**Цель:** снизить остаточный риск «ложного нуля» / расхождения без полного nightly full-scan по всем клиникам.

- **Реализация:** Celery `erp_tasks.run_daily_visit_revenue_parity_sample` (beat **05:15 UTC**, после nightly **03:30 UTC**). За один прогон: **одна** клиника (ротация по `day.toordinal()`), окно **вчера (UTC)**, сравнение **sum(raw)** vs **sum(vitrine)** для `visit_revenue`.
- **Включение:** `ERP_AGGREGATE_PARITY_SAMPLE_ENABLED=true` (по умолчанию `false`, чтобы не шуметь в dev). Без флага задача — no-op (метрики не инкрементируются).
- **Метрика:** `erp_aggregate_parity_sample_total{result="match|mismatch|skipped_no_clinics"}`; расхождение — структурный лог `erp_parity_sample_visit_revenue_mismatch` с `clinic_id` (детализация не в лейблах Prometheus).
- **Алерт:** `ERPVisitRevenueParitySampleMismatch` в `deploy/prometheus/dental_booking_alerts.yml`.
- **Архитектура:** согласовано с `ARCHITECTURE_EXCELLENCE_PASSPORT.md` §5 (сверка reporting vs операционные таблицы) и эталоном `ErpReportsRepository` / витрина `ErpVisitRevenueAggregate`.

### §5.3 Wave 5 — replica / reporting timeout / Redis dashboards (QA_ARCH W5)

- **Read replica:** `DATABASE_REPLICA_URL` (optional) — `GET` admin report routes use reporting pool; writes stay on primary. См. `docs/adr/ADR-005-wave5-replica-reporting-redis-cache.md`.
- **Statement timeout:** `DB_REPORTING_STATEMENT_TIMEOUT_MS` (default 120000, `0` = off) — `SET LOCAL` на reporting-сессии.
- **Lag probe:** `GET /health/replica` (если задан `DATABASE_REPLICA_URL`) — `in_recovery`, `lag_seconds`, `lag_warning` при превышении `DB_REPLICA_LAG_WARN_SECONDS`; gauge **`db_replica_lag_observed_seconds`**. Runbook: `./WAVE5_OPS_RUNBOOK.md`.
- **Redis cache:** `ERP_DASHBOARD_CACHE_ENABLED`, `ERP_DASHBOARD_CACHE_TTL_SECONDS` — JSON для `.../reports/dashboard` и `.../reports/owner-dashboard`; инвалидация после успешного commit refresh (фоновая задача FastAPI + Celery).
- **Метрики кэша:** `erp_dashboard_cache_requests_total{result="hit|miss|error"}`, `erp_dashboard_cache_invalidations_total`.
- **Индексы / EXPLAIN:** после `w5perf1idx_fin` — см. `./WAVE5_A3_EXPLAIN_QUERIES.sql`.
- **Perf / k6:** `scripts/loadtests/k6_wave5_smoke.js` (`/health` + опционально `ADMIN_TOKEN`/`ADMIN_CLINIC_ID` для `GET .../dashboard`); workflow **Load tests (k6, optional)** — не блокирует merge; Variables `LOADTEST_BASE_URL`, `K6_ADMIN_CLINIC_ID`, secret `K6_ADMIN_TOKEN`.

---

## §6 Пороги алертов (стартовые) и кардинальность метрик

Источник правил: **`deploy/prometheus/dental_booking_alerts.yml`**. Пороги — **начальные**; подбирать по staging/prod.

| Alert (rule) | Expr (идея) | for | Примечание |
|--------------|-------------|-----|------------|
| ERP_VitrineStaleRangeFallback | `rate(erp_aggregate_read_fallback_total{reason="stale_range"}[5m])` > 0.05 | 10m | warning — рост raw из-за устаревшей витрины |
| ERP_VitrineEmptyFallback | `rate(...{reason="empty_vitrine"}[5m])` > 0.05 | 10m | warning — пустая витрина без доверия watermark |
| ERP_NightlyPartialRefresh | `rate(erp_aggregate_nightly_kind_failures_total[1h])` > 0 | 15m | warning — сбой nightly по виду витрины |
| HTTPHigh5xxRate | доля 5xx по `http_request_duration_seconds` | 5m | critical |
| BookingToErpChainFailureBurst | `business_chain_booking_erp_errors_total` | 10m | warning |
| OmniAiChainFailureBurst | `business_chain_omni_ai_errors_total` | 10m | warning |
| CrmLeadActualValueErpMissingFact | info-серия H3 | 30m | info |
| ERPVisitRevenueParitySampleMismatch | `increase(erp_aggregate_parity_sample_total{result="mismatch"}[25h])` | 10m | warning — §5.2 |

### §6.1 Кардинальность (QA_ARCH 2026-03) — единая политика

**Правило:** для высокочастотных путей (HTTP, цепочки OBS, ERP/Loyalty, задачи, Omni) в лейблах Prometheus **не** используются сырые `clinic_id` / `business_account_id`. Вместо них — **`clinic_bucket`** / **`account_bucket`** (`0`…`31`, `crc32(id) % 32`), см. `src/core/prometheus_labels.py`. Детализация по конкретной клинике — в **структурных логах** (`clinic_id` в `extra`).

**Уровни (договорённость W1 scope = hot paths + ERP; остальное — техдолг с планом):**

| Уровень | Где | Политика |
|---------|-----|----------|
| **A — обязательно bucket** | Цепочки completion → ERP, Omni+AI, ERP L2 read/fallback/empty_trusted, nightly failures по `aggregate_kind`, выборочная сверка §5.2 (счётчик без `clinic_id` в лейблах) | Новые метрики в этих семействах — только `clinic_bucket` / `account_bucket` или без tenant-лейбла |
| **B — id допустим с пометкой** | Низкочастотные admin-операции, переходы стадий CRM, paperless, редкие счётчики | Допустимо `clinic_id` до снятия техдолга; при росте числа клиник — миграция на bucket или срез по `job_type` |
| **C — бэклог** | `crm_lead_stage_transitions_total` и аналоги с высокой кардинальностью стадий × клиник | План: срез по `stage_group` / bucket; не расширять необоснованно лейблы |

| Семейство метрик | Лейбл tenant |
|------------------|--------------|
| `business_chain_booking_erp_*`, локальные `booking_completion_*` | `clinic_bucket` |
| `business_chain_crm_attribution_*`, `business_chain_tasks_attention_*` | `clinic_bucket` |
| `business_chain_omni_ai_*`, `omni_messages_total`, `omni_ai_auto_replies_total`, `omni_ai_suggestions_total` | `account_bucket` |
| `erp_loyalty_*`, `loyalty_*` (campaign / family / wallet), `tasks_created_total`, `task_time_to_close_seconds`, `crm_ai_recommendations_total` | `clinic_bucket` |
| `erp_aggregate_nightly_kind_failures_total` | только `aggregate_kind` |
| `erp_aggregate_empty_trusted_total` | `aggregate_kind` |
| `erp_aggregate_parity_sample_total` | только `result` (match / mismatch / skipped_no_clinics) |
| RBAC для AI tools | `booking.ai_tools.use`, `ai.tasks.run` — не в Prometheus; фильтр в `list_tools_for_context` |

**Остаточная кардинальность:** часть CRM-воронки (`crm_lead_stage_transitions_total` и др.) всё ещё может использовать `clinic_id` в лейблах — уровень **B/C**; см. `./QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG.md` при плановом сокращении.

### §6.2 Runbook: event-driven refresh витрин

1. Включить **`ERP_AGGREGATE_EVENT_REFRESH_ENABLED=true`** только при работающих **Redis** и **Celery worker** (задача `erp_tasks.refresh_clinic_erp_aggregates_window`).
2. **`ERP_AGGREGATE_EVENT_DEBOUNCE_SECONDS`** — подавление дублей enqueue на одну клинику/день визита (Redis `SET NX`).
3. Без воркера очередь растёт — витрины обновляет nightly job; не полагаться только на события.

### §6.3 Grafana dashboard (как код)

JSON: **`deploy/grafana/dashboards/dental_booking_observability_w1_w2.json`** (алиас смысла L2 / W1–W2 observability; дублирующее имя `dental_booking_l2_observability.json` не требуется — один канонический файл в репо). Импорт: Grafana → Dashboards → Import → загрузить файл; мастер подставит **`__inputs`** — выбрать ваш Prometheus datasource (панели ссылаются на `${DS_PROMETHEUS}`, без жёсткой привязки к uid в репо). В дашборде: **notes** (контекст bucket/логов), **row**-секции ERP vs chains, те же запросы, что и для алертов. Расширение панелей (lag, SLO, multicluster variables) — см. `./QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG.md` §1.

### §6.4 SLO, error budget и burn rate (надстройка над статическими порогами)

Статические пороги в `dental_booking_alerts.yml` — **стартовые**; для зрелого OPS-контура см. [Google SRE — SLI/SLO](https://sre.google/workbook/sli-services/) и [burn rate alerts](https://sre.google/workbook/alerting-on-slos/).

**Практика в этом репозитории (по мере необходимости, без обязательности в W1):**

- Завести **recording rules** для SLI: например доля «успешных» запросов по `http_request_duration_seconds` (исключая ожидаемые 4xx) или доля ошибок по `business_chain_*_errors_total` относительно базовой скорости цепочки.
- Алерты **multi-window, multi-burn-rate** (fast/slow) для критичных API и цепочек — см. классическую формулу в workbook; пороги согласовать с @LEAD / OPS.
- Пока recording rules не заведены, **достаточно** текущих `rate`/`increase` в правилах и таблицы §6; перенос порогов в error budget — отдельный инкремент (часто W5+).

### §6.5 Завершение визита и CRM (Wave 3)

- **`booking_completion_attempts_total`** — при жёсткой блокировке loyalty (подписка / кошелёк / семья, см. `LoyaltyVisitCompletionBlocked`) инкрементируется **`status="loyalty_blocked"`**; это отдельно от best-effort ошибок списания (метрика `loyalty_error` / логи без блокировки `completed`).
- **`booking_completion_erp_retry_total`** — `PUT /admin/bookings/{id}/complete/retry`; структурный лог **`booking_complete_erp_retry_attempt`** с полем **`previous_erp_error_code`**.
- **Celery** `crm_tasks.reconcile_lead_actual_values` — обработка лидов порциями с **отдельной короткой сессией на лид** (снижение длительной блокировки одной транзакцией).

### §6.6 CRM Kanban / семантика стадий (Wave 4, QA_ARCH W4.2)

- **Контракт:** `GET .../pipelines/{id}/stage-semantics` возвращает **`resolved_stage_semantics`** (явный маппинг + infer по `stage.code`, как в `LeadStageSemanticsService`). Фронт строит строгий режим Kanban по этому полю; fallback — только `mappings`, если resolved пуст.
- **Смена стадии:** `PATCH .../leads/{id}/stage` с телом **`enforce_semantic_transition`** (bool). При `true` и нарушении state machine — **400**, `detail.code=semantic_transition_invalid` (серверная гарантия при включённом строгом режиме в UI).
- **RBAC AI tools (W4.1):** permissions **`booking.ai_tools.use`**, **`ai.tasks.run`** — в матрице и фильтре доступных tools; не дублировать сырые UUID в Prometheus (см. таблицу §6.1, строка про RBAC).

**Perf «на потом»** (без DoD W4): горячий путь `stage-semantics` при большом числе стадий, объединённый bootstrap Omni — см. **`./QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG.md`** §5 п.13–15.

### §6.7 Структурированные ошибки записи/оплаты (Wave 7, BE4)

- **Метрика:** `booking_errors_total{code, clinic_bucket, source}` — `source` = `api` | `ai_tool`; кардинальность кода ограничена enum `BookingErrorCode`.
- **Дашборд:** `deploy/grafana/dashboards/dental_booking_booking_errors_w7.json`.
- **Алерты:** `BookingServiceUnavailableBurst`, `BookingPaymentFailedBurst` в `deploy/prometheus/dental_booking_alerts.yml`.
- **Runbook:** `docs/runbook/SUPPORT_TRACE_ID.md`.
- **Webhook:** `payment_webhook_failures_total{reason=invalid_json|processing_error}`; тело ошибок 4xx/5xx включает `trace_id` при наличии middleware.

---

## Связанные артефакты

- `ARCH_PERF_ENGINE_L2_DEEP_2026.md`, `ARCH_DEV_ERP_VITRINES_026_TASKS.md`
- `./QA_ARCH_W1_W2_FOLLOWUP_PLAN_2026.md` — чеклист доработок по отчёту W1/W2 (перекрёстно с этим файлом)
- `./DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md`, `CONTRIBUTING.md` — волны W1/W2 и критерии PR (§5)
