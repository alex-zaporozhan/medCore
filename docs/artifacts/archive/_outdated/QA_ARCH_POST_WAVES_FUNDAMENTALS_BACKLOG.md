# QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG — фундамент после первого прохода по Waves

> **Роль:** @QA_ARCH / @LEAD (приоритизация)  
> **Когда открывать:** после закрытия **всех** рекомендуемых волн из `docs/artifacts/DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` (или раньше — только по явному решению @LEAD).  
> **Зачем:** пункты здесь **не** должны подменять DoD текущих волн; это **второй слой** — снижение долгосрочного operational/product risk там, где первый проход сознательно оставил «достаточно хорошо» или техдолг.

**Поиск в репо:** `QA_ARCH_POST_WAVES_FUNDAMENTALS` или `POST_WAVES_FUNDAMENTALS`

---

## Выполнено и зафиксировано в коде (Wave 3, 2026-03, @DEV / ревью @QA_ARCH)

> **Закрытие волны:** **@LEAD** зафиксировал закрытие Wave 3 и разрешил формулировки DoD (политика Loyalty = `ARCH_DEV_ERP_LOYALTY_011`, единый PR допустим, gate CI отдельно от DoD) — **`docs/artifacts/LEAD_DECISIONS_QA_ARCH_WAVES.md`**.

Ниже — **не** закрытие всего пост-waves фундамента, а **факт** реализации пакета **Wave 3** из `DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` (Completion / CRM / Loyalty / Family), чтобы архитектурные ссылки не расходились с репозиторием.

| Область | Суть | Где смотреть |
|--------|------|----------------|
| **G1** Блокировка завершения визита по Loyalty | Базовый тип `LoyaltyVisitCompletionBlocked`; подписка (`SubscriptionBusinessError`) и кошелёк (`WalletFamilySpendDenied`, `InsufficientWalletBalance`) не переводят визит в `completed`; задача **`LOYALTY_MISMATCH`**; в ответе — `subscription_id` при подписке | `src/application/loyalty_completion_errors.py`, `booking_completion_service.py`, `loyalty_service.py`, `wallet_service.py` |
| **G2** CRM после ERP | Фасад **`CrmAttributionSyncService`**; подписчик `BOOKING_COMPLETED` вызывает его вместо прямого lifecycle | `crm_attribution_sync_service.py`, `lead_event_handlers.py` |
| **G4** Retry ERP | `PUT .../admin/bookings/{id}/complete/retry`, метрика **`booking_completion_erp_retry_total`**, лог с `previous_erp_error_code` | `bookings.py` |
| **E7** Несколько визитов на лид | Таблица **`lead_secondary_bookings`**, **`get_lead_by_any_booking_id`**, **`attach_booking`** дополняет secondary; Kanban-фильтр по booking учитывает secondary | миграция `r4s5t6u7v8w9`, `lead_repo_impl.py`, `lead_service.py`, `lead_lifecycle_service.py` |
| **Reconcile CRM** | Celery **`crm_tasks.reconcile_lead_actual_values`**, короткая сессия на лид | `crm_tasks.py`, `celery_app.py` |
| **H6** Audit прогноза лида | **`COMPLIANCE_CRM_AUDIT_ENABLED`**, таблица **`crm_lead_estimated_value_audit`**, **`LeadService.append_estimated_value_compliance_audit`** (quantize Decimal) | `config.py`, `admin_crm.py`, `lead_service.py` |
| **I2–I4** LoyaltyGroup / группы | Таблица **`loyalty_groups`**, nullable **`family_links.group_id`**, runbook | миграция, `docs/artifacts/LOY_FAMILY_LOYALTY_GROUP_MIGRATION_RUNBOOK.md` |
| **NFR** | §**6.5** в `NONFUNCTIONAL_AUDIT_NEXT.md` — метрики completion / retry / reconcile | `docs/artifacts/NONFUNCTIONAL_AUDIT_NEXT.md` |
| **Политика ERP↔Loyalty** | §**1.2.1** атомарность фасада | `docs/artifacts/ARCH_DEV_ERP_LOYALTY_011.md` |

Документы **MIGRATION_UPGRADE.md** и **.env.example** обновлены под ревизию **`r4s5t6u7v8w9`** и флаг compliance.

### Выполнено и зафиксировано в коде (Wave 4, 2026-03, @DEV / ревью @QA_ARCH)

