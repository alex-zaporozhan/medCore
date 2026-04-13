# Инвентарь роутеров ↔ entitlement

> **Статус:** Фаза **1c** — гейты `require_entitlement` на опциональных модулях; скрипт проверки `scripts/check_admin_entitlement_routers.py` (CI: `build-and-test-entitlements.yml`, `release-gate.yml`). Таблица ниже — явные SKU без плейсхолдеров «уточнить Product» (PRC-D1).  
> **Приёмка:** ARCH + LEAD — [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) §12.2, §19 п.17.

## Легенда

- **RBAC** — только `require_permissions` / `require_active_clinic_admin` без entitlement.
- **ENT** — `require_entitlement("<ключ>")` на уровне `APIRouter` (плюс RBAC где был).
- **Legacy** — если у организации **нет** строк в `organization_entitlements`, сервер **не** режет опции (совместимость старых установок); при появлении строк включается режим enforcement.

## Явные product gates (опции §4 / §16.5)

| Роутер | Было | Сейчас | Целевой ключ (мастер-план) | Владелец | Статус |
|--------|------|--------|----------------------------|----------|--------|
| admin_crm.py | RBAC + `require_crm_enterprise_edition` | RBAC + **ENT** `crm.pipeline` | `crm.pipeline` | DEV | **1c закрыто** |
| admin_retention.py | RBAC + `is_box_edition()` в хендлерах | RBAC + **ENT** `retention.bundle` | `retention.bundle` | DEV | **1c закрыто** |
| admin_tasks.py | RBAC | RBAC + **ENT** `tasks.kanban` | `tasks.kanban` | DEV | **1c закрыто** |
| admin_task_boards.py | RBAC | RBAC + **ENT** `tasks.kanban` | `tasks.kanban` | DEV | **1c закрыто** |
| admin_task_streams.py | RBAC | RBAC + **ENT** `tasks.kanban` | `tasks.kanban` | DEV | **1c закрыто** |
| admin_task_tags.py | RBAC | RBAC + **ENT** `tasks.kanban` | `tasks.kanban` | DEV | **1c закрыто** |
| admin_marketing.py | RBAC | RBAC + **ENT** `marketing.attribution` | `marketing.attribution` | DEV | **1c закрыто** |
| admin_marketing_attribution.py | RBAC | RBAC + **ENT** `marketing.attribution` | `marketing.attribution` | DEV | **1c закрыто** |
| admin_recall.py | RBAC | RBAC + **ENT** `marketing.attribution` | `marketing.attribution` | DEV | **1c закрыто** (recall = маркетинг/коммуникации) |
| admin_embed.py | — | RBAC + **ENT** `omni.embed.bundle` | `omni.embed.bundle` | DEV | **1e**: API keys / webhook secret в админке |
| admin_crm_import.py | — | RBAC `manage_crm` + **ENT** `import.crm_v1` | `import.crm_v1` | DEV | **Phase 3+** / ADR-010: staging job dry-run |
| admin_commerce.py | — | RBAC `view_inventory` / `manage_inventory` + **ENT** `commerce.store_network` | `commerce.store_network` | DEV | **Фаза 4** / ADR-013: overview, stock-locations CRUD, POST nomenclature |
| admin_organization_profile.py | — | RBAC `view_crm` / `manage_crm` + роль **owner** на PATCH | — (не SKU) | DEV | **Phase 3+** §14: `industry_profile` |
| admin_lead_logs.py | RBAC | RBAC (`leads.log.view`) | — (не SKU) | QA_ARCH | **без `require_entitlement`**: omni-операции ≠ воронка CRM |
| admin_discounts.py | RBAC marketing | RBAC | часть **core.base** / ценообразование | DEV | без отдельного ключа — базовый продукт |
| admin_waitlist.py | RBAC marketing | RBAC | **core.base** (очередь записи) | DEV | без отдельного ключа |
| admin_prepayment.py | RBAC marketing | RBAC | **core.base** | DEV | без отдельного ключа |
| payments.py | публичный webhook A | — | контур A, не SaaS платформа | — | ок |

## Остальные admin_* (сводка: RBAC по домену)

Одинаковый паттерн: **RBAC без entitlement** для базы §13.1; опции — только по каталогу §4.

| Роутер | Примечание |
|--------|------------|
| admin_auth.py | вход / session |
| admin_omni_chat.py | omni / inbox perms |
| admin_omni_*.py | omni |
| admin_staff_*.py | персонал / collab |
| admin_schedule.py, admin_doctor_schedule.py | расписание, база |
| admin_services.py | услуги, база |
| admin_patients*, admin_patient_* | пациенты, база |
| admin_bookings* | запись, база |
| admin_finance.py, admin_reports*.py | ERP / отчёты; опция `erp.reporting_plus` — отдельный эпик |
| admin_loyalty.py | лояльность |
| admin_leads*.py (кроме lead-logs) | лиды / CRM-поверхности — по мере появления гейтов |
| admin_owner_settings.py, owner_omni_*.py | owner scope, U-005 |
| admin_ai_*.py | AI настройки |
| admin_integrations.py, integrations_gateway.py | интеграции |
| _admin_staff_common.py | общий dependency |

## Публичные и patient

| Роутер | Gate |
|--------|------|
| public_embed.py | Bearer API key (`dceb.*`) + SaaS **`omni.embed.bundle`** через `ensure_org_entitlement_keys_for_public_client`; webhook Bearer + тот же ключ; rate limit (§24.4) |
| auth.py, public_*.py, schedule.py, doctors.py, services.py, bookings.py (patient), patient_*.py | публичный / patient JWT |

---

**Проверка wiring:** `python scripts/check_admin_entitlement_routers.py`

**Бэклог QA_ARCH после 1c** (оптимизация `get_current_admin`, регистр кодов ошибок API, расширение CI pytest, контракт 403): [arch_plan/04_PHASE_1C_ENTITLEMENTS.md](./arch_plan/04_PHASE_1C_ENTITLEMENTS.md) («Бэклог после merge 1c») и строки **1c-Q1…Q4** в [arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md).

**Версия:** 2026-04-06 — PRC-D1/D2: инвентарь + CI-скрипт синхронизированы с `admin_*` роутерами; **2026-04-05** DEV: Phase 1c `require_entitlement` + session `entitlement_*` + UI фильтр.
