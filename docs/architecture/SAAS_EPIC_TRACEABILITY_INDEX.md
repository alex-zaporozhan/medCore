# Индекс эпик-срезов SaaS (traceability для LEAD / ARCH / DEV / QA_ARCH)

> **Назначение (DOC-1):** одна точка входа: **Epic_ID** → разделы [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) (**МП**), строки [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md), ADR, ключевые пути кода, ожидаемый **QA_REPORT**, статус.  
> **Правило:** при закрытии среза добавляйте строку **QA_REPORT** и меняйте **Статус** на `done`.  
> **Ритуал исполнения:** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](./LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md).  
> **Дорожная карта потоков (детализация срезов):** см. таблицу «Потоки» ниже и файлы `STREAM_*_EPICS.md` в [arch_plan/](./arch_plan/).  
> **PRC-TRACK (Production Launch L3):** [STREAM_PRODUCTION_READINESS.md](./arch_plan/STREAM_PRODUCTION_READINESS.md) — единая матрица **PRC-A…I**, waiver, DAG, задание @ARCH.  
> **QA_ARCH:** в файлах `docs/architecture/arch_plan/STREAM*.md`, [STREAM_PRODUCTION_READINESS.md](./arch_plan/STREAM_PRODUCTION_READINESS.md), [STREAM_PHASE0_AND_GOVERNANCE.md](./arch_plan/STREAM_PHASE0_AND_GOVERNANCE.md), [STREAM_CROSS_CUTTING_GO_LIVE.md](./arch_plan/STREAM_CROSS_CUTTING_GO_LIVE.md) и [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) зафиксирован раздел **«QA_ARCH: префлайт для @ARCH и приёмка»** — вход для моделирования до кода и чеклист приёмки после @DEV.

**Не путать** с продуктовым RAG §24.3 — см. [STREAM_PRODUCT_RAG_24_EPIC.md](./arch_plan/STREAM_PRODUCT_RAG_24_EPIC.md).

---

## Потоки (roadmap-файлы)

| Поток | Документ срезов |
|--------|-----------------|
| 1a Platform | [STREAM_1A_PLATFORM_EPICS.md](./arch_plan/STREAM_1A_PLATFORM_EPICS.md) |
| 1b Commerce | [STREAM_1B_COMMERCE_EPICS.md](./arch_plan/STREAM_1B_COMMERCE_EPICS.md) |
| Frontend SaaS | [STREAM_FRONTEND_SAAS_EPICS.md](./arch_plan/STREAM_FRONTEND_SAAS_EPICS.md) |
| Phase 2 Reliability | [STREAM_PHASE2_RELIABILITY_EPICS.md](./arch_plan/STREAM_PHASE2_RELIABILITY_EPICS.md) |
| 1e + 3+ + опц. 4 | [STREAM_1E_AND_PHASE3_PLUS_EPICS.md](./arch_plan/STREAM_1E_AND_PHASE3_PLUS_EPICS.md) |
| Продукт RAG §24.3 | [STREAM_PRODUCT_RAG_24_EPIC.md](./arch_plan/STREAM_PRODUCT_RAG_24_EPIC.md) |
| Приоритет 1a vs 1b | [SAAS_EPIC_PRIORITY_DECISION_1A_VS_1B.md](./SAAS_EPIC_PRIORITY_DECISION_1A_VS_1B.md) |
| Observability smoke | [../operations/OBSERVABILITY_COMPOSE_SMOKE.md](../operations/OBSERVABILITY_COMPOSE_SMOKE.md) |
| **Production Readiness (PRC L3)** | [STREAM_PRODUCTION_READINESS.md](./arch_plan/STREAM_PRODUCTION_READINESS.md) |
| Phase 0 + governance | [STREAM_PHASE0_AND_GOVERNANCE.md](./arch_plan/STREAM_PHASE0_AND_GOVERNANCE.md) |
| Cross-cutting go-live | [STREAM_CROSS_CUTTING_GO_LIVE.md](./arch_plan/STREAM_CROSS_CUTTING_GO_LIVE.md) |

