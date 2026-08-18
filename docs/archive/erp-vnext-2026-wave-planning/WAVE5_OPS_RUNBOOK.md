# Wave 5 — ops runbook (реплика, кэш дашбордов, лаг)

Связано с `docs/adr/ADR-005-wave5-replica-reporting-redis-cache.md` и `NONFUNCTIONAL_AUDIT_NEXT.md` §5.3.

## Реплика чтения (`DATABASE_REPLICA_URL`)

- **Назначение:** снять нагрузку с primary для `GET` admin-отчётов (`get_reporting_session`).
- **Риск:** лаг реплики → устаревшие витрины и (при включённом Redis) устаревший JSON дашбордов до TTL.
- **Проверки:**
  - `GET /health/replica` — если реплика настроена: `in_recovery`, `lag_seconds`, `lag_warning` (порог `DB_REPLICA_LAG_WARN_SECONDS`, по умолчанию 60).
  - Метрика `db_replica_lag_observed_seconds` обновляется при каждом вызове `/health/replica` (для мониторинга — опрос с blackbox или cron).
- **Действия при высоком lag:** уменьшить `ERP_DASHBOARD_CACHE_TTL_SECONDS`, временно отключить `DATABASE_REPLICA_URL`, проверить `pg_stat_replication` на primary.

## Redis-кэш дашбордов

- **Ключи:** `erp:rpt:v1:{clinic_id}:*` (см. `erp_report_cache.py`).
- **Инвалидация:** после успешного `POST .../erp-aggregates/refresh` (фоновая задача после commit) и после Celery refresh.
- **Метрики:** `erp_dashboard_cache_requests_total{result="hit|miss|error"}`, `erp_dashboard_cache_invalidations_total`.
- **Redis down:** запросы идут в БД (кэш-miss/error), лог `erp_report_cache_get_failed`.

## Индексы (миграция `w5perf1idx_fin`)

- После `alembic upgrade head` на staging — прогнать `EXPLAIN (ANALYZE, BUFFERS)` по запросам из `./WAVE5_A3_EXPLAIN_QUERIES.sql` и зафиксировать план в тикете при необходимости.

## k6 (optional CI)

- Скрипт: `scripts/loadtests/k6_wave5_smoke.js`.
- Базово: `GET /health`.
- Сценарий отчёта: задать `ADMIN_TOKEN` и `ADMIN_CLINIC_ID` (staging secrets) — нагрузка на `GET .../reports/dashboard`.
- В GitHub Actions: repository Variable `LOADTEST_BASE_URL`, `K6_ADMIN_CLINIC_ID`, secret `K6_ADMIN_TOKEN`.

## Prometheus (идея правила)

Лаг обновляется только при опросе `/health/replica` (или при интеграции probe в scrape). Пример выражения для blackbox/json не приводим; по gauge:

```yaml
# Пример: рост лага на standby (после регулярного probe)
- alert: DbReplicaLagHigh
  expr: db_replica_lag_observed_seconds > 120
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Replication lag on reporting DSN > 120s (see GET /health/replica)"
```

Порог подобрать по staging; при `DATABASE_REPLICA_URL` на primary (ошибка конфигурации) `in_recovery=false`, lag в JSON будет `null`.
