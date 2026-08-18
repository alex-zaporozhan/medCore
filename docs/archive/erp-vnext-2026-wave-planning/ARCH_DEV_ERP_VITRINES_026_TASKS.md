## ARCH_DEV_ERP_VITRINES_026_TASKS — таски по витринам payroll / materials / ROI (attribution)

> **Архитектура:** `ARCH_DEV_ERP_VITRINES_026.md`  
> **Эталон кода:** витрина выручки по визитам (`erp_visit_revenue_aggregate`, `ErpAggregateService`, `admin_reports` `revenue-by-period`, `erp_tasks`).  
> **Где ещё упоминается эпик:** `ARCH_PERF_ENGINE_L2_DEEP_2026.md` §7, `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS.md` §8.2 / «На потом», `NONFUNCTIONAL_AUDIT_NEXT.md` §5, `ARCH_DEV_ERP_REPORTS_012.md` §1.3, `ARCH_ERP_NEXT.md` §5, `ARCH_ATTRIBUTION_NEXT.md` §4, `ARCH_DEV_PERF_SPOTS_024.md` §8.2, `DEV_EXECUTION_TRACKER_NEXT.md` §9.  
> **Роль @DEV:** выполнять **по фазам 1→8**; вертикали **026-4 / 026-5 / 026-6** (payroll / materials / ROI) — по отдельным PR; фаза **026-7** (Celery + общий POST refresh) — после или вместе с последней включённой вертикалью, по согласованию с @LEAD.

**Ключевые файлы (старт реализации):**  
`src/application/services/erp_reports_repository.py`, `erp_aggregate_service.py`, `src/api/v1/routers/admin_reports.py`, `src/application/dto/reports_dto.py`, `src/core/config.py`, `src/infrastructure/messaging/tasks/erp_tasks.py`, `tests/services/test_erp_aggregate_parity.py`.

**Порядок PR (минимум):** `026-3` (скелет: миграции + сущности без включения read-path) → `026-4` payroll → `026-5` materials → `026-6` ROI → `026-7` Celery/unified POST → `026-8` стабилизация. *Materials зависит от явного решения §2.6 (дневная гранулярность).*

**Статус (2026-03, QA_ARCH):** фазы **026-3…026-8** и интеграция в L2 выполнены в коде; мастер-флаг **`ERP_REPORTS_READ_FROM_AGGREGATE`** на read-path; **per-kind overrides** `ERP_VISIT_REVENUE_READ_FROM_AGGREGATE` / `ERP_PAYROLL_*` / `ERP_MATERIALS_*` / `ERP_ATTRIBUTION_*` (nullable → мастер) — см. `Settings.erp_read_from_aggregate_for_kind`. **Аудит ручного POST refresh:** таблица **`erp_aggregate_manual_refresh_audit`**, лог `erp_manual_refresh_audit`. Дополнительно: миграция **`n0o1p2q3r4s5`** (payroll NULL-флаги), **`resolve_erp_aggregate_rows`**, RBAC на unified POST, тесты stale/API/RBAC.

**Nightly refresh — транзакционная семантика (QA_ARCH 2026-03):** для каждой клиники выполняется **одна** транзакция с `pg_advisory_xact_lock` и вызовом **`refresh_clinic_erp_aggregates_window`** (все четыре витрины подряд). При **любом** исключении откатываются **все** четыре вида для этой клиники в этом прогоне (атомарность окна). Метрика **`erp_aggregate_nightly_kind_failures_total`** инкрементируется **по каждому виду** (четыре раза на одну ошибку) для совместимости с алертами; **детализация по клинике** — только в **логах** (`erp_aggregate_refresh_clinic_failed`, поле `clinic_id`). Частично «свежие» витрины по kind при сбое соседа **не остаются** — осознанный trade-off в пользу согласованности среза.

**Watermark / пустой ряд:** см. `erp_aggregate_coverage_watermark`, `NONFUNCTIONAL_AUDIT_NEXT.md` §5.1; счётчик **`erp_aggregate_empty_trusted_total`**.

---

### DEV_PROMPT (кратко)

