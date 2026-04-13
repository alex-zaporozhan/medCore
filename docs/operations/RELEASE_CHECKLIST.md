# Чек-лист релиза (LEAD)

> **Связь:** ворота SaaS — [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) §19; миграции — [05_data_migrations_multitenancy.md](../architecture/05_data_migrations_multitenancy.md).

Ответственный за go: **LEAD** (или делегат).

## Перед merge в релизную ветку

- [ ] Alembic `upgrade head` на чистой схеме; путь отката (downgrade или forward-fix).
- [ ] Новые переменные в `.env.example`; секреты вне git.
- [ ] Ломающие изменения API — [API_VERSIONING_POLICY.md](../architecture/API_VERSIONING_POLICY.md).
- [ ] `pytest` по затронутым областям; платежи — `tests/api/test_payments.py`; контур B платформы — `tests/api/test_platform_billing.py`; публичный SaaS checkout/каталог — `tests/api/test_public_platform_checkout.py`, `tests/api/test_public_platform_catalog_rate_limit.py`; JWT Основателя — `tests/api/test_platform_internal.py`.
- [ ] GitHub Actions: job **`full-backend-tests`** (`pytest tests/`) зелёный на PR (U-008 / [07_PHASE_2_RELIABILITY.md](../architecture/arch_plan/07_PHASE_2_RELIABILITY.md)); job **`trivy-fs`** — [`.github/workflows/security-trivy.yml`](../../.github/workflows/security-trivy.yml) (скан зависимостей; на PR не блокирует merge при CRITICAL — см. workflow).
- [ ] **U-009:** после квартального restore на staging обновить дату/факт в [DR_RUNBOOK.md](./DR_RUNBOOK.md) §1.
- [ ] При релизе по **тегу `v*`** — workflow **Release gate** ([`.github/workflows/release-gate.yml`](../../.github/workflows/release-gate.yml)): entitlements, фронт, `scripts/phase0_governance_preflight.py all`, полный pytest (**PRC-E4** / **2-F8** — политика LEAD: [LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md](../artifacts/LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md); e2e/security из `workflows_disabled` — отдельное включение).
- [ ] Платежи **контур A** (`POST /api/v1/payments/webhook`): в prod задать **`PATIENT_PAYMENT_WEBHOOK_SECRET`** и тот же секрет в YooKassa/edge; не совпадать с **`PLATFORM_BILLING_WEBHOOK_SECRET`** (U-006). Долг rate limit контура A — [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) **0-Q2**.
- [ ] Если используете **`GET …/platform/internal/*`** в production: задайте **`PLATFORM_FOUNDER_JWT_SECRET`** (отдельно от `JWT_SECRET_KEY`). Пока секрет пустой, эти маршруты отвечают **503**; остальное API поднимается.

## Перед деплоем staging / prod