> Факт реализации **W4.1 / W4.2** из `DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` (AI / Omni / Tools hardening + CRM UI / семантика стадий). Формальное закрытие волны @LEAD — по внутреннему процессу при необходимости.

| Область | Суть | Где смотреть |
|--------|------|----------------|
| **W4.1** C6/C7/J2/J3 | Permissions **`booking.ai_tools.use`**, **`ai.tasks.run`** в матрице и в контекстах инструментов; адаптер слотов с лимитами (`booking_ai_tools_max_*`); orchestrator: порядок `tool_ctx` / schema, JSON-safe payloads для tool events; тесты RBAC/registry | `rbac_matrix.py`, `booking_tools_adapter.py`, `omnichannel_ai_orchestrator.py`, `tests/application/test_tools_registry_rbac.py`, `tests/services/test_ai_tools_booking.py` |
| **W4.2 D2** | Блок «Рабочий центр» (CRM / расписание / задачи), русские подписи вкладок правой колонки | `frontend/src/admin/pages/AdminOmniChatPage.tsx` |
| **W4.2 D3** | **`AiFeatureBadge`**; **`useEffectiveAiFeatureGate`** в `hooks/` (без инверсии `shared`→`hooks`); merge ключей **`/admin/ai-status.features`** с id из дефолтного набора фич | `AiFeatureBadge.tsx`, `useEffectiveAiFeatureGate.ts`, `aiFeatures.ts` |
| **W4.2 D4** | **`GET .../pipelines/{id}/stage-semantics`** — поле **`resolved_stage_semantics`** (та же логика, что проверка переходов); **`PATCH .../leads/{id}/stage`** — **`enforce_semantic_transition`**, ответ **400** с `semantic_transition_invalid`; строгий Kanban: клиент + сервер; парсинг **`ApiErrorWithCode.details`** для объекта `detail` | `admin_crm.py`, `lead_service.py` (`SemanticTransitionBlockedError`), `crm_semantics_dto.py`, `AdminSalesPipelinePage.tsx`, `useCrmLeads.ts`, `frontend/src/api/client.ts` |
| **Тесты** | Pytest: resolved semantics + enforce; Vitest: семантика на фронте; мок **`usePipelineStageSemantics`** в тесте Kanban | `tests/api/test_admin_crm.py`, `crmStageSemantics.test.ts`, `AdminSalesPipelinePage.test.tsx` |

Сводка ID в **`QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md`** (блок «Статус Wave 4»).

### Выполнено и зафиксировано в коде (Wave 5, 2026-03, @DEV / ревью @QA_ARCH)

Ниже — **не** полное закрытие пост-waves фундамента, а факт реализации пакета **Wave 5** (`DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` W5.1–W5.2, ID **A1, A8, A9, A3, A4, A21** в части, допустимой DoD).

| Область | Суть | Где смотреть |
|--------|------|----------------|
| **A1** Read replica (optional) | Отдельный DSN `DATABASE_REPLICA_URL`, пул `get_reporting_session` | `src/infrastructure/database/base.py` |
| **A8** statement_timeout | `DB_REPORTING_STATEMENT_TIMEOUT_MS`, `SET LOCAL` на reporting-сессии | `get_db_reporting`, `src/core/config.py` |
| **A9** Redis дашбордов | JSON read-through для `GET .../dashboard`, `.../owner-dashboard`; инвалидация после commit refresh | `src/application/services/erp_report_cache.py`, BackgroundTasks в `admin_reports.py` |
| **Метрики кэша / реплики** | `erp_dashboard_cache_*`, `db_replica_lag_observed_seconds` | `src/core/metrics.py` |
| **Probe лага** | `GET /health/replica`, `DB_REPLICA_LAG_WARN_SECONDS` | `src/main.py` |
| **A3** Индексы | Миграция **`w5perf1idx_fin`**; шаблоны EXPLAIN | `alembic/versions/w5perf1idx_fin_*.py`, **`WAVE5_A3_EXPLAIN_QUERIES.sql`** |
| **A4 / A21** k6 | Optional workflow, smoke + опционально dashboard при токене | **`load-tests-k6-optional.yml`**, **`k6_wave5_smoke.js`** |
| **OPS / NFR** | Runbook, §5.3 NFR | **`WAVE5_OPS_RUNBOOK.md`**, **`NONFUNCTIONAL_AUDIT_NEXT.md`** §5.3 |

