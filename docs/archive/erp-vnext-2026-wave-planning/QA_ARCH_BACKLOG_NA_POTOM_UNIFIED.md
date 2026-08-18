# QA_ARCH — единый бэклог «на потом» (из `*_TASKS.md`)

> **Назначение:** один вход для **инвентаризации** хвостов после закрытых эпиков: что отложено в рубриках **«На потом»** в парных TASK-файлах, с кратким намёком на реализацию.  
> **Не заменяет** исходные TASK: там остаётся контекст, номера фаз и ссылки на код. Здесь — **сводка для triage** (приоритет, дедупликация, зависимости).  
> **Поиск в репо:** `QA_ARCH_BACKLOG_NA_POTOM` или `BACKLOG_NA_POTOM_UNIFIED`

**Связь с «шлюзом» (инвентаризация + triage):**  
- **Инвентаризация** — собрать хвосты в одном месте (этот файл или его обновление после каждого крупного TASK).  
- **Triage** — разложить по **P0/P1/P2**, убрать дубли, отметить блокеры и «быстрые победы»; не каждый пункт обязан быть про перфоманс — ниже темы разделены для удобства.  
Запрос пользователя «собрать из всех TASK задачи на потом» — это по сути **шаг 1 (инвентаризация)**; регулярный **triage** — шаг 2 перед планированием спринта.

**Обновление:** при закрытии эпика править **исходный** `ARCH_DEV_*_TASKS.md`, затем **дополнять или пересобирать** этот сводный список (раз в квартал / по релизу — по договорённости с @LEAD).

### Статус Wave 4 (AI / Omni / CRM семантика, 2026-03, @DEV / ревью @QA_ARCH)

Закрытие DoD **W4.1 / W4.2** из `DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` зафиксировано в коде. Ниже — **факт реализации** для согласованности с репозиторием (не снимает отдельные ID из triage в секциях A–K).

| Пакет | Суть | Где смотреть |
|-------|------|----------------|
| **W4.1** | RBAC для AI tools; лимиты слотов в адаптере; правки orchestrator | `rbac_matrix.py`, `booking_tools_adapter.py`, `config.py`, `omnichannel_ai_orchestrator.py` |
| **W4.2 D2–D4** | Omni рабочий центр; бейджи/гейт фич; семантика: `resolved_stage_semantics`, `enforce_semantic_transition`, строгий Kanban | `AdminOmniChatPage.tsx`, `AiFeatureBadge.tsx`, `useEffectiveAiFeatureGate.ts`, `aiFeatures.ts`, `admin_crm.py`, `lead_service.py`, `AdminSalesPipelinePage.tsx` |

Детали и таблица: **`./QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG.md`** (§«Выполнено Wave 4»). NFR: **`./NONFUNCTIONAL_AUDIT_NEXT.md`** §6.6.

### Статус Wave 5 (Perf / инфра, 2026-03, @DEV / ревью @QA_ARCH)

Закрытие DoD **W5.1 / W5.2** из `DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` зафиксировано в коде и артефактах (ADR, runbook, NFR). Ниже — **не** снятие ID из triage навсегда, а **факт реализации** для согласованности с репозиторием.

| ID | Статус | Где смотреть |
|----|--------|----------------|
| **A1** | Реализовано (ops) | `DATABASE_REPLICA_URL`, `get_reporting_session` / `get_db_reporting`, `src/infrastructure/database/base.py`; probe **`GET /health/replica`**, gauge `db_replica_lag_observed_seconds` |
| **A8** | Реализовано | `DB_REPORTING_STATEMENT_TIMEOUT_MS`, `SET LOCAL` в `get_db_reporting`; порог **`DB_REPLICA_LAG_WARN_SECONDS`** для JSON probe |
| **A9** | Реализовано | `src/application/services/erp_report_cache.py` (дашборды admin); метрики `erp_dashboard_cache_*`; инвалидация после refresh (BackgroundTasks + Celery) |
| **A3** | Частично | миграция **`w5perf1idx_fin`**; шаблоны **EXPLAIN** — `./WAVE5_A3_EXPLAIN_QUERIES.sql` |
| **A4** | Частично | workflow **`.github/workflows/load-tests-k6-optional.yml`** (optional, `continue-on-error`); скрипт **`scripts/loadtests/k6_wave5_smoke.js`** |
| **A21** | Частично | k6: `/health` + опционально `GET .../reports/dashboard` при `ADMIN_TOKEN` / `ADMIN_CLINIC_ID` (полные сценарии Kanban/Omni — в пост-waves фундаменте) |

