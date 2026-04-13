# ADR-005 — Wave 5: read replica, reporting session limits, Redis report cache

**Status:** accepted  
**Date:** 2026-03-21  
**Context:** `DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` Wave 5 (A1, A8, A9) and related NFR.

## Decision

1. **Read replica (A1)**  
   - Optional `DATABASE_REPLICA_URL` (async SQLAlchemy URL, same schema as primary).  
   - Admin **GET** report routes use `get_reporting_session`, which opens sessions on the replica engine when the URL is set; otherwise the primary DB is used.  
   - **Writes** (aggregate refresh, audit, mutations) stay on `get_session` (primary).  
   - **Consistency:** replica lag is acceptable for read-only dashboards; aggregate tables on a lagging replica may be slightly behind primary. For zero-lag reads, leave `DATABASE_REPLICA_URL` unset.

2. **Statement timeout (A8)**  
   - `DB_REPORTING_STATEMENT_TIMEOUT_MS` (default 120000, `0` = off) applies per reporting transaction via `SET LOCAL statement_timeout` at the start of each reporting session.  
   - A dedicated PostgreSQL **role** `reporting` with `ALTER ROLE ... SET statement_timeout` remains an ops choice; the app enforces a ceiling even without a separate role.

3. **Redis read-through for dashboards (A9)**  
   - JSON cache for `GET .../reports/dashboard` and `GET .../reports/owner-dashboard` under prefix `erp:rpt:v1:{clinic_id}:...`.  
   - TTL from `ERP_DASHBOARD_CACHE_TTL_SECONDS` (default 60). Toggle with `ERP_DASHBOARD_CACHE_ENABLED`.  
   - Invalidation: `SCAN` + `DEL` for `erp:rpt:v1:{clinic_id}:*` after successful ERP aggregate refresh (HTTP POST and Celery window/nightly).

## Consequences

- Ops must provision replication and set `DATABASE_REPLICA_URL` only when ready; no behavior change if unset.  
- **Lag / observability:** `GET /health/replica` probes the reporting DSN and returns `lag_seconds` on standbys; gauge `db_replica_lag_observed_seconds` updates on each probe. Пороги и NFR: `docs/NONFUNCTIONAL_SCORECARD.md`, алерты: `deploy/prometheus/dental_booking_alerts.yml`.  
- **Index audit:** после миграции `w5perf1idx_fin` — `EXPLAIN` по тяжёлым отчётным запросам в коде; см. `docs/MIGRATION_UPGRADE.md`.
