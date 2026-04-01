## ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS — пошаговые задачи для @DEV (Engine L2)

> **Связанный план:** `ARCH_PERF_ENGINE_L2_DEEP_2026.md`  
> **Предпосылка:** v1 `DEV_PROMPT_PERF_SPOTS_024` сдан (см. `ARCH_DEV_PERF_SPOTS_024.md` §8).  
> **Роль:** выполнять **по фазам** (1→7), не смешивать крупную миграцию предагрегатов с курсором Kanban в одном PR без согласования с @LEAD.

---

### DEV_PROMPT (кратко, для контекста агента)

```
Реализуй Engine L2 глубокого перфоманса строго по docs/artifacts/ARCH_PERF_ENGINE_L2_DEEP_2026.md
и пошагово по docs/artifacts/ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS.md.

Инварианты: multi-tenant (clinic_id), RBAC, корректность ERP-фактов vs предагрегаты, AI/PD политика.
После каждой крупной фазы — тесты сверки сумм и регресс ключевых API.
```

---

### 1. Understand — инвентаризация перед изменениями

1.1. **ERP / отчёты: что считается «тяжёлым» сейчас.**  
1.1.1. Просмотреть `ErpReportsRepository`, `ReportsService`, роутер `admin_reports.py`: выписать эндпоинты с агрегациями по `financial_transactions`, attribution, payroll, materials, ROI.  
1.1.2. Для каждого — зафиксировать: используемые таблицы, типичный период запроса, наличие join’ов без лимита строк.  
1.1.3. Свериться с `ARCH_DEV_ERP_REPORTS_012.md` / `ARCH_DEV_ERP_REPORTS_012_TASKS.md` (если актуально).

1.2. **Celery / фон.**  
1.2.1. Найти `celery_app`, зарегистрированные очереди, существующие periodic tasks.  
1.2.2. Зафиксировать, куда логично добавить job пересчёта агрегатов (новая очередь `erp_reports` или общая).

1.3. **CRM Kanban: текущий контракт.**  
1.3.1. Зафиксировать `GET /admin/crm/leads` (projection, page, page_size), поведение после DnD, ключи React Query.  
1.3.2. Описать целевой контракт курсора: поля `cursor` / `next_cursor`, сортировка `(created_at DESC, id DESC)` на колонку.

1.4. **Фронт админки.**  
1.4.1. Зафиксировать страницы с длинными списками (Kanban, таблицы CRM, отчёты) — кандидаты на `@tanstack/react-virtual` или аналог.  
1.4.2. Оценить конфликт **dnd-kit** ↔ scroll/virtual (нужен единый scroll container на колонку).

1.5. **Redis / кэш (опционально для L2).**  
1.5.1. Проверить `redis_client`, политику ключей; оценить TTL для кэша дашбордов (если входит в scope).

---

### 2. Design‑to‑code — схема предагрегатов, API курсора, метрики job’ов

2.1. **Модель предагрегатов (первый срез).**  
2.1.1. Выбрать **1–2 витрины MVP** (например: выручка по дням по клинике; выручка/ROI по источнику трафика) — согласовать с @LEAD.  
2.1.2. Спроектировать таблицы (имена колонок, PK, индексы по `clinic_id`, `date`, измерениям).  
2.1.3. Описать правило **инкрементального** обновления (за вчера / за sliding window) и **полного** пересчёта за диапазон.  
2.1.4. Добавить DTO/чтение «только из витрины» vs fallback (если витрина пуста).

2.2. **События инвалидации.**  
2.2.1. Список доменных событий или триггеров, после которых нужен пересчёт (новая проводка, отмена визита и т.д.) — минимум для MVP: nightly + ручной `POST .../rebuild` под permission (опционально).

2.3. **Контракт курсора Kanban.**  
2.3.1. OpenAPI: query `stage_id`, `cursor` (opaque string или пара `created_at`+`id`), `limit` (cap).  
2.3.2. Ответ: `items`, `next_cursor | null`, `total` (опционально дорого — либо только для первой страницы, либо кэш).  
2.3.3. Обратная совместимость: старые `page`/`page_size` не ломать до deprecation.

2.4. **Метрики.**  
2.4.1. Имена Prometheus: `erp_aggregate_refresh_seconds`, `erp_aggregate_lag_seconds`, `erp_aggregate_rows_processed` (лейблы с низкой кардинальностью).  
2.4.2. Логирование job_id / clinic_id в structured logs (без PII).

---

### 3. Implement — предагрегаты + миграции