Сводка ID в сводке бэклога: **`QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md`** (блок «Статус Wave 5»).

### Выполнено и зафиксировано в коде (Wave 7, 2026-03, @DEV / ревью @QA_ARCH)

> Факт реализации пакета **Wave 7** (`DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` W7.1–W7.4, ID BE* и SR* из сводки L/M). Формальное закрытие волны @LEAD — по внутреннему процессу при необходимости.

| Область | Суть | Где смотреть |
|--------|------|----------------|
| **BE1** | Единый словарь tool/legacy → `BookingErrorCode`; AI tools выровнены на те же строковые коды, что API | `src/application/booking_error_codes.py`, `src/application/ai/tools_booking.py`, orchestrator |
| **BE2 / BE4** | Метрика `booking_errors_total{code,clinic_bucket,source}`; запись на API и для booking-tools в Omni; алерты Prometheus; JSON-дашборд | `src/core/metrics.py`, `booking_error_observability.py`, `deploy/prometheus/dental_booking_alerts.yml`, `deploy/grafana/dashboards/dental_booking_booking_errors_w7.json` |
| **BE5** | Порог burst → Task (опционально, Redis, отдельная DB-сессия); шумные коды исключены из burst; env-флаги | `booking_error_observability.py`, `src/core/config.py`, `.env.example` |
| **BE6** | PWA: `role="alert"`, `aria-live`, строка `traceId` для поддержки | `frontend/src/app/pages/BookingWizardPage.tsx` |
| **BE7 / OpenAPI** | `BookingErrorResponse` в `responses` booking/payment; complete/retry → структурированный `detail` | `bookings.py`, `payments.py`, `application/errors.py` (`booking_error_from_completion_result`) |
| **BE8 / audit** | Строка в журнале согласованности | `docs/artifacts/ARCH_AUDIT_NEXT.md` §4 (журнал) |
| **SR5** | Роль `manager`: `erp.owner_reports.read`, `attribution.reports.read` (код + миграция БД) | `rbac_matrix.py`, `alembic/versions/x7w8y9z0a1b2_*.py` |
| **SR8** | Вынесенная спецификация RBAC (ссылка из архивных документов; не дублировать матрицу в TASK) | репозиторий: `docs/SEC_RBAC_SPEC.md` (вне `docs/artifacts`) |
| **SR3 / SR9** | Инвентарь permission-кодов из роутеров: `docs/artifacts/sec_rbac_router_permissions.txt`; `scripts/audit_rbac_endpoints.py --check`; pytest | `tests/application/test_sec_rbac_router_permissions_inventory.py`, `tests/application/test_rbac_matrix_w7.py` |
| **SR1** | Карта эндпоинтов + процесс обновления инвентаря | `docs/artifacts/SEC_RBAC_ENDPOINTS_MAP.md` |
| **QA follow-up** | `trace_id` в глобальном 500 и в теле ошибок webhook; `payment_webhook_failures_total`; NFR §6.7 | `src/main.py`, `payments.py`, `docs/artifacts/NONFUNCTIONAL_AUDIT_NEXT.md` §6.7 |

Сводка ID: **`QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md`** (блок «Статус Wave 7»).

---

## 1. Наблюдаемость (Grafana / OPS)

- Расширение дашбордов: lag/SLO-панели по `erp_aggregate_lag_seconds`, корреляционные подсказки (ссылки на log queries), **folders** и именование под окружения (`staging` / `prod`).
- **Переносимость ≠ упрощение:** импорт усиливается через **`__inputs`** и маппинг datasource в мастере Grafana, а не через удаление переменных и «жёсткий» uid — см. `deploy/grafana/dashboards/dental_booking_observability_w1_w2.json`.
- При мультикластере: переменные `cluster` / `namespace` (с контролем кардинальности в шаблонах запросов).

## 2. Метрики и кардинальность

- Миграция **остаточных** CRM-рядов с сырым `clinic_id` в лейблах на `clinic_bucket` (инвентаризация: `NONFUNCTIONAL_AUDIT_NEXT.md` §6.1).
- Выравнивание recording rules / alert queries с дашбордами (единая библиотека выражений или документированные отклонения).

## 3. Perf и инфраструктура (часто пересекается с Wave 5)

