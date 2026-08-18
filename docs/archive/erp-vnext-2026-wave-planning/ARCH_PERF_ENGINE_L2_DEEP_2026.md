# ARCH_PERF_ENGINE_L2_DEEP_2026 — глубокий перфоманс (Engine L2)

> **Поиск по репозиторию:** `ARCH_PERF_ENGINE_L2_DEEP` или `PERF_ENGINE_L2`  
> **Связь:** продолжение `ARCH_DEV_PERF_SPOTS_024.md` / `DEV_PROMPT_PERF_SPOTS_024` после v1 (точечные оптимизации уже в коде — см. §8 в ARCH).  
> **Пошаговые задачи для @DEV:** `ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS.md`

---

## 1. Зачем отдельный план

Итерация **PERF_SPOTS v1** закрыла «быстрые выигрыши»: лёгкая проекция Kanban, один SQL на список+total, лимиты периода отчётов, HTTP‑метрики.  
**Engine L2** — это **изменение архитектуры данных и фона**, плюс **тяжёлый фронт** (виртуализация, курсоры). Без отдельного плана высок риск половинчатых миграций и расхождений отчётов с «сырыми» проводками.

**Инварианты** (не ослаблять): multi‑tenant, RBAC, корректность ERP‑фактов, AI/PD‑политика.

---

## 2. Обязательный квартет (из PERF‑024, вне v1)

### 2.1. Материализованные предагрегаты ERP / Attribution

- **Суть:** таблицы или materialized views по **дням / клинике / источнику / кампании** (и др. зрелым измерениям из `ErpReportsRepository` / отчётов владельца).
- **Работы:** схема Alembic, правила **инкрементального** обновления и **полного** пересчёта за окно, сверка с «сырыми» `financial_transactions` (тесты на суммы).
- **API:** отчётные эндпоинты читают слой агрегатов; онлайн‑скан «сырья» за год — только как fallback или под отдельным permission + жёстким лимитом.

### 2.2. Фоновые пересчёты (Celery / cron)

- **Суть:** расписание (например ночной roll-up + catch-up при бэклоге), идемпотентные задачи, метрики: длительность job, lag, ошибки.
- **Связь:** питает §2.1; без фона предагрегаты устаревают и бесполезны.

### 2.3. Пакет виртуализации списков (фронт админки)

- **Суть:** например `@tanstack/react-virtual` (или аналог) для **колонок Kanban** и длинных таблиц CRM/списков, при сохранении UX **dnd-kit** (измерение высоты, scroll container).
- **Критерий:** стабильный FPS при сотнях карточек без роста DOM линейно.

### 2.4. Курсорная пагинация по колонкам Kanban

- **Суть:** контракт API `stage_id` + **cursor** (стабильная сортировка, например `created_at desc, id desc`) + `limit`; опционально «загрузить ещё» в каждой колонке.
- **Связь:** согласовать с фильтрами, инвалидацией React Query после DnD, оптимистичными обновлениями.

---

## 3. Дополнительные направления с высоким эффектом

| Направление | Зачем |
|-------------|--------|
| **Индексный аудит** по таблицам отчётов (`financial_transactions`, attribution, bookings под join’ы ERP) | Снижение CPU и блокировок до внедрения предагрегатов |
| **Ограничения БД** для тяжёлых отчётов: `statement_timeout` на роль reporting, лимит строк | Предсказуемость под нагрузкой |
| **Кэш read-through (Redis)** для редко меняющихся дашбордов с теми же ключами, что и период/клиника | Быстрый повторный просмотр без удара в БД |
| **Omnichannel / AI:** параллелизация независимых LLM‑шагов, единый **budget** времени на ответ, circuit breaker к провайдеру | См. `ARCH_DEV_OMNI_REGISTRY_015.md` |
| **Пулы соединений и мониторинг** `pool overflow` / wait time | Ранний сигнал исчерпания коннектов при отчётах |
| **Read replica** только для read-only отчётов (при масштабе) | Разгрузка primary |
| **Перф-бюджет в CI:** smoke на латентность ключевых API или пороги k6/Locust на staging | Регресс перфа не «случайно» |
| **Батчевые эндпоинты** где фронт делает N запросов подряд | Меньше round-trips |

Приоритет L2 внутри таблицы — по бизнесу: обычно **ERP предагрегаты + Celery** первыми, затем **Kanban cursor + virtual**, затем кэш и прочее.

---

## 4. Предлагаемые фазы внедрения

1. **Design:** схема предагрегатов, контракт инвалидации, контракт курсора Kanban, выбор библиотеки виртуализации.  
2. **MVP предагрегатов:** одна-две витрины (например выручка по дням + ROI по источнику) + Celery job + переключение одного отчётного API.  
3. **Расширение:** остальные тяжёлые отчёты, мониторинг расхождений.  
4. **Kanban:** API курсора + UI подгрузки + виртуализация колонок.  
5. **Stabilize:** нагрузочные сценарии, обновление `NONFUNCTIONAL_AUDIT_NEXT.md`, SLO в `ARCH_DECISIONS_NEXT.md` при необходимости.