3.1. **Alembic.**  
3.1.1. Создать миграции под таблицы витрин из 2.1.  
3.1.2. Индексы под типичные фильтры отчётных API.

3.2. **Слой заполнения.**  
3.2.1. Реализовать `ErpAggregateService` (или расширить `ErpReportsRepository`) методами: `refresh_range(clinic_id, date_from, date_to)`, `refresh_all_clinics_nightly()`.  
3.2.2. SQL: INSERT … ON CONFLICT / DELETE+INSERT в зависимости от СУБД; транзакции по батчам.

3.3. **Сверка с эталоном.**  
3.3.1. Unit/integration тест: сумма по витрине за тестовый период == результату «сырого» запроса на тех же seed-данных (допуск — явный epsilon для decimal).  
3.3.2. Зафиксировать в тесте сценарий границы дня (timezone клиники, если применимо).

---

### 4. Implement — Celery + переключение отчётных API

4.1. **Задачи Celery.**  
4.1.1. Задача `refresh_erp_aggregates` с аргументами периода; retry, idempotency key.  
4.1.2. Расписание (celery beat / cron): nightly; опционально catch-up при старте.

4.2. **Переключение эндпоинтов.**  
4.2.1. Один отчётный эндпоинт MVP перевести на чтение витрины; feature-flag или settings (для быстрого отката).  
4.2.2. Fallback на старый путь при пустой витрине — только с логом `warn` и метрикой.

4.3. **Ограничения БД (опционально).**  
4.3.1. Отдельная DB role или `statement_timeout` для reporting-запросов — по согласованию с ops.

---

### 5. Implement — Kanban: курсор на backend + интеграция фронта

5.1. **Репозиторий / сервис.**  
5.1.1. Реализовать `list_leads_cursor(stage_id, cursor, limit, filters...)` с стабильной сортировкой.  
5.1.2. Кодирование cursor: base64(json) или `created_at|lead_id`; валидация границ клиники.

5.2. **Роутер.**  
5.2.1. Новый query или расширение существующего `GET .../leads` — документация OpenAPI.  
5.2.2. Тесты API: первая страница, вторая по `next_cursor`, пустая колонка.

5.3. **Фронт.**  
5.3.1. React Query: ключи с `cursor`, «Загрузить ещё» в колонке (или intersection observer).  
5.3.2. Согласовать инвалидацию после `PATCH .../stage` (DnD): обновить затронутые колонки без полного сброса всего кэша (по возможности).

---

### 6. Implement — виртуализация списков (фронт)

6.1. **Зависимость.**  
6.1.1. Добавить `@tanstack/react-virtual` (или выбранный аналог), зафиксировать версию.

6.2. **Kanban колонка.**  
6.2.1. Обернуть список карточек в virtualizer; задать `estimateSize` / измерение.  
6.2.2. Проверить drag-and-drop: зона droppable и scroll одной колонки; при необходимости `DragOverlay`.

6.3. **Регресс UI.**  
6.3.1. Прогон `AdminSalesPipelinePage` тестов; ручной чек-лист: скролл, drag, выбор лида.

---

### 7. Observe — наблюдаемость и нагрузка

7.1. **Дашборды / алерты.**  
7.1.1. Grafana/Prometheus: панели по job duration, lag, ошибкам refresh.  
7.1.2. Алерт: lag > N часов или рост ошибок refresh.

7.2. **Нагрузочный smoke (staging).**  
7.2.1. Сценарий: отчёт за 90 дней + Kanban с курсором по 3 колонкам.  
7.2.2. Зафиксировать целевые пороги (latency p95) в комментарии или `NONFUNCTIONAL_AUDIT_NEXT.md`.

---

### 8. Stabilize — документация и закрытие GAPS

*Частично закрыто (QA_ARCH, 2026-03): §6 `ARCH_PERF_ENGINE_L2_DEEP_2026.md`, §5 `NONFUNCTIONAL_AUDIT_NEXT.md`; ops-runbook (ручной refresh / flag) — по желанию дополнить §8.1.3.*

8.1. **Документация.**  
8.1.1. Обновить `ARCH_PERF_ENGINE_L2_DEEP_2026.md` — статус MVP (что сделано).  
8.1.2. Обновить `NONFUNCTIONAL_AUDIT_NEXT.md`, при необходимости `BACKEND_GAPS_*` / `FRONTEND_GAPS_*`.  
8.1.3. Краткая инструкция для ops: как вручную дернуть пересчёт, как откатить feature-flag.