Детали OPS: **`./WAVE5_OPS_RUNBOOK.md`**; NFR: **`./NONFUNCTIONAL_AUDIT_NEXT.md`** §5.3. (ADR Wave 5 — отдельный файл в `docs/adr/` репозитория.)

### Статус Wave 7 (ошибки записи / RBAC, 2026-03, @DEV / ревью @QA_ARCH)

Закрытие DoD **W7.1–W7.4** из `DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` зафиксировано в коде и артефактах. Ниже — **факт реализации** для согласованности с репозиторием (не снимает отдельные ID из triage в секциях A–K).

| ID | Суть | Где смотреть |
|----|------|----------------|
| **BE1–BE8** | Словарь ошибок, метрики `booking_errors_total`, burst→Task, PWA, OpenAPI, журнал ARCH | `booking_error_codes.py`, `booking_error_observability.py`, `metrics.py`, Grafana/Prometheus, `BookingWizardPage`, `bookings.py`/`payments.py`, `ARCH_AUDIT_NEXT` §4 |
| **SR5** | `manager` + `erp.owner_reports.read`, `attribution.reports.read` | `rbac_matrix.py`, миграция `x7w8y9z0a1b2_*` |
| **SR3/SR9** | Инвентарь `sec_rbac_router_permissions.txt`, `audit_rbac_endpoints.py --check`, pytest | `tests/application/test_sec_rbac_router_permissions_inventory.py` |
| **SR1** | Карта эндпоинтов | `SEC_RBAC_ENDPOINTS_MAP.md` |
| **QA follow-up** | `trace_id` в 500/webhook, `payment_webhook_failures_total`, completion DTO | `main.py`, `payments.py`, `errors.py`, `NONFUNCTIONAL_AUDIT_NEXT` §6.7 |

Подробная таблица: **`QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG.md`** («Выполнено Wave 7»). Фундаментальный performance «на потом»: **§5** того же файла (п. **18–23**).

---

## A. Перфоманс, ERP-витрины, отчёты

