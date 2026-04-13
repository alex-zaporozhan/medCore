# Архитектура и соответствие критериям Enterprise SaaS — генеральный обзор

> **Версия:** 2026-04-09 (§1c: актуализация строки webhook B; ссылка на блок §25–§30 мастер-плана) · 2026-04-03  
> **Назначение:** единая точка входа для обзора архитектуры репозитория и выводов по зрелости SaaS. Содержание агрегирует модульные файлы каталога `docs/architecture/`; детали и повторяющиеся Enterprise-секции по слоям остаются в исходных `.md` для сопровождения.  
> **Краткая сводка продукта и схема:** [../product_state/ARCHITECTURE_FROM_CODE.md](../product_state/ARCHITECTURE_FROM_CODE.md).  
> **Фундаментальный обзор логики и БД:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md).  
> **Приёмка LEAD и перечень пробелов:** [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).  
> **Целевая платформа (эталон):** [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md).  
> **ADR:** [../adr/README.md](../adr/README.md).  
> **Мастер-план SaaS (фазы, модули, vertical, §25–§30):** [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) · навигация и якоря — [INDEX.md](./INDEX.md) (шапка). Ревью QA_ARCH цикл 4: [./SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md#qa-arch-saas-master-sec9).

---

## Оглавление

1. [Итоги для руководства и архитектора](#1-итоги-для-руководства-и-архитектора)
1a. [Фундаментальный обзор логики и БД (PRINCIPLE)](#1a-фундаментальный-обзор-логики-и-бд-principle)
1b. [Приёмка LEAD (операционный вердикт)](#1b-приёмка-lead-операционный-вердикт)
1c. [Целевое vs текущее (platform, BCP, импорт)](#1c-целевое-vs-текущее-platform-bcp-импорт)
2. [Сводная оценка по осям SaaS (0–2)](#2-сводная-оценка-по-осям-saas-0–2)
3. [Системный контур и рантайм](#3-системный-контур-и-рантайм)
4. [Backend: слои и логика](#4-backend-слои-и-логика)
5. [Frontend: зоны SPA](#5-frontend-зоны-spa)
6. [Данные, миграции, мультитенантность](#6-данные-миграции-мультитенантность)
7. [Кэш, Redis, Celery](#7-кэш-redis-celery)
8. [Метрики и наблюдаемость](#8-метрики-и-наблюдаемость)
9. [Тесты](#9-тесты)
10. [Пример сквозного домена: booking и события](#10-пример-сквозного-домена-booking-и-события)
11. [Соглашения и трассируемость документации](#11-соглашения-и-трассируемость-документации)
12. [Журнал неясностей (UNRESOLVED)](#12-журнал-неясностей-unresolved)
13. [Карта исходных документов (18 + вспомогательные)](#13-карта-исходных-документов-18--вспомогательные)

---

## 1. Итоги для руководства и архитектора

**Что это за система (по коду):** монолитный backend на **FastAPI** с единым `api_router`, бизнес-логика в **`src/application/services/`**, данные в **PostgreSQL** (async SQLAlchemy), кэш и брокер очередей — **Redis**, фоновые задачи — **Celery**, фронт — **React SPA** с TanStack Query. События между модулями в рамках процесса API — **in-process EventBus**; межпроцессная асинхронность — **Celery**.

**Критические выводы для позиционирования как «многоарендаторный Enterprise SaaS»:**

- **Нет контура «оператор платформы» (vendor / platform tenant)** и **self-service онбординга нового бизнес-клиента** с изоляцией «все клиенты платформы vs один клиент». Есть **`Organization`** и связь **`Clinic.organization_id`**, но основная изоляция данных в коде завязана на **`clinic_id`**.
- Префикс API **`/owner/`** (`owner_omni_*`) **не** означает отдельный тип JWT: используется **`get_current_admin`**, область — **`current_admin.clinic_id`**. Риск путаницы для интеграций и аудита.
- **Горизонтальное масштабирование API** при использовании только in-process EventBus требует отдельной стратегии (outbox, брокер, идемпотентность обработчиков).
- **Границы транзакций:** HTTP-запрос коммитит сессию до того, как обработчики доменных событий завершат работу в **отдельных** транзакциях — возможны частично применённые цепочки (см. §1a).

**Что сделано хорошо с точки зрения инженерии:** широкая поверхность API с RBAC, метрики и алерты как код, реплика для отчётов, структурированные ошибки и `trace_id`, значимый объём pytest по API и сервисам.

Подробная рубрика осей и шкала **0 / 1 / 2:** [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md).

---

## 1a. Фундаментальный обзор логики и БД (PRINCIPLE)

Краткое резюме (полный разбор с якорями в `src/`): **[FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md)**.

- **События:** `EventBus` in-process; подписчики часто открывают новый `AsyncSessionLocal` — атомарность «запрос + все реакции» **не** гарантируется.
- **Платежи:** уникальность `(provider, provider_payment_id)` на таблице `payments`; webhook обновляет запись и при успехе переводит бронь из ограниченного набора статусов — повторные доставки нужно осознанно считать в тестах.
- **Домен:** широкий `BookingStatus` — риск рассинхрона переходов и отчётности; изоляция тенанта без RLS — дисциплина кода и тестов.
- **С нуля:** outbox, platform-tenant, BFF/сессии, runbooks HA Redis и backup — перечислены в фундаментальном документе.

В каждом модульном файле `docs/architecture/**/*.md` добавлена секция **Углубление (PRINCIPLE)** с фокусом на свой слой.

---

## 1b. Приёмка LEAD (операционный вердикт)

Документ **[LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md)** фиксирует приёмку техлида: методология (что прочитано vs grep), **вердикт** «продукт vs Enterprise SaaS», критические находки с якорями в `src/`, таблицу **документация ↔ код**, оценку по **осям 1–14** рубрики и **бэклог P0–P2**. Красные флаги для слова «Enterprise» — в [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md). При противоречии между модульными файлами и LEAD-документом до синхронизации приоритет у LEAD (см. [CONVENTIONS_AND_TRACEABILITY.md](./CONVENTIONS_AND_TRACEABILITY.md)).

---

## 1c. Целевое vs текущее (platform, BCP, импорт)

| Тема | Текущее (код/репо) | Целевое (документы) |
|------|--------------------|----------------------|
| Platform super-admin, self-service бизнеса | Нет контура (U-004) | [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md), ADR-007 |
| Backup / DR / drill | Compose volume; runbook добавлен документально | [09_backup_restore_bcp.md](./09_backup_restore_bcp.md), ADR-008, [DR_RUNBOOK.md](../operations/DR_RUNBOOK.md), U-009 |
| Надёжные события при N репликах API | In-process bus | ADR-009, U-007 |
| Импорт 1С / Битрикс | Не заявлен | ADR-010, [modules/data_migration_import_connectors.md](./modules/data_migration_import_connectors.md), U-010 |
| Webhook подписки платформы vs пациентские платежи | **Частично:** контур **B** (отдельный путь, секрет, таблицы, happy path + идемпотентность) — **MVP spine**; **не** полный продукт (OpenAPI B, ветки, retry/reconcile, rate limit) — см. мастер-план **§2d**, **§16.6**, [ADR-011](../adr/ADR-011-platform-subscription-webhook-provisioning.md) | ADR-011, [modules/platform_subscription_billing.md](./modules/platform_subscription_billing.md), U-006; аудит A vs B: [../artifacts/WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md](../artifacts/WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md) |
| **§17.1** мультиреплика API + публичный B / signup | Зафиксирован **interim** (singleton приём до outbox) — см. операции | [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md), [RELEASE_CHECKLIST.md](../operations/RELEASE_CHECKLIST.md), ADR-009 |
| Скан пробелов QA_ARCH | — | [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) |

---

## 2. Сводная оценка по осям SaaS (0–2)

Оси **1–14** и чек-листы: [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md). Ниже — краткая сводка по репозиторию; детальное обоснование — в [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md). Оценка **субъективная по репозиторию**, без претензии на сертификацию.

| Ось | Уровень | Комментарий |
|-----|---------|-------------|
| Идентичность и границы тенанта | **1** | Сильная опора на `clinic_id`; `Organization` есть; platform-tenant и self-service провижининг отсутствуют. |
| Жизненный цикл клиента SaaS | **0–1** | Нет выделенного продукта «регистрация нового арендатора» в коде как у классического SaaS. |
| Безопасность и соответствие | **1** | JWT, RBAC, rate limits, PII-настройки; токены SPA в `localStorage` — типичный enterprise-риск XSS. |
| Надёжность | **1** | Health/replica, webhooks с метриками; явные SLO в репо не зафиксированы; EventBus не распределённый. |
| Наблюдаемость | **1** | `/metrics`, middleware latency, алерты YAML; полнота прод-стека Prometheus/Grafana/on-call вне репозитория. |
| Операции | **1** | Alembic, compose; runbooks restore/HA Redis не в этом каталоге. |
| Коммерция и биллинг | **0** | Не выведено как зрелый слой в архитектурных документах репозитория. |
| Поставка и цепочка (CI/CD) | **0–1** | Активен в основном markdown-links workflow; backend/frontend/e2e/security в `workflows_disabled` — U-008. |
| Модель угроз фронта | **1** | Токены в `localStorage` (`frontend/src/api/client.ts`); CSP/httpOnly — не как обязательная политика в репо. |
| Управление изменениями API | **1** | Префикс `/api/v1`; явного deprecation-процесса не выделено. |
| Непрерывность бизнеса (BCP) | **0** | Runbooks restore/DR в репо не зафиксированы; drill-workflow отключён. |

*Ось 12 (отрасль / медицина): не сводится к одной цифре без юридического контура — см. рубрику.*

---

## 3. Системный контур и рантайм

**Якоря:** `src/main.py`, `src/api/v1/router.py`, `docker-compose.yml`, `frontend/src/api/client.ts`.

- **Lifespan:** регистрация обработчиков EventBus (lead, erp, loyalty, tasks, marketing); при shutdown — `close_redis()`.
- **Middleware:** CORS; `X-Trace-Id` в `request.state` и ответе; Prometheus latency для путей кроме `/metrics`, `/health`, `/health/replica`.
- **Ошибки:** глобальный 500 с `trace_id`; `HTTPException` → единый envelope `{detail, code, trace_id?}`; 422 с безопасным `errors`.
- **Маршруты:** `api_router` с `settings.api_v1_prefix`; дублирующий mount на `/api/v1` при отличии префикса. Корневые: `/health`, `/health/s3`, `/health/replica`, `/metrics`.
- **Compose (локально):** Postgres, Redis, migrations job, backend, celery, celery-beat, frontend; e2e profile с Playwright.
- **SPA:** базовый HTTP-префикс `/api`, Bearer из `localStorage`.

*Детализация и mermaid:* [00_system_runtime.md](./00_system_runtime.md).

---

## 4. Backend: слои и логика

### 4.1 API (`src/api/v1/`)

- Сборка роутеров в `router.py`; десятки модулей в `routers/`.
- Паттерн: `Depends(get_session)`, `get_current_admin` / `get_current_patient`, `require_permissions`, `get_request_context` + RBAC из `RbacServiceImpl`.
- **`/owner/*` (omni):** фактически админ текущей клиники, не отдельная роль — `owner_omni_channels.py`.
- Edition: `require_crm_enterprise_edition` для части CRM.

*Детали:* [backend/api_layer.md](./backend/api_layer.md).

### 4.2 Application (`src/application/services/`, `dto/`, `events/`)

- Оркестрация, репозитории и/или прямой SQLAlchemy на сессии запроса.
- События: `get_event_bus().publish(...)`; обработчики открывают **собственные** сессии БД — цепочки транзакционно не атомарны end-to-end.

*Детали:* [backend/application_layer.md](./backend/application_layer.md).

### 4.3 Domain (`src/domain/entities/`, interfaces)

- SQLAlchemy-модели; Alembic тянет все модули `entities` через `pkgutil` в `alembic/env.py`.
- Изоляция: в основном **`clinic_id`**; пациентский контекст без `clinic_id` в `RequestContext` — привязка через сущность `Patient`.

*Детали:* [backend/domain_layer.md](./backend/domain_layer.md).

### 4.4 Infrastructure

- `get_db` / `get_db_reporting`: commit при успехе, rollback при ошибке.
- **16** файлов `*_repo_impl.py` в `src/infrastructure/database/`.
- Celery tasks: отдельный event loop (`_run_async` и аналоги), свои сессии.
- S3-совместимое хранилище для медфайлов.

*Детали:* [backend/infrastructure_layer.md](./backend/infrastructure_layer.md).

### 4.5 Core

- `Settings` из env; `metrics.py` с no-op без `prometheus_client`; `edition.py`; security/tokenization/sanitizer.

*Детали:* [backend/core_crosscutting.md](./backend/core_crosscutting.md).

---

## 5. Frontend: зоны SPA

| Зона | Якоря | Суть |
|------|--------|------|
| Маршруты и shell | `frontend/src/App.tsx`, `routePaths.ts`, `AdminAuthGuard`, `PatientAuthProvider`, `edition.ts` | `/`, `/admin/*`, `/app/*`; Box скрывает часть сегментов. |
| API и состояние | `frontend/src/api/client.ts`, `queryKeys.ts`, `main.tsx` | `/api`, Bearer, TanStack Query. |
| Админка | `admin/pages/`, `hooks/` | Страницы и доменные хуки. |
| Пациент | `app/pages/`, контекст auth | Те же транспортные правила; 401-политика для patient session. |
| Shared / PWA | `shared/`, `pwa/` | Error boundary, опциональный SW. |

*Детали по файлам:* [frontend/routing_and_shells.md](./frontend/routing_and_shells.md), [api_state.md](./frontend/api_state.md), [admin_domain.md](./frontend/admin_domain.md), [app_patient_domain.md](./frontend/app_patient_domain.md), [shared_ui_and_pwa.md](./frontend/shared_ui_and_pwa.md).

---

## 6. Данные, миграции, мультитенантность

- **Alembic:** `alembic/env.py`, `Base.metadata`, async URL из `settings`.
- **Мультитенантность:** клиника как основной столбец изоляции; `Organization` — группировка клиник без platform-слоя в модели.
- **Реплика отчётов:** `get_reporting_session`, `DATABASE_REPLICA_URL`.

*Детали:* [05_data_migrations_multitenancy.md](./05_data_migrations_multitenancy.md).

---

## 7. Кэш, Redis, Celery

- Приложение: `REDIS_URL` (часто db 0), `get_redis()`.
- Celery: отдельные Redis DB для broker/result в типичном compose.
- Beat-расписание в `celery_app.py`; задачи в `src/infrastructure/messaging/tasks/`.

*Детали:* [06_cache_redis_celery.md](./06_cache_redis_celery.md).

---

## 8. Метрики и наблюдаемость

- Код: `src/core/metrics.py`, middleware в `main.py`, `GET /metrics`.
- Deploy: `deploy/prometheus/dental_booking_alerts.yml`, дашборды Grafana в `deploy/grafana/dashboards/`.
- Протокол имён: [../METRICS_PROTOCOL.md](../METRICS_PROTOCOL.md).

*Детали:* [07_metrics_observability.md](./07_metrics_observability.md).

---

## 9. Тесты

- **pytest:** `tests/api/`, `services/`, `application/`, `core/`, `e2e/`, `conftest.py` (тестовая БД, alembic upgrade).
- **Фронт:** `frontend/src/__tests__/`, частично `admin/pages/__tests__/`.
- **Playwright:** скрипты и compose есть; workflow e2e в `workflows_disabled`.

*Детали:* [08_tests_matrix.md](./08_tests_matrix.md).

---

## 10. Пример сквозного домена: booking и события

HTTP `bookings.py` → `BookingService` → `get_event_bus().publish` → подписчики в `application/events/*`, регистрация в `main.py` lifespan. Ограничение: in-process bus.

*Полная цепочка с якорями:* [domains/booking_event_chain.md](./domains/booking_event_chain.md).

---

## 11. Соглашения и трассируемость документации

Каждое утверждение о поведении — с путём к файлу в репо или пометка «не проверено». Системные пробелы SaaS не дублировать в каждом модульном файле без необходимости.

*Полный текст правил:* [CONVENTIONS_AND_TRACEABILITY.md](./CONVENTIONS_AND_TRACEABILITY.md).

---

## 12. Журнал неясностей (UNRESOLVED)

Актуальная таблица ведётся в [UNRESOLVED_AND_CONFUSION_LOG.md](./UNRESOLVED_AND_CONFUSION_LOG.md). Снимок на момент составления генерального обзора:

| ID | Вопрос | Где смотрели | Что проверить / гипотеза |
|----|--------|--------------|---------------------------|
| U-010 | Первый коннектор импорта и сущности v1? | ADR-010, `modules/data_migration_import_connectors.md` | Продукт + эпик DEV. |
| U-009 | Retention, PITR, drill для выбранного окружения? | ADR-008, `DR_RUNBOOK.md` | OPS заполняет факты; до этого BCP=0. |
| U-008 | Гарантирует ли репозиторий CI без внешнего процесса? (`workflows_disabled`) | `.github/workflows/`, `workflows_disabled/` | Включить пайплайны или задокументировать внешний CI. |
| U-006 | Достаточна ли идемпотентность `handle_webhook` при повторных уведомлениях YooKassa? | `payment_service.py` | Тесты двойного webhook; расширение веток — guard по состоянию. |
| U-007 | Нужна ли outbox вместо только in-process EventBus при масштабировании API? | `event_bus.py`, `application/events/*` | ADR: схема outbox, воркер, дедуп. |
| U-004 | Как без поломки изоляции по `clinic_id` ввести platform-operator и self-service регистрацию нового бизнеса с root-tenant? | `Organization`, `AdminUser`, JWT | ADR: сущность/claim, RLS или policy, отдельный shell. |
| U-005 | Переименовать `/owner/*` или ввести отдельный dependency для сетевого владельца? | `owner_omni_channels.py` | Сверить с продуктом; multi-clinic admin vs omni scope. |
| U-001 | Утечка `error` в `GET /health/replica`? | `src/main.py` | Prod-маскирование. |
| U-002 | Полнота repo vs прямой доступ из сервисов? | `infrastructure/database` | grep `AsyncSession` в services. |
| U-003 | Все ли Celery-задачи реально ставятся в очередь? | `tasks/` | `.delay` / `apply_async` по `src/`. |

---

## 13. Карта исходных документов (18 + вспомогательные)

Модульные файлы, из которых собран этот обзор (для углублённого чтения и секций **Enterprise-аудит** по слоям):

| № | Файл |
|---|------|
| 1 | [INDEX.md](./INDEX.md) |
| 2 | [CONVENTIONS_AND_TRACEABILITY.md](./CONVENTIONS_AND_TRACEABILITY.md) |
| 3 | [UNRESOLVED_AND_CONFUSION_LOG.md](./UNRESOLVED_AND_CONFUSION_LOG.md) |
| 4 | [00_system_runtime.md](./00_system_runtime.md) |
| 5 | [backend/api_layer.md](./backend/api_layer.md) |
| 6 | [backend/application_layer.md](./backend/application_layer.md) |
| 7 | [backend/domain_layer.md](./backend/domain_layer.md) |
| 8 | [backend/infrastructure_layer.md](./backend/infrastructure_layer.md) |
| 9 | [backend/core_crosscutting.md](./backend/core_crosscutting.md) |
| 10 | [frontend/routing_and_shells.md](./frontend/routing_and_shells.md) |
| 11 | [frontend/api_state.md](./frontend/api_state.md) |
| 12 | [frontend/admin_domain.md](./frontend/admin_domain.md) |
| 13 | [frontend/app_patient_domain.md](./frontend/app_patient_domain.md) |
| 14 | [frontend/shared_ui_and_pwa.md](./frontend/shared_ui_and_pwa.md) |
| 15 | [05_data_migrations_multitenancy.md](./05_data_migrations_multitenancy.md) |
| 16 | [06_cache_redis_celery.md](./06_cache_redis_celery.md) |
| 17 | [07_metrics_observability.md](./07_metrics_observability.md) |
| 18 | [08_tests_matrix.md](./08_tests_matrix.md) |

Дополнительно к набору из 18:

- [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md) — оси и шкала критики.
- [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) — логика, транзакции, БД, пробелы.
- [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md) — приёмка LEAD, бэклог, doc↔код.
- [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md) — эталон platform SaaS.
- [09_backup_restore_bcp.md](./09_backup_restore_bcp.md), [../operations/DR_RUNBOOK.md](../operations/DR_RUNBOOK.md) — BCP.
- [../adr/README.md](../adr/README.md) — ADR-007…011.
- [./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) — матрица рисков QA_ARCH.
- [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) — пошаговое усиление под SaaS и модули.
- [domains/booking_event_chain.md](./domains/booking_event_chain.md) — пример доменной цепочки.

---

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** сведены в §1a и в [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md); здесь только навигация.
- **Что усилить:** при изменении кода обновлять §1a, таблицу UNRESOLVED в §12 и фундаментальный документ.
- **С нуля:** не дублировать списки — см. раздел 4 фундаментального документа.
- **БД:** направления в §3 фундаментального документа; без утверждений без `EXPLAIN`.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md); приёмка и P0–P2: [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).

**Обновление:** при значимых изменениях кода или тенант-модели править сначала модульные файлы, [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md), [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md), [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md), ADR в [../adr/README.md](../adr/README.md) и рубрику, затем синхронизировать §1, §1a–§1c, §2 и §12 этого генерального обзора.