8.2. **Расширение покрытия.**  
8.2.1. ~~Перенести остальные тяжёлые отчёты на витрины~~ — **сделано (2026-03):** payroll, materials, ROI по `ARCH_DEV_ERP_VITRINES_026*.md` (миграции `m8n9o0p1q2r3`, `n0o1p2q3r4s5`). Дальнейшие улучшения — §«На потом» в конце этого файла и в `ARCH_DEV_ERP_VITRINES_026_TASKS.md`.  
8.2.2. Redis read-through для дашбордов — если ещё актуально после витрин.

---

### Критерии приёмки (минимум для закрытия MVP L2)

- [x] По меньшей мере **одна** витрина заполняется job’ом и используется отчётным API; тесты сверки сумм зелёные.  
- [x] Celery job **наблюдаем** (метрики + логи).  
- [x] Kanban: **курсор** работает для одной колонки end-to-end; виртуализация включена без поломки DnD.  
- [x] Нет нарушений tenant/RBAC; откат через flag возможен. **Дополнительно (QA):** миграция прав в БД `k7l8m9n0o1p2`, контроль устаревшей витрины по диапазону дат + метаданные в ответе `revenue-by-period`.

---

### Выполнено сверх чеклиста (QA_ARCH / follow-up)

- §8.1: фрагмент в `NONFUNCTIONAL_AUDIT_NEXT.md` §5–§6 (RBAC-миграция, свежесть витрины, пустая витрина, пороги алертов, кардинальность метрик).  
- Интеграционный тест: устаревшая витрина → raw + `aggregate_stale` (`tests/services/test_erp_aggregate_parity.py`).

---

### На потом (вне MVP L2, по желанию @LEAD)

**Уже было в списке**

- ~~Read replica для read-only отчётов.~~ — **частично закрыто Wave 5 (2026-03):** optional `DATABASE_REPLICA_URL`, `get_reporting_session`, `GET /health/replica`, gauge lag; см. `QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md` (статус Wave 5).  
- Параллелизация Omni AI / budget — см. `ARCH_DEV_OMNI_REGISTRY_015.md`.  
- ~~Полный индексный аудит `financial_transactions` и смежных таблиц.~~ — **частично Wave 5:** миграция `w5perf1idx_fin`, шаблоны `WAVE5_A3_EXPLAIN_QUERIES.sql`; полный аудит ROI/attribution — см. `QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG.md`.  
- ~~Перф-бюджет в CI (k6/Locust).~~ — **частично Wave 5:** optional workflow + smoke; пороги p95 на staging — пост-waves.

**Предложения QA_ARCH / Engine L2 (на потом)**

- **Пустая витрина:** таблица или строка «watermark» покрытия диапазона per-clinic (`last_refresh_from` / `to` или version), чтобы при согласованной политике не делать полный raw-scan при нулевой выручке после успешного refresh.  
- ~~**Больше витрин:** payroll, materials, ROI~~ — **реализовано (2026-03)**; см. §6 `ARCH_PERF_ENGINE_L2_DEEP_2026.md`, детали и «на потом» post-026 — `ARCH_DEV_ERP_VITRINES_026_TASKS.md`.  
- **Инвалидация:** не только nightly, а подписка на доменные события (проводка, отмена визита) с дебаунсом/очередью пересчёта окна.  
- **Наблюдаемость:** дашборд/алерты по `erp_aggregate_read_fallback_total` (особенно `stale_range`, `empty_vitrine`) и по p95 лагу из `erp_aggregate_lag_seconds` — **приоритет после внедрения витрин** (панели по `aggregate_kind`).  
- **RBAC:** явно решить, нужны ли `erp.owner_reports.read` / `attribution.reports.read` роли `manager` (сейчас только `owner` в матрице и в миграции `k7l8m9n0o1p2`); unified `POST .../erp-aggregates/refresh` для `attribution`/`all` уже требует `attribution.reports.read`.  
- **Ограничения БД:** ~~`statement_timeout`~~ — **приложение:** `DB_REPORTING_STATEMENT_TIMEOUT_MS` на reporting-сессии (Wave 5); отдельная **роль** PG reporting — ops.  
- **Кэш:** ~~Redis read-through для дашбордов~~ — **реализовано Wave 5** (`erp_report_cache`, метрики `erp_dashboard_cache_*`).  
- **Per-report feature flags** и **аудит** вызова ручного POST (admin id), **E2E** отчётов на витрине, **тесты на отрицательные суммы** — см. расширенный список в `ARCH_DEV_ERP_VITRINES_026_TASKS.md` §«На потом».