| ID | Источник | Суть | Намётка реализации |
|----|-----------|------|---------------------|
| A1 | `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` | Read replica для read-only отчётов | Отдельный DSN + routing в репозитории отчётов; smoke на лаг репликации. |
| A2 | `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` | Параллелизация Omni AI / budget | См. `ARCH_DEV_OMNI_REGISTRY_015`; разнести независимые LLM-шаги, общий тайм-бюджет. |
| A3 | `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` | Индексный аудит `financial_transactions` и смежных | `EXPLAIN` тяжёлых путей; микро-миграции индексов; зафиксировать в ADR. |
| A4 | `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` | Перф-бюджет в CI (k6/Locust) | Порог p95 на staging; job в pipeline, не блокирующий merge по умолчанию. |
| A5 | `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` | Watermark покрытия диапазона витрины (не raw при нуле после refresh) | Таблица/строка `last_refresh_from/to` per clinic+kind; политика в `ErpAggregateService` + тесты. |
| A6 | `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` | Инвалидация витрин по событиям (не только nightly) | Подписка на `BookingCompleted` / проводки → debounce + `refresh_range` для окна. |
| A7 | `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` | Grafana: fallback `stale_range` / `empty_vitrine`, lag | Панели по `aggregate_kind`; алерты по порогам из `NONFUNCTIONAL_AUDIT`. |
| A8 | `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` | `statement_timeout` / роль reporting | Роль в PG + `SET` на сессию reporting-роутера. |
| A9 | `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` | Redis read-through для дашбордов | Ключ `clinic_id+period+kind`, TTL, инвалидация после refresh. |
| A10 | `ARCH_DEV_ERP_VITRINES_026_TASKS` | Витрина loyalty obligations | Отдельный эпик: семантика снимка ≠ периодный отчёт. |
| A11 | `ARCH_DEV_ERP_VITRINES_026_TASKS` | Batch POST refresh по клинике + дедуп | Очередь per clinic, advisory lock или idempotency key. |
| A12 | `ARCH_DEV_ERP_VITRINES_026_TASKS` | TZ клиники для границ дня в эталоне/refresh | Поле `clinic.timezone`; единые границы в `ErpReportsRepository` + тесты границы дня. |
| A13 | `ARCH_DEV_ERP_VITRINES_026_TASKS` | Аудит ручного POST refresh (admin id) | Лог/таблица audit с `admin_user_id`, `kind`, диапазон. |
| A14 | `ARCH_DEV_ERP_VITRINES_026_TASKS` | Per-report feature flags | Settings `erp_payroll_read_from_aggregate`, … + fallback на мастер-флаг. |
| A15 | `ARCH_DEV_ERP_VITRINES_026_TASKS` | EXPLAIN + индекс ROI / attribution | План эталона; индекс под FK/join при доказанной необходимости. |
| A16 | `ARCH_DEV_ERP_VITRINES_026_TASKS` | Тесты отрицательных сумм / корректировок | Фикстуры в БД + паритет витрина vs raw. |
| A17 | `ARCH_DEV_ERP_VITRINES_026_TASKS` | UI: `data_source` / `aggregate_stale` | Бейдж на страницах отчётов админки. |
| A18 | `ARCH_DEV_ERP_VITRINES_026_TASKS` | Детерминированный order для materials items | Явный `ORDER BY` в fetch из витрины; OpenAPI. |
| A19 | `ARCH_DEV_ERP_VITRINES_026_TASKS` | Мониторинг частичного nightly (не все 4 вида) | Метрика/алерт «пропущенный kind» per clinic. |
| A20 | `ARCH_DEV_PERF_SPOTS_024_TASKS` | Baseline P50–P99 до/после v1 | Замеры в staging, таблица в артефакте или release notes. |
| A21 | `ARCH_DEV_PERF_SPOTS_024_TASKS` | Нагрузочные Kanban / ERP / Omni | k6 сценарии; опционально CI nightly. |
| A22 | `ARCH_DEV_PERF_SPOTS_024_TASKS` | Алерты Prometheus под `status_class` | Обновить правила под новый лейбл. |
| A23 | `ARCH_DEV_ERP_REPORTS_012_TASKS` | SQL VIEW / materialized views для ORM-отчётов | Частично перекрыто **L2-витринами**; оставить для legacy путей или отменить после полного перехода. |
| A24 | `ARCH_DEV_CRM_MONEY_008_TASKS` | MV / view для income общая для CRM и ERP | Согласовать с витринами; не дублировать расчёт. |

---

## B. Наблюдаемость (OBS), цепочки, метрики

| ID | Источник | Суть | Намётка реализации |
|----|-----------|------|---------------------|
| B1 | `ARCH_DEV_OBS_CHAINS_023_TASKS` | Логи prepare в completion + CRM step | Расширить `BookingCompletionService` логами/metric steps. |
| B2 | `ARCH_DEV_OBS_CHAINS_023_TASKS` | Детализация `omni_ai` steps | Новые значения `step` в гистограмме, обратная совместимость. |
| B3 | `ARCH_DEV_OBS_CHAINS_023_TASKS` | CRM + attribution логи с `trace_id` | Структурные поля в lifecycle-сервисе. |
| B4 | `ARCH_DEV_OBS_CHAINS_023_TASKS` | `trace_id` в Attention/Task как поле | Миграция JSON/metadata колонки; поиск в UI/логах. |
| B5 | `ARCH_DEV_OBS_CHAINS_023_TASKS` | SLO/алерты по `business_chain_*` | Grafana dashboard + Alertmanager. |
| B6 | `ARCH_DEV_TASKS_MODEL_020_TASKS` | Дашборды Tasks/Attention, SLA | Разрезы по типам; согласование с ops. |
| B7 | `ARCH_DEV_LOY_FAMILY_013_TASKS` | Дашборды по метрикам FamilyLink | Панели по loyalty family counters. |
| B8 | `ARCH_DEV_PPR_MODEL_018_TASKS` | Метрики покрытия визитов формами | Доля без обязательных форм; алерты owner. |

