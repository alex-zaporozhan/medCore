# Technical Executive Summary — dental_booking (evidence-backed)

Scope: repository scan (backend `src/`, `tests/`, `frontend/`, `deploy/`, `alembic/`, CI workflows). Metrics below are from the workspace as of this audit unless noted.

---

## 1. Data & multi-tenancy isolation

**How multi-tenancy is implemented**

- **Primary tenant key is `clinic_id`:** JWT admin login embeds `clinic_id` in the token payload; patient/booking flows consistently assert `clinic_id` on entities (e.g. `BookingService` uses `assert_entity_belongs_to_clinic` from `src/application/multitenancy.py`).
- **Organization / network layer:** `organization_id` appears on admins, clinics, billing, entitlements, and RAG KB (`OrganizationRagKbDocument.organization_id`). Cross-clinic admin access is explicit: `src/api/v1/clinic_scope.py` allows another clinic only when same `organization_id` **and** the user has global role `owner` at the home clinic; otherwise **404/403** to avoid cross-tenant enumeration.
- **HTTP error mapping for boundary violations:** `src/api/v1/multitenancy_http.py` maps `ClinicForbiddenError` to structured JSON (code `clinic_forbidden`, clinic and entity ids, trace id).

**Scale of relational model**

- **~160 SQLAlchemy physical tables** indicated by **`__tablename__` assignments counted across `src/`: 160** (includes association/auxiliary tables; `omnichannel_chat_closure` contributes multiple names in one module).
- **160 domain entity modules** under `src/domain/entities/` (excluding `__init__.py`): each maps to the persistence model in practice.
- **98 Alembic revision files** under `alembic/versions/` (schema evolution depth).

**RBAC**

- **Granular permission codes:** `src/application/rbac_matrix.py` defines **`PermissionDef` entries: 49** distinct permission codes (examples: `view_finance`, `manage_inventory`, `patients.pii.read`, `patients.medical.read` / `write`, task Kanban ops, loyalty campaign ops, CRM, etc.).
- **Enforcement:** `RbacServiceImpl` (`src/application/services/rbac_service.py`) resolves **role codes + permission codes per `(user_id, clinic_id)`** via `RbacRepository`. Router-level usage is widespread: **`require_permissions` / `user_has_any_permission` references across `src/api/v1/routers`: 300+ decorator/dependency call sites** (aggregated grep counts across router modules).
- **Persistence:** `permissions`, `roles`, `role_permissions`, `user_roles`, `user_permission_grant`, `rbac_audit_log` entities exist under `src/domain/entities/`.

---

## 2. Backend & architecture scale

**HTTP surface**

- **486 FastAPI route handlers** in `src/api/` matching `@router.get|post|put|patch|delete|head|options(` (decorator count).
- **94 router modules** under `src/api/v1/routers/` (including shared `_admin_staff_common.py`).
- **565 Python modules** under `src/` (`.py` file count).

**Stack (libraries)**

- From `pyproject.toml`: **FastAPI**, **Starlette**, **Uvicorn**, **SQLAlchemy 2.x** + **asyncpg**, **Alembic**, **Pydantic v2**, **Redis** (`redis`, `aioredis`), **Celery** (Redis broker extras), **httpx**, **prometheus-client**, **PyJWT**, **python-telegram-bot**, **boto3**, **cryptography**, **pyotp**.

**Background processing (Celery + Redis)**

- **Celery app** `src/infrastructure/messaging/celery_app.py`: broker/result backend from settings; **11 task packages** in `include=[...]` (notifications, AI, loyalty, owner integrations, exports, backups, ERP, CRM, staff collab, platform billing, domain outbox, payment reconciliation).
- **Beat schedule (examples of critical workloads):**
  - **Reminders:** `notifications.run_reminders` every **900s**.
  - **AI task generator / manager:** daily + hourly clinic sweep.
  - **Loyalty:** expiring packages daily; campaign engine daily.
  - **Owner comms:** morning brief 09:00 UTC; AI supervisor summary 20:00 UTC.
  - **Exports/backup hygiene:** `cleanup_old_exports_and_backups` 04:00 UTC.
  - **ERP:** nightly aggregate refresh **03:30 UTC**; visit-revenue parity sample **05:15 UTC**.
  - **Staff collab:** calendar reminders **every 300s**.
  - **Platform billing:** provision retries **60s**; stale signup intent expiry **3600s**.
  - **Domain outbox dispatch:** **`domain_outbox.dispatch_pending` every 30s**.
  - **Payment reconciliation:** local-pending YooKassa reconcile **every 600s**.
- **Redis usage (in addition to Celery):** rate limiting (`src/infrastructure/rate_limiter.py`), omnichannel realtime pub/sub (`src/infrastructure/realtime/omni_pubsub.py`), optional **webchat multi-replica fan-out** (`webchat:notify:{chat_id}` in `webchat_push_manager.py`).