- **Базовый слой Wave 5 (2026-03)** уже в коде: optional replica, reporting timeout, Redis для двух дашбордов, миграция индексов, k6 optional, probe лага — см. таблицу «Выполнено Wave 5» выше. Ниже — **углубление** (топология Redis-кластера, политика пулов при двух DSN, формальный perf-budget на staging).
- ADR-расширения: Redis topology при росте, индексы под **новые** профили нагрузки после замеров; k6/Locust с порогами p95 на **staging** (не только smoke).

## 4. Продукт и корректность домена

- Всё, что в `QA_ARCH_BACKLOG_NA_POTOM_UNIFIED` помечено как отложенное **после** SEC/юридического контура (например полный roadmap Medical PD), если не вынесено в отдельный эпик.

---

## 5. Фундаментальный performance «на потом» (предложения @QA_ARCH)

Пункты **не** заменяют DoD Wave 5; пересечения с W5 отмечены. Это **второй слой** — когда инварианты домена и OBS уже стабильны, а узкое место — **масштаб**, **предсказуемость latency** и **стоимость** БД/воркеров.

1. **SLO и recording rules для цепочки завершения визита** — SLI по `booking_completion_duration_seconds`, доле `loyalty_blocked` vs `success`, ошибкам ERP; multi-window burn rate (см. `NONFUNCTIONAL_AUDIT_NEXT.md` §6.4) — без этого пороги «по ощущениям».
2. **Индексы и план под нагрузкой** — `EXPLAIN` + миграции для горячих путей: `lead_secondary_bookings` (lead_id, booking_id, clinic_id), join с `lead_cards` при росте списков; сверка с `sum_income_revenue_for_crm_lead` (см. также единый SQL/view в `QA_ARCH_BACKLOG` A24).
3. **Read path CRM↔ERP (расширение за Wave 5)** — при росте объёма: кэш read-through по **lead** / тяжёлым CRM GET (не только два дашборда), ключи `clinic_id + период + lead`, согласование с `ErpReportsRepository`; не смешивать с записью визита. *(Wave 5 закрыл базовый кэш дашбордов владельца.)*
4. **Read replica / reporting (углубление)** — маршрутизация **всех** тяжёлых CRM read-only путей при необходимости; отдельная **роль** PostgreSQL `reporting` + server-side defaults; пул/лимиты при двух DSN. *(Wave 5: optional replica для admin report GET + app-level timeout.)*
5. **Нагрузочный профиль complete_visit и цепочка CRM** — k6/Locust: параллельные `complete` по клинике, очереди Celery, длина транзакций; **отдельно** — Kanban cursor под нагрузкой, Omni AI budget; fan-out `BookingCompleted`. *(Wave 5: smoke k6 + опционально один отчётный GET.)*
6. **Reconcile CRM** — при росте числа лидов: шардирование по `clinic_id`, rate limit воркера, метрика `crm_reconcile_duration_seconds` и алерт на backlog; опционально — advisory lock per clinic.
7. **Кардинальность Prometheus** — периодический аудит новых серий (`booking_completion_erp_retry_total`, `loyalty_blocked`); при мультикластере — согласование `cluster`/`namespace` с §1 выше.
8. **Дашборды Grafana под Wave 5** — панели по `erp_dashboard_cache_requests_total`, `erp_dashboard_cache_invalidations_total`, `db_replica_lag_observed_seconds`; алерт при росте `result=error` или при `lag_warning` из внешнего probe `/health/replica`.
9. **Миграция лейблов `erp_reports_requests_total`** — замена сырого `clinic_id` на `clinic_bucket` / снижение кардинальности (см. `prometheus_labels.py`, `NONFUNCTIONAL_AUDIT_NEXT` §6).
10. **Redis invalidation при очень большом числе ключей** — замена `SCAN`+`DEL` на версионирование namespace ключа или индекс ключей на клинику (SET), если инвалидация станет горячей точкой.
11. **Пулы соединений при dual-engine** — метрики ожидания/исчерпания пула для primary vs reporting; алерт при `pool_timeout` на reporting при массовых отчётах.
12. **Формальный perf-budget на staging** — зафиксированные пороги p95/p99 (k6 thresholds) для набора API (отчёты, Kanban, complete), а не только smoke `/health`; гейт по политике release (см. `WAVE5_OPS_RUNBOOK.md`).
13. **`GET .../stage-semantics` на больших воронках** — сейчас на каждое открытие Kanban: N вызовов `get_semantic_for_stage` на бэкенде; при росте числа стадий — батч-резолв в одном SQL, материализованный снимок per pipeline или сильный HTTP-кэш (ETag / `Cache-Control`) + согласованная инвалидация при смене маппинга.
14. **Дублирующие запросы Omni UI** — `admin-ai-status` и `available-tools` дедуплицируются React Query, но при росте экранов — рассмотреть один агрегированный **`GET /admin/omni/ui-bootstrap`** (флаги + tools) для снижения RTT и водопадов на медленных сетях.
15. **Kanban cursor + строгая семантика** — под нагрузкой: p95 для `crm-leads-kanban` × число колонок; при узком месте — server-side prefetch семантик в ответе списка стадий или сжатие числа round-trips (см. также пункт 13).
16. **Метрики строгого CRM** — счётчик **`crm_semantic_transition_blocked_total`** с разрезом `initiator=client_precheck|server_enforce` (и опционально `result=blocked|bypassed_no_mapping`) для отличия UX-блока от API-400 и анализа обходов клиента.
17. **Приоритет `ai_mode` vs `features` в merge** — при расширении ответа **`/admin/ai-status`** ключами `omni.*` зафиксировать в ADR/NFR порядок слияния (сейчас: глобальный режим + затем перекрытие по `features` для известных id), чтобы не было «дрейфа» статусов Spotlight между окружениями.
18. **`booking_errors_total` при очень высоком RPS** — при росте кардинальности или cost scrape: recording rules (агрегация по `code` без `clinic_bucket` в отдельном ряду), либо документированный sampling; детализация по клинике остаётся в структурных логах.
19. **Hot path ошибок оплаты** — при профилировании: избегать лишнего `session.get(Booking)` в except, если `clinic_id` можно вернуть из `PaymentService` в одном проходе с бизнес-логикой.
20. **Webhook внешнего провайдера (YooKassa)** — долгая обработка в HTTP: очередь (Celery) + idempotency по идентификатору платежа; метрика `payment_webhook_failures_total` как сигнал, не единственный контур.
21. **BE5 burst → Task** — при нескольких репликах API Redis-ключи общие; при латентности Redis между AZ — ослабить синхронную запись Task в пользу алертов по метрике или отложенного воркера.
22. **Структурированные ошибки complete/retry** — дополнительная сериализация только на failure path; при замере — кэшировать редко меняющиеся шаблоны ответов (микро-оптимизация).
23. **Скрипт инвентаря RBAC (`audit_rbac_endpoints.py`)** — при раздувании роутеров заменить regex на AST-парсинг для устойчивости к форматированию (отдельный инкремент).