---

## C. Безопасность, RBAC, ПД, compliance

| ID | Источник | Суть | Намётка реализации |
|----|-----------|------|---------------------|
| C1 | `ARCH_DEV_BKG_MULTI_003_TASKS` | Единый контракт 403/404 для clinic scope | Матрица роутеров vs `ClinicForbiddenError`. |
| C2 | `ARCH_DEV_BKG_MULTI_003_TASKS` | Multi-clinic JWT / смена контекста | Явный API context switch для owner нескольких клиник. |
| C3 | `ARCH_DEV_BKG_MULTI_003_TASKS` | Rate limit на серию 403 | Защита от перебора clinic_id без блока легитимного админа. |
| C4 | `ARCH_DEV_LOY_FAMILY_013_TASKS` | Permission `manage_family_links` | Seed + матрица RBAC. |
| C5 | `ARCH_DEV_LOY_FAMILY_013_TASKS` | ПД в истории «за кого списание» | Политика маскирования в UI. |
| C6 | `ARCH_DEV_TASKS_AI_021_TASKS` | Permission `ai.tasks.run`, audit trail | Миграция permissions + лог запусков runner. |
| C7 | `ARCH_DEV_BKG_AI_TOOLS_006_TASKS` | RBAC на tools через permissions | `booking.ai_tools.use` и др. в `list_tools_for_context`. |
| C8 | `ARCH_DEV_AI_TOKENIZATION_025_TASKS` | Medical PD, DOB, отдельная политика | Roadmap в §6 TASK; SEC-review перед флагами. |
| C9 | `ARCH_DEV_PPR_ESIGN_019_TASKS` | Юридический гейт ЭП, webhooks, kill switch | Отдельный эпик; runbook инцидентов. |
| C10 | `ARCH_DEV_OMNI_POLICY_016_TASKS` | Вывод `LLMClient`, единая матрица ПД | Поэтапный deprecation list в коде. |

---

## D. AI, Omnichannel, инструменты

| ID | Источник | Суть | Намётка реализации |
|----|-----------|------|---------------------|
| D1 | `ARCH_DEV_OMNI_REGISTRY_015_TASKS` | Расширение tools + фильтрация по роли/каналу | Реестр + контекст вызова. |
| D2 | `ARCH_DEV_OMNI_UI_017_TASKS` | Omni как рабочий центр (CRM/Booking/Tasks) | Композиция панелей на `AdminOmniChatPage`. |
| D3 | `ARCH_DEV_OMNI_UI_017_TASKS` | `AiFeatureBadge`, effective availability helper | Общие компоненты/хук `isFeatureEnabled`. |
| D4 | `ARCH_DEV_CRM_AI_009_TASKS` | Семантика стадий в UI, state-machine strict | Конфиг pipeline + флаги auto-apply. |
| D5 | `ARCH_DEV_LOY_AI_014_TASKS` | AI tool для кампаний, FamilyLink маршрутизация | Orchestrator + согласование с LOY_FAMILY. |
| D6 | `ARCH_DEV_CRM_EVENTS_007_TASKS` | Pydantic на границе DomainEvent | Контрактные модели + CI тест. |
| D7 | `ARCH_DEV_CRM_EVENTS_007_TASKS` | Stale leads как отдельный поток (Celery) | Периодический job `LeadEventStale`. |