- [ ] **Phase 1 — fail-closed секреты:** при `APP_ENV=production` процесс API **не стартует**, если пустой любой из обязательных секретов: `PATIENT_PAYMENT_WEBHOOK_SECRET`, `PLATFORM_BILLING_WEBHOOK_SECRET`, `PLATFORM_FOUNDER_JWT_SECRET`, `JWT_SECRET_KEY` — см. `assert_required_security_secrets_in_production` в `src/core/payment_webhook_governance.py`, тесты `tests/core/test_payment_webhook_governance.py`. Загрузка из AWS Secrets Manager до Settings: `src/core/runtime_secrets.py` (`AWS_SECRETS_MANAGER_SECRET_ID`). Закрытие **PRC-A3** в prod — чеклист: [PLATFORM_AND_TENANT_SECRETS_RUNBOOK.md](./PLATFORM_AND_TENANT_SECRETS_RUNBOOK.md) § «Закрытие PRC-A3».
- [ ] **PRC staging (C1, B7, F1, F3, G2):** при приёмке релиза на staging — [PRC_STAGING_EVIDENCE_CHECKLIST.md](./PRC_STAGING_EVIDENCE_CHECKLIST.md); матрица публичных лимитов: [PUBLIC_PERIMETER_RATE_LIMIT_MATRIX.md](../review/PUBLIC_PERIMETER_RATE_LIMIT_MATRIX.md).
- [ ] **CI workflow debt (WP5.2):** таблица waive/замещения: [CI_WORKFLOWS_WAIVERS.md](../architecture/arch_plan/CI_WORKFLOWS_WAIVERS.md).
- [ ] Бэкап: [DR_RUNBOOK.md](./DR_RUNBOOK.md), ADR-008.
- [ ] Если планируется **`replicas(API) ≥ 2`** и уже есть или будет публичный **webhook B** / **signup** — проверить запись по **§17.1:** [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](./API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md) (outbox / одна реплика на приём / ADR риска).
- [ ] Ворота §19 — если затронуты platform / платный лендинг.
- [ ] **Публичный периметр SaaS (cross-cutting):** лимиты Redis на `POST /api/v1/public/platform/signup/checkout` (IP + email), `GET /api/v1/public/platform/catalog/*` (IP), `POST /api/v1/platform/billing/webhooks/yookassa` (IP); при деплое за ingress задать `PUBLIC_RATE_LIMIT_TRUSTED_PROXY_CIDRS` — см. [STREAM_CROSS_CUTTING_GO_LIVE.md](../architecture/arch_plan/STREAM_CROSS_CUTTING_GO_LIVE.md). Celery beat: `platform_billing.expire_stale_signup_intents` (TTL intent).
- [ ] SLO: [SLO_CRITICAL_PATHS.md](./SLO_CRITICAL_PATHS.md).
- [ ] Grafana / дашборды: сеть и доступ — [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) §11 M5 (не публичная сеть без auth). Локально/staging: `docker compose --profile observability up -d` — порты Prometheus/Grafana/Alertmanager на **127.0.0.1**; в проде — VPN/reverse-proxy с auth, не выставлять Grafana в публичный интернет. Пошаговый smoke: [OBSERVABILITY_COMPOSE_SMOKE.md](./OBSERVABILITY_COMPOSE_SMOKE.md).
- [ ] Staging (1d): после включения профиля `observability` — ≥1 срабатывание алерта до Alertmanager и доставка в тестовый HTTP-приёмник или настроенный Telegram/webhook OPS; кардинальность новых рядов `platform_billing_*` проверить по чеклисту в [07_metrics_observability.md](../architecture/07_metrics_observability.md).
- [ ] Релиз с гейтами **Фазы 1c** (entitlements): [ENTITLEMENT_ROUTER_INVENTORY.md](../architecture/ENTITLEMENT_ROUTER_INVENTORY.md) принят ARCH+LEAD (мастер-план §19 п.17, §15b 1c).
- [ ] **Phase 3 (rollout entitlements):** задать **`ENTITLEMENT_ENFORCEMENT_MODE`** (`legacy` / `auto` / `strict`) и при поэтапном переходе — **`ENTITLEMENT_ENFORCEMENT_STRICT_ORG_IDS`** (CSV UUID); см. `src/application/services/organization_entitlement_access.py`, тесты `tests/application/test_organization_entitlement_access.py`.
- [ ] **Phase 2 (contour B reconcile):** UI Основателя `/platform/provision-queue` — Retry и **manual-close** (`POST …/manual-close`); OPS runbook [PLATFORM_BILLING_PROVISION_RECONCILE.md](./PLATFORM_BILLING_PROVISION_RECONCILE.md); pytest `tests/api/test_platform_billing.py`, `tests/api/test_platform_internal.py`; smoke Playwright: `frontend/e2e/smoke-routes.spec.ts` (маршрут без JWT → редирект на `/platform/login`; полный клик по Retry/Закрыть на staging — с тестовым founder JWT вручную по runbook).
- [ ] Фаза **1e** (offboarding / embed): процедура и экспорт — [TENANT_OFFBOARDING_AND_EXPORT.md](./TENANT_OFFBOARDING_AND_EXPORT.md); публичный периметр embed — [EMBED_WIDGET_INTEGRATION.md](../architecture/EMBED_WIDGET_INTEGRATION.md), ключ **`omni.embed.bundle`** в тарифе при SaaS enforcement.

## После деплоя

- [ ] Smoke: `/health` + один критичный сценарий.
- [ ] Тег релиза и ссылка на PR.

**Версия:** 2026-04-08 (Phase 2/3: reconcile runbook + entitlement rollout env)