```
Расширь шаблон Engine L2 (предагрегаты ERP) на payroll, materials и ROI/attribution
строго по ./ARCH_DEV_ERP_VITRINES_026.md и
./ARCH_DEV_ERP_VITRINES_026_TASKS.md.

Инварианты: clinic_id везде, RBAC (erp.owner_reports.read / attribution.reports.read),
паритет строк и сумм с ErpReportsRepository, без изменения семантики «сырых» методов без ADR.
```

---

### 1. Understand — инвентаризация и границы

1.1. **Зафиксировать эталонные методы и эндпоинты.**  
1.1.1. `ErpReportsRepository.get_visit_payroll_by_period` → `GET .../reports/payroll-by-period`.  
1.1.2. `get_visit_inventory_by_period` → `GET .../reports/materials-by-period`.  
1.1.3. `get_attribution_revenue_by_period` → `GET .../reports/roi-by-source`.  
1.1.4. Выписать для каждого: поля DTO, ограничение периода (`MAX_REPORT_PERIOD_DAYS`), текущие индексы таблиц (см. миграции/индексы по `salary_transactions`, `inventory_transactions`, `financial_transactions`, `visit_attributions`).

1.2. **Сопоставить с существующей витриной visit-revenue.**  
1.2.1. Прочитать `ErpAggregateService`, `ErpVisitRevenueAggregate`, обработку stale/empty в `admin_reports`.  
1.2.2. Составить таблицу «что копируем 1:1» vs «что отличается по PK/permission».

1.3. **Вне scope 026 (только ссылка).**  
1.3.1. `get_loyalty_obligations_snapshot`, owner dashboard, patient LTV — не входят в этот эпик, кроме краткой заметки в `ARCH_DEV_ERP_VITRINES_026.md` §2.5.

1.4. **Границы идентичности транзакций.**  
1.4.1. Зафиксировать: изменение **только** SQL/ORM в `ErpReportsRepository` для перфа без изменения бизнес-смысла — через ADR или отдельный тикет; в 026 витрина **зеркалит** текущий метод как чёрный ящик.  
1.4.2. Убедиться, что income / quantity / salary **отрицательные** и **корректировки** (если появятся в данных) отражаются в эталоне и в витрине одинаково (тест-кейс при необходимости).

---

### 2. Design — общая платформа витрин (shared)

2.1. **Именование и миграции.**  
2.1.1. Три новые таблицы (рабочие имена): `erp_payroll_aggregate`, `erp_inventory_movement_aggregate`, `erp_attribution_revenue_aggregate` — уточнить имена до Alembic.  
2.1.2. Для каждой: PK, типы колонок, `updated_at`, индексы `(clinic_id, …)` под `date_from`/`date_to` или overlap-запросы.  
2.1.3. NULL в PK: использовать фиксированные bucket UUID (как `NULL_BOOKING_BUCKET`) для `booking_id` / `traffic_source_id` / `campaign_id` где нужно.  
2.1.4. Вынести константы bucket’ов в один модуль (например рядом с `erp_visit_revenue_aggregate.py` или общий `src/domain/entities/erp_report_buckets.py`) — избежать дублирования UUID.

2.2. **Сервисный слой.**
2.2.1. Решение: расширить `ErpAggregateService` методами `refresh_payroll_range`, `refresh_inventory_range`, `refresh_attribution_revenue_range` + `fetch_*` + `max_*_updated_at_for_range` **или** выделить общий базовый класс с параметрами entity/mapper (минимизировать дублирование).  
2.2.2. Общий контракт refresh: DELETE строк клиники в `[date_from, date_to]` по правилам окна (**payroll** — overlap по `period_start`/`period_end`; **materials** — см. §2.6, DELETE по `movement_date` в окне; **attribution** — по `visit_date` в окне); INSERT из эталонного запроса (см. §2.6 для materials).  
2.2.3. **Свежесть (stale):** **payroll** — `max(updated_at)` по строкам витрины, у которых период пересекается с запросом (тот же predicate, что у `fetch`, см. ARCH §2.3). **materials** (дневная витрина) — `max(updated_at)` где `movement_date` в `[date_from, date_to]`. **attribution** — как visit-revenue по `visit_date`.  
2.2.4. **Идемпотентность refresh:** повторный `refresh` с тем же диапазоном даёт тот же набор строк; параллельные refresh по одной клинике — вне MVP (опционально advisory lock / очередь на клинику).