---

## E. Доменные продуктовые хвосты (Booking, CRM, Loyalty, Waitlist, Paperless)

| ID | Источник | Суть | Намётка реализации |
|----|-----------|------|---------------------|
| E1 | `ARCH_DEV_BKG_WAITLIST_004_TASKS` | Публичные/PWA waitlist, триггеры без cancel, expire job | Сервисные методы + Celery. |
| E2 | `ARCH_DEV_BKG_WAITLIST_004_TASKS` | E2E waitlist в CI | Playwright/API цепочка. |
| E3 | `ARCH_DEV_LOY_FAMILY_013_TASKS` | Два механизма шэринга, UI FamilyLink, e2e цепочка | Продуктовое решение + тесты. |
| E4 | `ARCH_DEV_ERP_NODE_010_TASKS` | Процессоры Finance/Payroll/Inventory, обогащение `ErpVisitNodeRequest` | Рефактор `ErpVisitNodeService` + DTO. |
| E5 | `ARCH_DEV_ERP_LOYALTY_011_TASKS` | Обязательства на кошельки, строгая атомарность с ERP | Расширение модели + транзакции. |
| E6 | `ARCH_DEV_BKG_STATE_002_TASKS` | Гранулярные статусы отмены, `scheduled`/`in_progress` | Миграции данных + отчёты. |
| E7 | `ARCH_DEV_CRM_MONEY_008_TASKS` | Связь лида с несколькими `booking_id`, reconcile job | Модель + периодическая сверка. |
| E8 | `ARCH_DEV_PPR_MODEL_018_TASKS` | Публичный `in_progress`, ревокация signed, CI `alembic upgrade` | Эндпоинты + политика юр. |
| E9 | `ARCH_DEV_CRM_EVENTS_007_TASKS` | E2E воронки, дедуп задач, связка Task↔Attention | Тесты + продуктовые правила. |

---

## F. Инфраструктура тестов, CI, документация

| ID | Источник | Суть | Намётка реализации |
|----|-----------|------|---------------------|
| F1 | `ARCH_DEV_CRM_EVENTS_007_TASKS` | Стабилизация async teardown на Windows | pytest-asyncio / маркеры. |
| F2 | `ARCH_DEV_TASKS_AI_021_TASKS` | Alembic в test runner, Windows teardown | Скрипт CI + локальный `upgrade_test_db`. |
| F3 | `ARCH_DEV_PPR_ESIGN_019_TASKS` | Дубли §1–6 в TASKS — свернуть файл | Редакторская чистка. |
| F4 | `ARCH_DEV_PPR_MODEL_018_TASKS` | То же — дубль секций | Редакторская чистка. |
| F5 | Разные TASK | Синхронизация `DEV_PROMPTS_NEXT`, GAPS, `ARCH_AUDIT_NEXT` | Чеклист при закрытии каждого эпика. |

---

## G. Фасад завершения визита (`BookingCompletionService`) — `ARCH_DEV_BKG_CORE_001_TASKS` §7–8

| ID | Источник | Суть | Намётка реализации |
|----|-----------|------|---------------------|
| G1 | `ARCH_DEV_BKG_CORE_001_TASKS` §7.1 | Критичные ошибки Loyalty → не `completed`, Task `LOYALTY_MISMATCH` | Политика в `ARCH_DEV_ERP_LOYALTY_011`; зеркало правил ERP. |
| G2 | `ARCH_DEV_BKG_CORE_001_TASKS` §7.2 | Выделенный сервис CRM/Attribution-агрегатов после ERP | Подписка на `BookingCompleted`; ERP — источник факта выручки. |
| G3 | `ARCH_DEV_BKG_CORE_001_TASKS` §7.3 | Интеграционные тесты сложных Loyalty+ERP сценариев | Фикстуры пакет/депозит/граничные остатки. |
| G4 | `ARCH_DEV_BKG_CORE_001_TASKS` §7.4 | Retry «перепровести визит в ERP» при `erp_error_code` | Admin endpoint + метрики ретраев. |
| G5 | `ARCH_DEV_BKG_CORE_001_TASKS` §8 | Backlog-граф (дубли §7) | Свести с ERP_LOYALTY / CRM_MONEY при triage. |

