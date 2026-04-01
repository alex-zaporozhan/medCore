# ARCH_DEV_ERP_VITRINES_026 — витрины ERP для payroll / materials / ROI (attribution)

> **Глобальный шаблон NFR (переносимый, не привязан к этому репо):** `docs/TEMPLATE_ERP_REPORTING_VITRINES.md` — нормы витрины, маппинг на scorecard, DoD; **этот файл** — конкретная реализация и эпик **026**.  
> **Поиск:** `ERP_VITRINES_026` или `VITRINES_026`  
> **Связь:** `ARCH_PERF_ENGINE_L2_DEEP_2026.md` §6–8, §8.2 TASK; эталон реализации — витрина выручки по визитам (`erp_visit_revenue_aggregate`, `ErpAggregateService`, `GET .../revenue-by-period`).  
> **Источник истины для «сырых» запросов:** `src/application/services/erp_reports_repository.py` (`ErpReportsRepository`).  
> **Пошаговые таски:** `ARCH_DEV_ERP_VITRINES_026_TASKS.md`

---

## Статус реализации (QA_ARCH / 2026-03)

**Закрыто в коде:** эпик **026** — витрины `erp_visit_revenue_aggregate` (эталон ранее), `erp_payroll_aggregate`, `erp_inventory_movement_aggregate` (дневная гранулярность), `erp_attribution_revenue_aggregate`; `ErpAggregateService` (refresh/fetch/max `updated_at` по правилам окна); `ErpReportsRepository.get_visit_inventory_daily_by_period`; чтение GET `revenue-by-period`, `payroll-by-period`, `materials-by-period`, `roi-by-source` с L2-fallback (stale / empty), DTO с `data_source` / `aggregate_max_updated_at` / `aggregate_stale`; общий helper **`resolve_erp_aggregate_rows`** (`erp_report_aggregate_read.py`); **`POST .../erp-aggregates/refresh`** с `kind`; nightly **`refresh_erp_aggregates_nightly`** на четыре вида; RBAC: `POST` с `kind` ∈ {`attribution`, `all`} требует **`attribution.reports.read`** поверх `erp.owner_reports.read` (см. `admin_reports.py`).

**Follow-up по качеству (тот же спринт):** миграция **`n0o1p2q3r4s5`** — в `erp_payroll_aggregate` добавлены **`period_start_is_null` / `period_end_is_null`** и расширен PK (убрана коллизия сентинелов дат с реальными значениями в API). Тесты: паритет, stale по всем вертикалям, RBAC на refresh, экстремальные даты payroll; идемпотентный DDL-патч в `tests/conftest.py` для старых тестовых БД.

**Документация:** `docs/MIGRATION_UPGRADE.md` (ERP витрины + права refresh), §6 `ARCH_PERF_ENGINE_L2_DEEP_2026.md`. Детальный чеклист фаз и G1–G5 — `ARCH_DEV_ERP_VITRINES_026_TASKS.md`.

---

## 1. Зачем отдельный эпик

После MVP L2 остаётся **тот же шаблон** (таблица витрины + DELETE/INSERT refresh за диапазон + чтение API с fallback + свежесть по `max(updated_at)` в окне + Celery + метрики), но **три других зерна агрегирования** и **два разных permission-контура** (`erp.owner_reports.read` vs `attribution.reports.read`). Вынесение в отдельный артефакт **026** позволяет:

- не раздувать L2-документ;
- вести PR **по одному домену** (payroll → materials → attribution) с чеклистами приёмки;
- явно зафиксировать **PK/гранулярность** каждой витрины (ниже).

---

## 2. Общая архитектурная структура

### 2.1. Повторяемый каркас (как у visit-revenue)

| Слой | Назначение |
|------|------------|
| **Сырой эталон** | Методы `ErpReportsRepository`: `get_visit_payroll_by_period`, `get_visit_inventory_by_period`, `get_attribution_revenue_by_period` — не менять семантику без осознанного ADR. |
| **Таблица витрины** | Одна таблица на отчётный срез; PK = гранулярность строки; `updated_at` с `onupdate`; индекс `(clinic_id, …)` под фильтр периода. |
| **Сервис** | Расширение `ErpAggregateService` **или** отдельные небольшие сервисы с общим mixin/helper (refresh, `max_updated_at_for_range`, маппинг NULL → bucket UUID при необходимости). |
| **API** | Существующие `GET .../payroll-by-period`, `.../materials-by-period`, `.../roi-by-source` — переключение на витрину под feature-flag/settings; тот же fallback/stale/empty, что и у `revenue-by-period`. |
| **Фон** | Расширить `erp_tasks.refresh_erp_aggregates_nightly` (или цепочку задач) на новые витрины; ручной `POST` по аналогии с `visit-revenue/refresh` (один общий роут с `kind` или три узких — см. TASK). |
| **Наблюдаемость** | Те же семейства метрик с лейблом `aggregate_kind` / `report_type`; логи `*_fallback_raw*`. |

### 2.2. Гранулярность (PK) — критично для совпадения с эталоном

Источник — текущий `GROUP BY` в `ErpReportsRepository`:

