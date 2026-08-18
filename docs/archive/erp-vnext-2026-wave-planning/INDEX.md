# Индекс архива `erp-vnext-2026-wave-planning`

> Не путать с живым реестром артефактов: [`docs/artifacts/README.md`](../../artifacts/README.md).  
> Этот индекс описывает **только** исторический vNext-пакет в данной папке.

## Назначение

| Раздел | Файлы (примеры) |
|--------|------------------|
| Архитектурный скелет vNext | `ARCH_DECISIONS_NEXT.md`, `ARCH_BOOKING_NEXT.md`, `ARCH_CRM_NEXT.md`, `ARCH_ERP_NEXT.md`, `ARCH_LOYALTY_NEXT.md`, `ARCH_OMNICHANNEL_NEXT.md`, `ARCH_PAPERLESS_NEXT.md`, `ARCH_TASKS_NEXT.md`, `ARCH_ATTRIBUTION_NEXT.md` |
| Пакеты разработки по ID | `ARCH_DEV_BKG_*`, `ARCH_DEV_CRM_*`, `ARCH_DEV_ERP_*`, `ARCH_DEV_OMNI_*`, `ARCH_DEV_SEC_RBAC_*`, … и парные `*_TASKS.md` |
| QA / волны / бэклоги | `DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md`, `QA_ARCH_*`, `LEAD_DECISIONS_QA_ARCH_WAVES.md`, `QA_CHECKLIST_BKG_MULTI.md` |
| Gaps (backend/frontend) | `BACKEND_GAPS_*`, `FRONTEND_GAPS_*`, `UX_FLOWS_AND_GAPS_NEXT.md` |
| Фронт: техпаспорт и дизайн | `ARCH_FRONTEND_TECH_PASSPORT_DENTAL_BOOKING.md`, `ARCH_FRONTEND_DESIGN_SYSTEM_MIDNIGHT.md`, `ARCH_FRONTEND_ENTERPRISE_BASELINE.md`, … |
| Perf / OPS / безопасность | `ARCH_PERF_ENGINE_L2_DEEP_2026.md`, `WAVE5_OPS_RUNBOOK.md`, `NONFUNCTIONAL_AUDIT_NEXT.md`, `SEC_RBAC_ENDPOINTS_MAP.md` |
| Факты о репозитории (сверять с кодом) | `PROJECT_INTERNALS_CURRENT_FACTS.md` |
| Прочее | `BUSINESS_PLAN_NEXT.md`, `BUSINESS_ROUTES.md` (снимок; канон маршрутов — **`docs/artifacts/BUSINESS_ROUTES.md`**), `WAVE5_A3_EXPLAIN_QUERIES.sql`, `sec_rbac_router_permissions.txt` (снимок; актуальный процесс — `scripts/audit_rbac_endpoints.py` + **`documentation/rbac_router_permissions.txt`**) |

## Связь с ADR

Часть тем здесь перекрывается с **`docs/adr/`** (outbox, реплика reporting, webhook-семантика и т.д.). При конфликте **приоритет у ADR и кода**; этот архив — контекст эволюции и формулировок волн.