---

## H. CRM ↔ деньги (`LeadCard.actual_value`) — расширенный блок `ARCH_DEV_CRM_MONEY_008_TASKS`

| ID | Источник | Суть | Намётка реализации |
|----|-----------|------|---------------------|
| H1 | CRM_MONEY §«На потом» | Явная связь лида с **списком** `booking_id` | Модель/JSON при необходимости, если ERP не всегда даёт `lead_id`. |
| H2 | CRM_MONEY §«На потом» | Reconcile job: success + `actual_value=0` при completed booking | Celery + метрика (уже частично). |
| H3 | CRM_MONEY @QA_ARCH | Алерты по `crm_lead_actual_value_erp_missing_fact_total` | Пороги в Grafana. |
| H4 | CRM_MONEY @QA_ARCH | Сквозной тест complete → `BookingCompleted` → `actual_value` vs `financial_transactions` | Integration в CI. |
| H5 | CRM_MONEY @QA_ARCH | Nightly/CI сверка агрегатов отчётов с ERP за период | Отдельный job или расширение существующих тестов. |
| H6 | CRM_MONEY @QA_ARCH | Audit для ручного `PATCH .../estimated-value` | Immutable журнал при COMPLIANCE. |
| H7 | CRM_MONEY @QA_ARCH | Фронт: `useUpdateLeadEstimatedValue` в Kanban | Когда приоритизирует продукт. |
| H8 | CRM_MONEY @QA_ARCH | Backfill исторических лидов | Одноразовый скрипт после смены правил. |

---

## I. Family / Loyalty — незакрытые пункты чеклиста (`ARCH_DEV_LOY_FAMILY_013_TASKS`)

| ID | Источник | Суть | Намётка реализации |
|----|-----------|------|---------------------|
| I1 | LOY_FAMILY «Не сделано» | Письменная инвентаризация в GAPS/UX | Документ + ссылки в `BACKEND_GAPS_Loyalty_NEXT`. |
| I2 | LOY_FAMILY | Сущность `LoyaltyGroup` (§2.1.2) | Миграция + домен. |
| I3 | LOY_FAMILY | Опциональный `group_id` на связях (§2.2.1) | FK nullable. |
| I4 | LOY_FAMILY | Документирование миграции данных между моделями шэринга | Runbook для ops. |
| I5 | LOY_FAMILY | UI / Omni / Tasks для семейного сценария (§4) | Экраны + хуки. |
| I6 | LOY_FAMILY | Attention §5.3.2 | Типы сигналов по порогам. |
| I7 | LOY_FAMILY | Разнести семантику лимитов сумма vs визиты, UTC-месяц | Документ + правки движка при необходимости. |

*(Пересечение с §«На потом» того же файла — одна политика PackageFamilyLink vs FamilyLink, RBAC `manage_family_links`, ERP obligation beneficiary — см. разделы C/E.)*

---

## J. Booking AI tools — детализация `ARCH_DEV_BKG_AI_TOOLS_006_TASKS` (§7.x)

| ID | Источник | Суть | Намётка реализации |
|----|-----------|------|---------------------|
| J1 | BKG_AI_TOOLS §7.1 | Единый `booking_ai_errors` / константы кодов | Таблица кодов для tools + UI. |
| J2 | BKG_AI_TOOLS §7.2 | Adapter `booking_tools_adapter.py` | Тонкие tools → адаптер → сервисы. |
| J3 | BKG_AI_TOOLS §7.4 | Лимиты `get_available_slots` (per-clinic, max_slots, suggest) | Settings + cap ответа. |
| J4 | BKG_AI_TOOLS §7.5 | Дедуп Task/Attention при ошибках tools | Ключ `(clinic_id, tool_id, error_code, bucket)`. |
| J5 | BKG_AI_TOOLS §7.6 | Интеграционные тесты Omni → booking в CI | Маркеры + docker-compose профиль. |
| J6 | BKG_AI_TOOLS §7.7 | Tokenization v2 (см. дедуп выше) | Единый дизайн с TASKS_AI_021. |