---

## Таблица эпиков

| Epic_ID | МП § (якоря) | PHASE_FULL_CLOSURE / U-* | ADR / модуль | Ключевые пути `src/` / инфра | QA_REPORT (ожидаемый) | Статус |
|---------|----------------|---------------------------|--------------|------------------------------|------------------------|--------|
| **DOC-1** | §15, §23 | — | — | `docs/architecture/SAAS_EPIC_TRACEABILITY_INDEX.md` | — | **done** |
| **OBS-1** | §11, §15b 1d | — | — | [docker-compose.yml](../../docker-compose.yml) `profiles: observability` | — | **done** (runbook) |
| **OBS-2** | §11 M6 | — | — | `deploy/alertmanager/` | QA_REPORT_OBS_TELEGRAM (после внедрения) | open |
| **OBS-3** | §11 M5 | — | — | OPS runbook + [RELEASE_CHECKLIST.md](../operations/RELEASE_CHECKLIST.md) | QA_REPORT_OBS_GRAFANA_ACCESS | open |
| **1a-E1** | §17, §19 п.3 | U-005 | [specs/OWNER_API_SEMANTICS_U005_DRAFT.md](./specs/OWNER_API_SEMANTICS_U005_DRAFT.md), [PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md](./specs/PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md) | Спеки / OpenAPI черновики | [QA_REPORT_1a_E1_jwt_spec](../artifacts/QA_REPORT_1a_E1_jwt_spec.md) | **done** |
| **1a-E2** | §16.1 | **1a-F1**, U-004 | [ADR-007](../adr/ADR-007-platform-multitenancy-super-admin.md) | `platform_founder_users`, `platform_founder_auth`, `get_current_platform_founder`, миграция `20260422_platform_founder_users` | [QA_REPORT_1a_E2_platform_user](../artifacts/QA_REPORT_1a_E2_platform_user.md) | **done** |
| **1a-E3** | §9, §19 | **1a-F2** | — | TOTP, `platform_founder_auth` | [QA_REPORT_1a_E3_founder_2fa](../artifacts/QA_REPORT_1a_E3_founder_2fa.md) | **done** |
| **1a-E4** | §1 C5 | **1a-F3** | — | `platform_audit` logger + вызовы на `/platform/*` | [QA_REPORT_1a_E4_platform_audit](../artifacts/QA_REPORT_1a_E4_platform_audit.md) | **done** |
| **1a-E5** | §1, ADR-007 | **1a-F5** | ADR-007 | RLS GUC на `organization_entitlements` + pytest | [QA_REPORT_1a_E5_rls](../artifacts/QA_REPORT_1a_E5_rls.md) | **done** |
| **1a-E6** | §19 п.3 | **1a-F4** | ADR-007 | `iss`/`aud` / отдельный issuer; `src/core/security.py`, все реалмы JWT | [QA_REPORT_1a_E6_jwt_hardening](../artifacts/QA_REPORT_1a_E6_jwt_hardening.md) | **done** |
| **1b-E1** | §3–§6 | **1b-F4**, **1b-F5** | [platform_subscription_billing.md](./modules/platform_subscription_billing.md) | catalog, `POST .../signup/checkout`, лендинг | [QA_REPORT_1b_E1_checkout](../artifacts/QA_REPORT_1b_E1_checkout.md) | **done** |
| **1b-E2** | §6, §2d п.8 | **1b-F1** (часть) | ADR-011 | `platform_billing_service.execute_platform_provision`, `organization_entitlements`, owner invite | [QA_REPORT_1b_E2_provision](../artifacts/QA_REPORT_1b_E2_provision.md) | **done** |
| **1b-E3** | §15b 1b, §2d п.3 | **1b-F2** | ADR-011 | webhook B OpenAPI examples + pytest unknown provider | [QA_REPORT_1b_E3_openapi_b](../artifacts/QA_REPORT_1b_E3_openapi_b.md) | **done** |
| **1b-E3b** | §15b 1b, §16.6 | **1b-F2** | ADR-011, [platform_subscription_billing.md](./modules/platform_subscription_billing.md) §7 | полный контракт веток YooKassa, pytest-матрица, reconcile UI | [QA_REPORT_1b_E3b_webhook_contract](../artifacts/QA_REPORT_1b_E3b_webhook_contract.md), `tests/api/test_platform_billing.py` | **done** |
| **1b-E4** | §16.6 шаги 3–4 | **1b-F6** (часть) | ADR-009 связка | gauges stuck/DLQ, алерты, runbook §10, Grafana W1/W2, `permanent_block` | [QA_REPORT_1b_E3b_webhook_contract](../artifacts/QA_REPORT_1b_E3b_webhook_contract.md) §метрики; **1b-F12** multi-replica — open | **done** (MVP) |
| **1b-E5** | §16.6 | **1b-F6** | [platform_subscription_billing.md](./modules/platform_subscription_billing.md) §4.3 | гейт в `execute_platform_provision`; **1b-F6a** override — open | pytest `tests/api/test_platform_billing.py` | **done** (ядро) |
| **1b-E6** | §10, **10-Q4** | — | SEC | app rate limit + nginx README; полный WAF edge — **10-Q4** open | [10_CROSS_CUTTING](./arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md), [deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md](../../deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md) | **partial** |
| **1c-E1** | §12.2, §19 п.17 | — | [ENTITLEMENT_ROUTER_INVENTORY.md](./ENTITLEMENT_ROUTER_INVENTORY.md) | инвентарь + Product строки | QA_REPORT_1c_E1_inventory | open |
| **1c-E2** | §12–§13 | **3-F3** (часть) | 04_PHASE_1C | routers `require_entitlement`, меню FE | QA_REPORT_1c_E2_menu_gates | open |
| **FE-E1** | §5, §2c C3 | **1b-F3** | — | `frontend/` маркетинг / signup | QA_REPORT_FE_E1_landing | open |
| **FE-E2** | §7–§8 | — | — | `frontend/` кабинет Основателя | QA_REPORT_FE_E2_founder_console | open |
| **FE-E3** | §12–§13 | — | — | `frontend/src` админка + entitlements API | QA_REPORT_FE_E3_admin_entitlements | open |
| **2-E1** | §17.1 | — | ADR-009, [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md) | outbox hot-path B | QA_REPORT_2_E1_outbox_b | open |
| **2-E2** | §17.1 | **2-F1** | ADR-009 | booking outbox | QA_REPORT_2_E2_booking_outbox | open |
| **2-E3** | §15a | **2-F8**, U-008 | `.github/workflows/` | CI workflows | [LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md](../artifacts/LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md), `release-gate.yml` | **done** (baseline + политика 2026-04-06) |
| **2-E4** | ADR-008 | **2-F2**, U-009 | [DR_RUNBOOK.md](../operations/DR_RUNBOOK.md) | drill evidence | QA_REPORT_2_E4_dr | open |
| **1e-bundle** | §24, §15b 1e | **1e-F1…F7** | 06_PHASE_1E | embed, export, metrics, RAG v1 | [06_PHASE_1E_LIFECYCLE_EMBED.md](./arch_plan/06_PHASE_1E_LIFECYCLE_EMBED.md), [STREAM_PRODUCT_RAG_24_EPIC.md](./arch_plan/STREAM_PRODUCT_RAG_24_EPIC.md) | **partial** (хвосты **1e-F1**, **1e-F3**) |
| **3-plus** | §25, §14 | **3-F*** | ADR-010 | import connectors, effective org | тот же отчёт | **partial** (**3-F3** хвост, **3-F4…F6** open) |
| **4-commerce** | §26 | — | [ADR-013](../adr/ADR-013-commerce-store-bounded-context-scope.md) | bounded context | QA_REPORT_4_commerce | open |
| **RAG-24** | §24.3 | **1e-F1** (partial) | [STREAM_PRODUCT_RAG_24_EPIC.md](./arch_plan/STREAM_PRODUCT_RAG_24_EPIC.md), [ADR-014](../adr/ADR-014-rag-retrieval-vectors-and-stores.md) | `organization_rag_kb_*`, `organization_rag_kb_audit_log`, `public_embed` `/rag/search`, метрики `embed_rag_search_*` | `tests/api/test_rag_org_isolation.py`, `tests/api/test_rag_kb_phase2.py` | **partial** (FTS/hybrid + аудит + квоты + метрики + OpenAPI 403; векторный store — ADR-014 фаза B) |
| **10-Q5** | §30–§31 | **10-Q5** | [LOAD_SCENARIO_MARKETING_10K.md](../operations/LOAD_SCENARIO_MARKETING_10K.md) | load test артефакты | QA_REPORT_10_Q5_load | in_progress |
| **P0-GOV** | §23, Phase 0 | **0-F1…0-F3**, U-006/008/009 (часть) | [STREAM_PHASE0_AND_GOVERNANCE.md](./arch_plan/STREAM_PHASE0_AND_GOVERNANCE.md) | `payment_webhook_governance`, `phase0_governance_preflight.py`, `release-gate.yml`, `dr-restore-drill.yml`, `ENTERPRISE_SAAS_TARGET.md` | [LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md](../artifacts/LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md), [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) (**0-F***) | **partial** (**0-F1** / PRC-G1 — draft envelope; 0-Q1…0-Q3, 0-F2, 0-F3 — **done** 2026-04-06) |