**Transactional outbox**

- **Implemented** in `src/application/services/domain_outbox_service.py` with entity `DomainOutbox` (`src/domain/entities/domain_outbox.py`): **PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`** on **`dedup_key`** for idempotent enqueue (e.g. payment success, platform signup provision, booking lifecycle).
- **Dispatch:** Celery task `domain_outbox.dispatch_pending` on a schedule; metrics include `domain_outbox_dispatch_total`, pending gauges, oldest-age gauge, post-commit failure counter (wired in `src/core/metrics.py`).
- **Feature flags** in settings (see `.env.example` in repo): `DOMAIN_OUTBOX_PAYMENT_WEBHOOK_ENABLED`, `DOMAIN_OUTBOX_PLATFORM_BILLING_PROVISION_ENABLED`, `DOMAIN_OUTBOX_BOOKING_EVENTS_ENABLED`, batch limits, dispatch attempt caps.

**Advisory locks & row locking**

- **Doctor slot serialization:** `pg_advisory_xact_lock` via `src/application/booking_slot_advisory_lock.py` + key derivation in `src/domain/booking_slot_policy.py` (used from `BookingService`, CSV import).
- **ERP refresh:** `src/application/services/erp_refresh_lock.py` uses **`pg_advisory_xact_lock`** with fixed namespace + `clinic_id`-derived key.
- **Waitlist:** `FOR UPDATE` noted in `waitlist_service.py` docstring for conversion serialization.

**Other “enterprise” data-path patterns**

- **Optional read replica** for reporting sessions (`get_db_reporting`, `DATABASE_REPLICA_URL`, `statement_timeout` in `src/infrastructure/database/base.py`).

---

## 3. Frontend & UI/UX maturity

**Stack**

- **React 18.3**, **Vite 6**, **TypeScript ~5.6**, **React Router 6**, **Mantine 7**, **TanStack React Query 5**, **@dnd-kit**, **Vitest**, **Playwright** (`frontend/package.json`).

**Counts (`frontend/src`)**

- **151 `.tsx` files** total.
- **77 routable page components** (files under `pages/` excluding `__tests__` path segments).
- **24 shared UI primitives** under `shared/ui/` (design-system-style building blocks).
- **12 `.tsx` files** under `admin/components/` (entity drawers, calendar shells, etc.; additional UI lives in `admin/pages` and `shared/`).

**PWA**

- **Yes:** `vite-plugin-pwa` + **Workbox** in `frontend/vite.config.ts` (manifest, icons, screenshots, shortcuts, `navigateFallback`, runtime caching rules); runtime registration in `frontend/src/pwa/registerPwa.ts`. **No native WebSocket usage found** in backend `src` grep for `WebSocket`/`websocket` (realtime is HTTP-long-poll / Redis fan-out patterns, not WS).

**State & server interaction**

- **Server state:** **TanStack Query** (`useQuery` / `useMutation` patterns across `frontend/src/hooks/`).
- **Realtime-ish UX:** **Webchat long-poll** with in-process `asyncio.Event` + optional **Redis PUBLISH** wake (`src/application/services/webchat_push_manager.py`); omnichannel uses **Redis pub/sub** for cross-replica events (`omni_pubsub`).

---

## 4. AI & external integrations

**AI assistant implementation**

- **Provider integration:** `AiClient` posts to a **configurable OpenAI-compatible** `.../chat/completions` endpoint via **httpx** (`src/infrastructure/external_apis/ai_client.py`); settings-driven base URL, API key, model, timeout.
- **Safety layer:** **`SafeAiClient`** wraps calls and runs **`AiSanitizer`** on outbound message text before external calls (`src/infrastructure/external_apis/safe_ai_client.py`); dedicated **`src/core/ai_sanitizer.py`** (covered by tests e.g. `tests/core/test_ai_sanitizer.py`).
- **Omnichannel orchestration:** Large **`OmnichannelAIOrchestrator`** (`src/application/services/omnichannel_ai_orchestrator.py`) plus **tooling** under `src/application/ai/` (booking, CRM, tasks, registry).
- **Admin chat AI:** `ChatAiService` builds context via `ChatService` and uses the safe client factory (`src/application/services/chat_ai_service.py`).

**RAG**

- **Yes (retrieval layer):** `OrganizationRagKbDocument` + **`organization_rag_kb_service`**: scoped search by **`organization_id`**; modes **`ilike` (default), `fts` (`plainto_tsquery` + `search_tsv`), `hybrid`** per `settings.rag_kb_search_mode`; explicit **ILIKE wildcard escaping** (`escape_ilike_user_fragment`). Comment in service: vector search flagged as future phase (**ADR-014** reference in code).

**Payments & third-party / infra APIs (non-exhaustive, code-present)**

- **YooKassa:** `src/infrastructure/external_apis/yookassa_client.py`, `platform_yookassa_payment`, webhooks (`payments`, `platform_billing` routers).
- **Telegram:** `python-telegram-bot` + `telegram_sender.py`; omnichannel outbound dispatcher.
- **S3-compatible object storage:** `src/infrastructure/storage/s3_storage.py` (**boto3**).
- **Optional AWS KMS envelope:** `src/infrastructure/security/kms_data_key.py`.
- **Cloudflare Turnstile:** `turnstile_service.py`, frontend `TurnstileWidget.tsx`.
- **SMTP / email:** `email_sender.py`.
- **OAuth hooks:** `oauth_auth_service.py`, `auth` router tests reference OAuth flows.

---

## 5. Observability, QA & deployment

**Automated tests**

- **`pytest` collection: 803 tests** (`poetry run pytest tests/ --collect-only`).
- **Test module inventory (by folder, `test_*.py` files):** `tests/api` **82**, `tests/services` **34**, `tests/core` **31**, `tests/application` **15**, `tests/unit` **8**, `tests/e2e` **5**, `tests/deploy` **1** (sums to **176 files**; remaining tests live in other `tests/` subtrees/scripts counted into 803).
- **Markers** (from `pyproject.toml`): `critical_path`, `regression_payments`, `regression_pd`, `regression_chats`, `security`, `redis_integration`; **`critical_path` currently collects 2 tests** (narrow gate — may be intentionally minimal).
- **Frontend unit tests:** **27** `*.test.ts(x)` files under `frontend/src`.
- **Playwright E2E (frontend repo):** **5** `frontend/e2e/*.spec.ts` specs; backend CI also drives **Playwright browser tests** against **Vite preview** (see `.github/workflows/backend-ci.yml` on branch).
- **Types:** FastAPI API tests, service/integration tests, domain/application tests, security/observability tests, Grafana JSON validation (`tests/core/test_grafana_dashboard_json.py`), Prometheus alert YAML tests (`tests/deploy/test_prometheus_alert_rules_yaml.py`).

**Observability stack**

- **Prometheus:** `deploy/prometheus/prometheus.yml` + **`deploy/prometheus/dental_booking_alerts.yml`** — **36 `alert:` rules** in that file (ERP, payments, webhooks, platform billing, domain outbox, security SOC, embed/RAG, patient auth, backup staleness, etc.).
- **Grafana:** **4 dashboard JSON files** under `deploy/grafana/dashboards/` (observability, booking errors, domain errors, security SOC); datasource provisioning in `deploy/grafana/provisioning/`.
- **Alertmanager:** `deploy/alertmanager/alertmanager.yml` (+ Telegram example).
- **In-app metrics:** `src/core/metrics.py` declares **115 `Counter`**, **18 `Histogram`**, **8 `Gauge`** constructors (**141 instruments** in that module alone); path normalization for cardinality in the same file.

**Deployment & CI/CD**

- **Docker Compose:** `docker-compose.yml` — **Postgres 16** (`max_connections=200`), **Redis 7**, **migrations job**, app images via `BACKEND_IMAGE` / `FRONTEND_IMAGE`, workers/beat as per file (not fully re-listed here); optional **observability profile** referenced in `.env.example`.
- **Container images:** root `Dockerfile` (backend) + `frontend/Dockerfile`.
- **GitHub Actions (9 workflows** under `.github/workflows/`): `backend-ci.yml`, `build-and-test-entitlements.yml`, `critical-path-gate.yml`, `release-gate.yml`, `docker-hub-publish.yml`, `docker-images-build-verify.yml`, `documentation-markdown-links.yml`, `dr-restore-drill.yml`, `security-trivy.yml`.
- **Jenkins / GHCR:** Documented in-repo as the **corporate** path (`Jenkinsfile` referenced in `AGENTS.md` / `CI_CD.md` / rules — present in repo for enterprise pipeline narrative).

---

## Buyer-oriented positioning (factual)

This codebase presents as a **layered modular monolith** (FastAPI + SQLAlchemy + Celery) with **explicit multi-tenant boundaries** (`clinic_id` / `organization_id`), **dozens of granular RBAC permissions**, **hundreds of HTTP operations**, **~160 relational tables**, **transactional outbox + PostgreSQL advisory locks**, **broad background job coverage**, **Prometheus/Grafana/Alertmanager assets**, and **803 automated tests** including API, service, security, observability artifact checks, plus frontend unit and Playwright suites.

If you want this turned into slide-ready bullets (one metric per slide) or a **reconciliation to “production tables only”** (excluding SQLite/test-only models if any), say which counting rule you prefer for “tables.”