---

## K. Вне `ARCH_DEV_*`: Engine L2

| ID | Источник | Примечание |
|----|-----------|------------|
| K1 | `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` | Полный список «на потом» — §171+ файла; дубли с A* сведены в таблицу A. |

---

## L. Структурированные ошибки Booking/Payments — `ARCH_DEV_BKG_ERRORS_005_TASKS` §«На потом»

| ID | Суть (кратко) | Намётка |
|----|----------------|--------|
| BE1 | Единый словарь кодов с BKG AI tools | `booking_ai_errors` + согласование с J1. |
| BE2 | Второй аудит «сырых» 500 / без `trace_id` | grep по роутерам → DTO. |
| BE3 | E2E / контрактные тесты wizard | Playwright или API. |
| BE4 | Дашборд/алерты по `booking_errors_total` | Grafana, пороги по code/clinic. |
| BE5 | Пороги Attention/Task §3.3 | Дедуп + `AttentionFeedService`. |
| BE6 | Локализация, A11y, UX | FPWA‑4. |
| BE7 | OpenAPI + runbook саппорта | Схема `BookingErrorResponse`. |
| BE8 | Строка в `ARCH_AUDIT_NEXT` при закрытии BKG‑5 | Док. |

---

## M. RBAC — `ARCH_DEV_SEC_RBAC_022_TASKS` §«На потом»

| ID | Суть (кратко) | Намётка |
|----|----------------|--------|
| SR1 | Матрица при новых эндпоинтах | Правило до merge + карта эндпоинтов. |
| SR2 | UI fail‑closed | Скрытие кнопок без права. |
| SR3 | CI/скрипт аудита роутеров vs карта | Регресс «забыли permission». |
| SR4 | Immutable AuditLog критичных мутаций | Платежи, ЗП, loyalty, AI settings. |
| SR5 | `manager` + отчёты ERP/Attribution | Расширение seed / матрицы. |
| SR6 | Временные делегирования | Отдельный эпик. |
| SR7 | Аудит Celery/system_ai | Новые задачи не расширяют права. |
| SR8 | `../../SEC_RBAC_SPEC.md` | Вынести матрицу из ARCH. |
| SR9 | Параметризованные тесты матрицы | Snapshot / таблица роль×permission. |

---

## Приложение: охват файлов `./ARCH_DEV_*_TASKS.md`