---

## Очередь следующих срезов (актуально на 2026-04-07)

**Phase 0 / governance:** эпик **P0-GOV** — [LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md](../artifacts/LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md) (закрытие 0-Q1…0-Q3, 0-F2, 0-F3); **PRC-G1** / **0-F1** envelope — см. [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) (Фаза 0).

**1a:** поток **закрыт** @QA_ARCH — [STREAM_1A_PLATFORM_EPICS.md](./arch_plan/STREAM_1A_PLATFORM_EPICS.md), [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md). Остаточный долг — раздел «Улучшения» в STREAM_1A. **1b:** срезы **1b-E3b…E5** закрыты в коде и [QA_REPORT_1b_E3b_webhook_contract](../artifacts/QA_REPORT_1b_E3b_webhook_contract.md); **1b-E6** partial (edge WAF); хвосты **1b-F6a, F11, F12, F3, F7–F9** — [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md), [STREAM_1B_COMMERCE_EPICS.md](./arch_plan/STREAM_1B_COMMERCE_EPICS.md).

Пост-ревью **1a-E2:** [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md). Решение порядка исполнения: [SAAS_EPIC_PRIORITY_DECISION_1A_VS_1B.md](./SAAS_EPIC_PRIORITY_DECISION_1A_VS_1B.md) (блок «Исполнение»). Долг полного закрытия: [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md).

---

## Связь с матрицей МП

Разделы МП → артефакты без привязки к эпик-ID: [arch_plan/TRACEABILITY_MATRIX.md](./arch_plan/TRACEABILITY_MATRIX.md).

---

**Версия:** 2026-04-07 — **RAG-24**, **1e-bundle**, **3-plus** отражают срез Stream 1e + Phase 3+ ([STREAM_PRODUCT_RAG_24_EPIC.md](./arch_plan/STREAM_PRODUCT_RAG_24_EPIC.md), [08_PHASE_3_PLUS.md](./arch_plan/08_PHASE_3_PLUS.md)); срезы **1a-E6**, **1b-E3b** в таблице; очередь синхронизирована с STREAM.