---

## Связанные артефакты

- `docs/artifacts/LEAD_DECISIONS_QA_ARCH_WAVES.md` — закрытие волн и разрешения по DoD (@LEAD)  
- `docs/artifacts/DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` §0.1 — философия «укрепление ≠ упрощение»; таблицы **Wave 4 / Wave 5** — факт реализации в коде  
- `docs/artifacts/QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md` — блоки «Статус Wave 4 / Wave 5 / Wave 7»  
- `docs/artifacts/NONFUNCTIONAL_AUDIT_NEXT.md` (в т.ч. §6.5–§6.6)  
- `docs/ARCHITECTURE_EXCELLENCE_PASSPORT.md` §16

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-03-21 | Первая версия: пост-waves фундамент + Grafana (переносимость vs упрощение). |
| 2026-03-21 | Таблица «Выполнено Wave 3» + §5 предложения по фундаментальному perf «на потом». |
| 2026-03-21 | Ссылка на **`LEAD_DECISIONS_QA_ARCH_WAVES.md`** (закрытие Wave 3 @LEAD). |
| 2026-03-21 | Таблица **«Выполнено Wave 5»** (perf/инфра); §3 уточнён; §5 дополнен пунктами 8–12 (фундаментальный perf «на потом»). |
| 2026-03-21 | Таблица **«Выполнено Wave 4»** (AI/Omni/tools + CRM семантика Kanban); §5 дополнен пунктами 13–17 (perf «на потом»: stage-semantics, Omni bootstrap, Kanban+семантика, метрики strict CRM, merge AI flags). |
| 2026-03-21 | Таблица **«Выполнено Wave 7»** (BKG_ERRORS / SEC RBAC: метрики, OpenAPI, completion/webhook/trace, инвентарь permissions, миграция manager); §5 дополнен пунктами **18–23** (perf «на потом» вокруг ошибок записи/оплаты, webhook, BE5, RBAC-скрипт). |