---

## 5. Критерии готовности (L2)

- Отчёты на предагрегатах **совпадают** с эталоном на контрольном периоде (автотесты + выборочная сверка).  
- Фоновые job’ы **наблюдаемы** (метрики, алерты на lag).  
- Kanban при большом числе лидов — **приемлемый** TTFB и интерактивность (замеры до/после).  
- Нет регрессии **RBAC / tenant / AI policy**.

---

## 6. Статус MVP (код)

- **Витрины L2:** `erp_visit_revenue_aggregate`, `erp_payroll_aggregate`, `erp_inventory_movement_aggregate` (дневная гранулярность), `erp_attribution_revenue_aggregate` + `ErpAggregateService`: пересчёт за диапазон, чтение в `GET .../reports/revenue-by-period`, `.../payroll-by-period`, `.../materials-by-period`, `.../roi-by-source` при `ERP_REPORTS_READ_FROM_AGGREGATE` (fallback на сырой SQL + `warn` + метрика при пустой витрине).
- **Свежесть витрины:** лаг по `max(updated_at)` в окне ответа (для payroll — пересечение периода с запросом; для materials — по `movement_date`; для ROI — по `visit_date`, как у выручки). Если лаг превышает `ERP_AGGREGATE_STALE_MAX_SECONDS` (по умолчанию 7200) — fallback на raw, метрика `erp_aggregate_read_fallback_total{reason="stale_range"}`, в ответе API поля `data_source`, `aggregate_max_updated_at`, `aggregate_stale`. Пустая витрина → raw (`empty_vitrine`); отдельного «доверия нулю» без маркера покрытия нет — см. §5 в `NONFUNCTIONAL_AUDIT_NEXT.md`.
- **Celery** `erp_tasks.refresh_erp_aggregates_nightly` (beat 03:30 UTC) + ручной `POST .../reports/erp-aggregates/refresh` (`kind`: `visit_revenue` | `payroll` | `materials` | `attribution` | `all`) и legacy `POST .../erp-aggregates/visit-revenue/refresh`. Права: `erp.owner_reports.read`; для `kind` `attribution` или `all` дополнительно `attribution.reports.read`.
- **Метрики** `erp_aggregate_*` в `src/core/metrics.py`.
- **Kanban** `GET /admin/crm/leads`: `pagination=cursor` + `projection=kanban`, сортировка `(created_at DESC, id DESC)`, поля `next_cursor` / `total` (первая страница).
- **Фронт** `@tanstack/react-virtual` по колонке, `useCrmKanbanStageLeadsInfinite`, кнопка «Загрузить ещё».
- **RBAC**: в матрицу добавлены `erp.owner_reports.read`, `attribution.reports.read` (ранее использовались роутером без строки в `PERMISSIONS`). **Data-migration в БД:** `k7l8m9n0o1p2_erp_reports_rbac_permissions` — INSERT в `permissions` + привязка к ролям `owner` per-clinic (после `alembic upgrade head` нет 403 на проде из-за отсутствия строк в `permissions`).

Миграции Alembic: `j6k7l8m9n0o1_erp_visit_revenue_aggregate` (+ индекс Kanban), `k7l8m9n0o1p2_erp_reports_rbac_permissions`, `m8n9o0p1q2r3_erp_vitrines_payroll_materials_attribution`, `n0o1p2q3r4s5_erp_payroll_aggregate_null_flags` (флаги NULL для границ периода payroll).

- **Wave 5 (2026-03, QA_ARCH пакет perf/инфра):** optional read replica + reporting `statement_timeout` + Redis JSON-кэш для admin-дашбордов + миграция индексов `financial_transactions`/`salary_transactions` (`w5perf1idx_fin`) + k6 optional + `GET /health/replica` + метрики кэша. Сводка ID: `./QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md` (блок «Статус Wave 5»), runbook: `./WAVE5_OPS_RUNBOOK.md`.

---

## 7. Связанные артефакты

- **`ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS.md`** — пошаговый TASK для реализации (MVP по §6 закрыт в коде; чеклист и «на потом» актуализированы)  
- `ARCH_DEV_PERF_SPOTS_024.md`, `ARCH_DEV_PERF_SPOTS_024_TASKS.md`  
- `ARCH_DEV_ERP_REPORTS_012.md` (если есть)  
- **`ARCH_DEV_ERP_VITRINES_026.md`** — архитектура эпика: payroll / materials / ROI (attribution) поверх `ErpReportsRepository`; **статус реализации (2026-03)** в начале файла  
- **`ARCH_DEV_ERP_VITRINES_026_TASKS.md`** — пошаговые фазы **026-1…026-8**, go/no-go **G1–G5** (закрыты), DEV_PROMPT, рубрика **«На потом»** (post-026)  
- `ARCH_ERP_NEXT.md`, `ARCH_ATTRIBUTION_NEXT.md`  
- `ARCH_DEV_OMNI_REGISTRY_015.md`, `ARCH_DEV_OBS_CHAINS_023.md`  
- `NONFUNCTIONAL_AUDIT_NEXT.md`