| Файл | Явная рубрика хвоста | Примечание |
|------|----------------------|------------|
| `ARCH_DEV_AI_TOKENIZATION_025_TASKS` | §6 **Later** — medical PD / DOB | SEC roadmap |
| `ARCH_DEV_BKG_AI_TOOLS_006_TASKS` | §**На потом** (начало файла) | См. J* |
| `ARCH_DEV_BKG_CORE_001_TASKS` | §7–8 **Предложения / Backlog-граф** | См. G* |
| `ARCH_DEV_BKG_ERRORS_005_TASKS` | **На потом** | BE1–BE8 |
| `ARCH_DEV_BKG_MULTI_003_TASKS` | **На потом** | C1–C3, PWA тесты |
| `ARCH_DEV_BKG_STATE_002_TASKS` | **Будущие улучшения** (заголовок legacy) | Статусы booking |
| `ARCH_DEV_BKG_WAITLIST_004_TASKS` | **На потом** | Таблица E1–E7 |
| `ARCH_DEV_CRM_AI_009_TASKS` | **На потом** | N.1–N.5 |
| `ARCH_DEV_CRM_EVENTS_007_TASKS` | **На потом** + подраздел QA | D6–D7, E9, F1 |
| `ARCH_DEV_CRM_MONEY_008_TASKS` | **На потом** + @QA_ARCH | H* |
| `ARCH_DEV_ERP_LOYALTY_011_TASKS` | **Будущие улучшения** | E5 |
| `ARCH_DEV_ERP_NODE_010_TASKS` | §7 **Будущие улучшения** | E4 |
| `ARCH_DEV_ERP_REPORTS_012_TASKS` | **Будущие улучшения** | A23 + snapshot obligations |
| `ARCH_DEV_ERP_VITRINES_026_TASKS` | **На потом** | A10–A19 |
| `ARCH_DEV_LOY_AI_014_TASKS` | **На потом** | D5 + LOY список 1–15 |
| `ARCH_DEV_LOY_FAMILY_013_TASKS` | **На потом** + чеклист «Не сделано» | I* |
| `ARCH_DEV_OMNI_POLICY_016_TASKS` | §7 **на потом** | C10 |
| `ARCH_DEV_OMNI_REGISTRY_015_TASKS` | **"На потом"** | D1 |
| `ARCH_DEV_OMNI_UI_017_TASKS` | **На потом** | D2–D3 |
| `ARCH_DEV_OBS_CHAINS_023_TASKS` | §7 **Later** | B1–B5 |
| `ARCH_DEV_PERF_SPOTS_024_TASKS` | **На потом** | A20–A22 |
| `ARCH_DEV_PPR_ESIGN_019_TASKS` | **На потом** | C9, F3 |
| `ARCH_DEV_PPR_MODEL_018_TASKS` | **На потом** | E8, B8, F4 |
| `ARCH_DEV_SEC_RBAC_022_TASKS` | **На потом** | SR1–SR9 |
| `ARCH_DEV_TASKS_AI_021_TASKS` | **На потом** | C6, F2 |
| `ARCH_DEV_TASKS_MODEL_020_TASKS` | §7 **на потом** | B6 архив Attention |

Дополнительно (не `ARCH_DEV_*`): `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS` — §**На потом** (K1, пересечение с A*).

---

## Дедупликация и пересечения (кратко)

- **Токенизация v2 / mapping table** — в `ARCH_DEV_BKG_AI_TOOLS_006_TASKS`, `ARCH_DEV_TASKS_AI_021_TASKS`; делать **один** дизайн (`ai_token_mapping`).  
- **Redis кэш** — L2 TASK (дашборды) и 026 (read-through витрин); общий ключевой префикс и политика инвалидации.  
- **Grafana/алерты** — PERF, L2, 026, OBS, CRM_MONEY — завести **единый** дашборд «ERP/отчёты» с переменной `aggregate_kind` / `chain`.

---

## История изменений документа

| Дата | Изменение |
|------|-----------|
| 2026-03-20 | Первая сборка из актуальных `./ARCH_DEV_*_TASKS.md` и `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS.md` (@QA_ARCH). |
| 2026-03-20 | Полный проход: секции G–K, J (BKG_AI_TOOLS), H (CRM_MONEY QA), I (LOY_FAMILY чеклист), приложение по 26+1 файлам. |
| 2026-03-20 | Рубрики **На потом** в `ARCH_DEV_BKG_ERRORS_005_TASKS` / `ARCH_DEV_SEC_RBAC_022_TASKS`; секции **L** (BE*), **M** (SR*), приложение обновлено. |
| 2026-03-21 | Блок **«Статус Wave 5»** (A1/A8/A9/A3/A4/A21) — фиксация реализации W5 в коде; дедуп: Redis/дашборды см. также §выше. |
| 2026-03-21 | Блок **«Статус Wave 4»** (W4.1/W4.2: Omni/tools + CRM семантика Kanban); ссылка на `QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG` и NFR §6.6. |
| 2026-03-21 | Блок **«Статус Wave 7»** (BE*/SR* + QA follow-up: trace/webhook/metrics completion); ссылка на «Выполнено Wave 7» и §5 п. 18–23 в `QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG.md`. |