2.3. **Конфигурация.**
2.3.1. Флаги чтения: три отдельных `settings` (`erp_payroll_read_from_aggregate`, …) **или** один мастер-флаг + per-kind (зафиксировать в PR).  
2.3.2. Порог устаревания: переиспользовать `erp_aggregate_stale_max_seconds` или завести per-report override — выбрать и описать в `config.py`.

2.4. **API и DTO.**  
2.4.1. Расширить `PayrollByPeriodReport`, `MaterialsByPeriodReport`, `RoiBySourceReport` полями `data_source`, `aggregate_max_updated_at`, `aggregate_stale` (как `VisitRevenueByPeriodReport`).  
2.4.2. Единый стиль метрик: `erp_aggregate_read_fallback_total{report_type="payroll-by-period"|…, reason=…}`.  
2.4.3. **Порядок элементов** в `items`: сохранить тот же порядок, что у эталонного списка из `ErpReportsRepository` (или явно задать `order_by` в fetch из витрины под текущий контракт фронта / OpenAPI).

2.5. **Celery и ручной refresh.**  
2.5.1. Расширить `refresh_erp_aggregates_nightly` (или добавить подзадачи) для новых витрин с тем же lookback, что visit-revenue.  
2.5.2. Ручной пересчёт: либо `POST .../erp-aggregates/refresh` с телом `{ "kind": "payroll"|"materials"|"attribution"|"visit_revenue", "date_from", "date_to" }`, либо три эндпоинта по аналогии — согласовать с ops (один роут предпочтительнее для сопровождения).  
2.5.3. **Lag-метрика:** при успешном чтении из витрины вызывать `erp_aggregate_lag_seconds.observe(...)` с лейблом `aggregate_kind`, как для `revenue-by-period`.

2.6. **Materials — зерно витрины (обязательно до кодирования §5).**  
2.6.1. Принять подход из `ARCH_DEV_ERP_VITRINES_026.md` §2.2a: **дневная** витрина `(clinic_id, movement_date, product_id, booking_bucket_id, quantity_day)` (имена уточнить).  
2.6.2. Добавить в `ErpReportsRepository` метод дневной агрегации **или** private SQL в `ErpAggregateService.refresh_inventory_range`, дающий те же суммы по `(product_id, booking_id)` за произвольный период, что и `get_visit_inventory_by_period` (сумма дней = эталон) — **покрыть интеграционным тестом паритета**.  
2.6.3. Read-path: из витрины читать дневные строки в диапазоне, **свернуть** в список как у текущего DTO (`ErpVisitInventoryView`), сохранить §2.4.3 порядок.

---

### 3. Implement — инфраструктура после design (скелет)

3.1. **Alembic.**  
3.1.1. Одна миграция на три таблицы **или** три микро-миграции по одной витрине (предпочтительно одна ревизия для атомарного roll-forward на staging).  
3.1.2. Downgrade: дроп таблиц / индексов.

3.2. **ORM-сущности** в `src/domain/entities/`.  
3.2.1. Три entity-класса + экспорт в `entities/__init__.py` при принятом стиле проекта.

3.3. **Метрики.**  
3.3.1. Добавить/расширить лейблы `aggregate_kind` для refresh/lag/fallback, не раздувая кардинальность.

---

### 4. Implement — модуль Payroll (первая вертикаль)

4.1. **Refresh и read.**  
4.1.1. `refresh_payroll_range`: DELETE по правилу overlap с `[date_from, date_to]` для клиники; INSERT из `get_visit_payroll_by_period` с тем же диапазоном.  
4.1.2. `fetch_payroll_aggregate` → те же структуры, что сейчас собирает роутер из `ErpVisitPayrollView`.  
4.1.3. `max_updated_at_for_range` для payroll (пересечение `period_start`/`period_end` с запросом — см. ARCH §2.3).