| Отчёт | Таблица-источник | Ключ витрины (логический) | Примечание |
|-------|------------------|---------------------------|------------|
| **Payroll** | `salary_transactions` | `(clinic_id, doctor_id, booking_id, period_start, period_end)` | Как в `get_visit_payroll_by_period`; `booking_id` NULL → отдельный bucket UUID (как `NULL_BOOKING_BUCKET` для выручки). |
| **Materials** | `inventory_transactions` | См. **§2.2a** — зерно витрины должно позволять ответ за **любой** `[date_from, date_to]` в лимите (как у выручки по дням). Рекомендуемый вариант: **дневная** гранулярность `(clinic_id, movement_date, product_id, booking_id)` с суммой quantity за день; итог за период = сумма дней (паритет с текущим эталоном — проверить тестом). |
| **ROI / attribution** | `financial_transactions` + `visit_attribution` | `(clinic_id, visit_date, traffic_source_id, campaign_id)` | Как `get_attribution_revenue_by_period`; NULL для source/campaign — bucket UUIDs или nullable колонки + уникальный индекс (предпочтительно bucket для PK стабильности). |

### 2.2a. Materials — почему недостаточно одного PK без даты

Текущий `get_visit_inventory_by_period` возвращает **одну** строку на `(product_id, booking_id)` на **весь** интервал. Если хранить в витрине только такое же зерно, то при **разных** запросах API с разными окнами одна и та же строка соответствует **разным** суммам — витрина не может одновременно кэшировать все диапазоны без дополнительного измерения.

**Решение для 026 (рекомендуется):** витрина materials с **дневной** осью `movement_date` (= дата `happened_at` в UTC или в согласованной TZ — как в эталонном SQL). Refresh: DELETE по `clinic_id` и `movement_date` в `[date_from, date_to]`, INSERT из дневной агрегации. Read API: `SUM(quantity)` по дням из витрины за запрошенный период, группировка до `(product_id, booking_id)` как у эталона — паритет обязателен в тесте.

**Альтернатива (не рекомендуется для общего API):** витрина только для **фиксированного** nightly-окна; при несовпадении запрошенного периода с окном — всегда raw.

### 2.3. Свежесть и пустая витрина

- **Свежесть (общее правило):** `max(updated_at)` по тем строкам витрины, которые **участвуют в ответе** на запрос `(clinic_id, date_from, date_to)`.
- **Visit-revenue / ROI:** есть естественная ось даты в строке (`visit_date`) — фильтр диапазона такой же, как у `max_aggregate_updated_at_for_range` в L2.
- **Payroll:** строки отбираются пересечением `period_start`/`period_end` с `[date_from, date_to]` — для stale нужен `max(updated_at)` **по этому же множеству строк** (SQL с тем же overlap-условием, что и fetch).
- **Materials:** при **дневной** витрине (§2.2a) — `max(updated_at)` по строкам с `movement_date` в `[date_from, date_to]` (аналог visit-revenue по дате в строке).
- **Пусто:** fallback на `ErpReportsRepository` + метрика `empty_vitrine` (как сейчас для выручки).
- **Устарело:** fallback на raw + `stale_range` + поля `data_source` / `aggregate_stale` в DTO (расширить `PayrollByPeriodReport`, `MaterialsByPeriodReport`, `RoiBySourceReport` — см. TASK).

### 2.4. RBAC и флаги

- Payroll / materials: `erp.owner_reports.read` (уже на роутерах).
- ROI: `attribution.reports.read` — отдельный контур; витрина только облегчает чтение, права не ослабляют.
- Settings: по аналогии с `ERP_REPORTS_READ_FROM_AGGREGATE` — либо три флага, либо один общий `ERP_VITRINES_READ_ENABLED` + маска (решение в DESIGN фазы TASK).

### 2.5. Что сознательно вне 026 (на потом)

- **Loyalty obligations** (`get_loyalty_obligations_snapshot`) — не периодный отчёт, а снимок; другой контракт инвалидации (отдельный мини-эпик или §«на потом» в L2).
- **CRM / LTV / owner dashboard** — другие запросы; подключать только если профилирование покажет ту же боль.

---

## 3. Рекомендуемый порядок внедрения

1. **Общая платформа** (миграции-шаблон, расширение Celery, общие хелперы) — короткий скелет без включения в прод.
2. **Payroll** — меньше join’ов, чем attribution; хороший первый «полный вертикальный» срез.
3. **Materials** — та же механика; внимание к гранулярности без даты в GROUP BY.
4. **Attribution / ROI** — тяжелее (join к атрибуции); индексы на FK подтвердить в TASK.

---

## 4. Критерии готовности эпика 026

- Для каждого из трёх отчётов: **паритет сумм/строк** с `ErpReportsRepository` на тестовых данных; тест на **stale** fallback (по образцу visit-revenue).
- Nightly refresh покрывает выбранный lookback для всех включённых витрин.
- Документация: ссылка из `ARCH_PERF_ENGINE_L2_DEEP_2026.md` §8.2 и краткий ops-блок (env, ручной refresh).

---

## 5. Связанные артефакты

- **`ARCH_DEV_ERP_VITRINES_026_TASKS.md`** — основной исполнительный документ (фазы 1–8, **026-1…026-8**, G1–G5).  
- `ARCH_PERF_ENGINE_L2_DEEP_2026.md`, `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS.md` §8.2 — связь с Engine L2 MVP (visit-revenue).  
- `ARCH_DEV_ERP_REPORTS_012.md`, `ARCH_DEV_ERP_REPORTS_012_TASKS.md` — владельческие отчёты и view-классы.  
- `ARCH_ERP_NEXT.md` §5, `ARCH_ATTRIBUTION_NEXT.md` §4 — доменные якоря.  
- `ARCH_DEV_PERF_SPOTS_024.md` §8.2, `DEV_EXECUTION_TRACKER_NEXT.md` §9 — трекинг перфа.  
- `NONFUNCTIONAL_AUDIT_NEXT.md` §5 — RBAC/свежесть витрины (паттерн как у revenue-by-period).