4.2. **Роутер `payroll-by-period`.**  
4.2.1. Ветка «читать из витрины» + stale + empty fallback; логи и метрики по образцу `revenue-by-period`.  
4.2.2. Не ломать OpenAPI: новые поля optional с default null при необходимости.

4.3. **Тесты.**  
4.3.1. Интеграционный тест паритета: после refresh суммы и набор строк совпадают с прямым вызовом репозитория.  
4.3.2. Тест stale → raw + `aggregate_stale` (аналог `test_erp_aggregate_parity`).

---

### 5. Implement — модуль Materials (inventory)

5.0. **Предпосылка:** закрыт §2.6 (дневная витрина + тест паритета «сумма дней = `get_visit_inventory_by_period`»).

5.1. **Refresh и read.**  
5.1.1. `refresh_inventory_range`: DELETE по `clinic_id` и `movement_date` в `[date_from, date_to]`; INSERT дневных строк из §2.6.2.  
5.1.2. `fetch_inventory_aggregate`: выбрать дневные строки за период, **сгруппировать** до `(product_id, booking_id)` с суммой `quantity`, отдать как `ErpVisitInventoryView`.  
5.1.3. `max_updated_at_for_range`: `max(updated_at)` по строкам с `movement_date` в запрошенном интервале.

5.2. **Роутер `materials-by-period`.**  
5.2.1. Переключение на витрину, метаданные stale/empty, DTO.

5.3. **Тесты.**  
5.3.1. Паритет + stale (как §4.3).

---

### 6. Implement — модуль ROI / Attribution

6.1. **Refresh и read.**  
6.1.1. Витрина по ключу `(visit_date, traffic_source_id, campaign_id)` + bucket’ы для NULL.  
6.1.2. Refresh из `get_attribution_revenue_by_period`.

6.2. **Роутер `roi-by-source`.**  
6.2.1. Permission `attribution.reports.read` без изменений.  
6.2.2. Те же поля метаданных ответа.

6.3. **Индексы и перф.**  
6.3.1. Проверить план запроса эталона; при необходимости добавить индекс под `FinancialTransaction.visit_attribution_id` / join к `VisitAttribution` (отдельная микро-миграция при доказанной необходимости).

6.4. **Тесты.**  
6.4.1. Паритет + stale; минимальный сценарий с `visit_attribution_id` на income-транзакции.

---

### 7. Implement — Celery, beat, ops

7.1. **Nightly.**  
7.1.1. Вызов refresh для всех включённых витрин по всем клиникам; идемпотентность; лог `clinic_id` без PII.  
7.1.2. Обработка ошибок: один сбой клиники не валит остальные (как в visit-revenue).

7.2. **Ручной refresh и документация.**  
7.2.1. Описать в `../../MIGRATION_UPGRADE.md` или кратком runbook: env-флаги, вызов POST, откат на raw.

---

### 8. Stabilize — приёмка эпика 026

8.1. **Регрессия.**  
8.1.1. Прогон всех тестов API/сервисов, затронутых отчётами.  
8.1.2. Обновить `ARCH_PERF_ENGINE_L2_DEEP_2026.md` §6 или §8.2 — ссылка на завершение payroll/materials/ROI витрин.

8.2. **Наблюдаемость.**  
8.2.1. Чек-лист Grafana: панели по новым `aggregate_kind`, алерты на рост `empty_vitrine`/`stale_range` (опционально).

---

### Нумерация модулей (для ссылок в PR и чатах)

| Код | Содержание |
|-----|------------|
| **026-1** | Фаза 1 (Understand) — можно закрыть документом/таблицей без кода. |
| **026-2** | Фаза 2 (Design shared) — ADR-lite в комментарии к PR или в ARCH. |
| **026-3** | Фаза 3 (Alembic + entities + метрики-скелет). |
| **026-4** | Фаза 4 — **Payroll** end-to-end. |
| **026-5** | Фаза 5 — **Materials** end-to-end. |
| **026-6** | Фаза 6 — **ROI / Attribution** end-to-end. |
| **026-7** | Фаза 7 — Celery + ручной refresh + ops-док. |
| **026-8** | Фаза 8 — Stabilize + обновление ссылок в L2. |

---

### Ревью архитектуры (чек-лист для @ARCH / QA)

| Тема | Статус в 026 |
|------|----------------|
| PK / гранулярность | Payroll / ROI = как GROUP BY эталона; **materials = дневная витрина §2.6 + ARCH §2.2a** (иначе кэш по произвольному периоду невозможен). |
| Стабильность NULL в PK | Bucket UUID §2.1.3–2.1.4. |
| Семантика stale | §2.2.3 (payroll overlap; materials по `movement_date`; attribution по `visit_date`). |
| RBAC | ARCH §2.4. |
| Параллельный refresh | §2.2.4 (вне MVP). |
| Порядок `items` | §2.4.3. |
| Индексы ROI | Фаза 6.3. |
| Loyalty / LTV / dashboard | Вне scope §1.3. |
| Lag histogram | §2.5.3. |

---

### QA_ARCH — готовность к запуску кода (go / no-go)

| # | Критерий | Статус |
|---|-----------|--------|
| G1 | Прочитаны эталонные методы в `erp_reports_repository.py` и текущие GET в `admin_reports.py` | [x] закрыто (2026-03) |
| G2 | Решение по **materials** §2.6 зафиксировано (дневная витрина + тест паритета) | [x] закрыто (2026-03) |
| G3 | Выбраны флаги `settings` §2.3.1 и порог stale §2.3.2 | [x] мастер-флаг + `erp_aggregate_stale_max_seconds` (2026-03) |
| G4 | Скелет **026-3** (таблицы под выбранные PK) согласован с миграциями | [x] `m8n9o0p1q2r3` + `n0o1p2q3r4s5` payroll (2026-03) |
| G5 | Есть тестовый план: паритет + stale на каждую вертикаль (§4.3, §5.3, §6.4) | [x] `test_erp_aggregate_parity.py` (2026-03) |

G1–G5 выполнены; дальнейшие улучшения — в рубрике **«На потом»** ниже.

---

### На потом (вне 026 или post-merge улучшения)

**Уже было (вне scope эпика)**

- Витрина / снимок для **loyalty obligations** (другая семантика времени).  
- Объединение POST refresh в единый **batch** по клинике с дедупликацией.  
- Read-through Redis поверх витрин для горячих дашбордов.  
- **Часовой пояс клиники:** сейчас эталонные запросы завязаны на комбинацию `date` + `datetime` в коде репозитория — при появлении `clinic.timezone` сверить границы дня для refresh и для API.  
- **Аудит:** кто вызвал ручной POST refresh (admin id) — для финансовых сценариев.

**Предложения QA_ARCH (после закрытия 026, 2026-03)**

- **Per-report флаги:** опциональные `settings` на каждый отчёт (payroll / materials / ROI) поверх `ERP_REPORTS_READ_FROM_AGGREGATE` — поэтапный rollout на проде.  
- **Индекс ROI** — §6.3: `EXPLAIN` эталона `get_attribution_revenue_by_period`; при необходимости микро-миграция под `FK visit_attribution_id` / join к `VisitAttribution`.  
- **Отрицательные суммы / корректировки** — явный тест-кейс §1.4.2 (income / quantity / salary), если в данных появятся корректировки.  
- **Наблюдаемость:** дашборд/алерты Grafana по `erp_aggregate_read_fallback_total` (`empty_vitrine`, `stale_range`) и p95 `erp_aggregate_lag_seconds` по `aggregate_kind` (критерий §8.2).  
- **Фронт:** опционально показать в UI `data_source` / `aggregate_stale` для прозрачности OPS (сейчас поля optional в API).  
- **Порядок `items` materials:** эталонный SQL без `ORDER BY`; из витрины — детерминированная сортировка; при регрессии UX — зафиксировать `order_by` в контракте или в OpenAPI.  
- **Nightly:** мониторинг «все четыре вида успешно за ночь по клинике» при частичных сбоях (частично заполненный набор витрин до следующего успешного прогона).
