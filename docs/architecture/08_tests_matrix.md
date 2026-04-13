# Матрица тестов

## Назначение

Обзор того, что в репозитории проверяется автоматически; якоря — каталоги и примеры файлов.

## Как это работает (что реально гоняет CI и разработчик)

1. **Pytest:** тесты лежат под `tests/`; `tests/conftest.py` выставляет тестовое окружение до импорта `src`, подключается к БД из `DATABASE_URL_TEST` или производной от `DATABASE_URL` с суффиксом `dental_booking_test`, при необходимости пропускает тесты если БД недоступна, гоняет `alembic upgrade head` через фикстуру инициализации схемы (детали и предупреждения — в шапке `conftest.py`).
1b. **Активный workflow Phase 1c (SaaS entitlements):** [`.github/workflows/build-and-test-entitlements.yml`](../../.github/workflows/build-and-test-entitlements.yml) — сервисы Postgres + Redis, `npm run build` во `frontend`, скрипт `scripts/check_admin_entitlement_routers.py`, узкий набор pytest (entitlements, session, box-cuts, tasks rbac, platform internal). **Бэклог QA_ARCH:** по мере готовности CI расширить на полный `pytest tests/` — см. [arch_plan/04_PHASE_1C_ENTITLEMENTS.md](./arch_plan/04_PHASE_1C_ENTITLEMENTS.md) (раздел «Бэклог после merge 1c», пункт B3), трекинг [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) **1c-Q3**, фаза [07_PHASE_2_RELIABILITY.md](./arch_plan/07_PHASE_2_RELIABILITY.md).
2. **Слои проверок:** `tests/api/` бьёт в приложение через `httpx.AsyncClient` к `app` из `main` — это интеграционные тесты маршрутов с реальной (тестовой) БД. `tests/services/` вызывают сервисы напрямую с фейковыми или реальными репозиториями. `tests/application/` фиксирует матрицы RBAC и контракты ошибок без полного HTTP.
3. **Фронт (Jest/Vitest):** тесты в `frontend/src/__tests__/` и рядом с страницами гоняются через скрипт test из `frontend/package.json`; они не поднимают backend по умолчанию.
4. **E2E Python:** `tests/e2e/` прогоняет длинные сценарии (бронь, деньги, workstation) при наличии окружения; требуют поднятых сервисов или маркеров pytest.
5. **Playwright:** отдельная цепочка `npm run test:e2e` и docker-сервис в compose — браузерные сценарии; CI workflow для них в репозитории отключён (`workflows_disabled`).

## Изоляция seed при SaaS-тестах (mutating `organization_id`)

Некоторые сценарии entitlements **меняют** строку seed-админа в БД (`AdminUser.organization_id`) или вставляют строки `organization_entitlements`. Без отката следующие тесты в том же процессе pytest могут увидеть «чужую» организацию и падать (RBAC, session, tasks).

**Паттерн:** в модуле, который мутирует seed, объявить **autouse**-фикстуру с `yield`, которая после теста восстанавливает `organization_id` и удаляет тестовые org/entitlements. Образец: `tests/api/test_admin_entitlement_api.py`. Не полагаться на порядок файлов в `tests/api/`.

Трекинг: [arch_plan/04_PHASE_1C_ENTITLEMENTS.md](./arch_plan/04_PHASE_1C_ENTITLEMENTS.md) B5, [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) **1c-Q5** (статус `done` при приёмке этого текста).

## Backend: pytest

- Корень: `tests/`, общая фикстура `tests/conftest.py`.
- **API:** `tests/api/` — десятки файлов по админским модулям, auth, owner omni, patient, schedule, bookings, health.
- **Сервисы:** `tests/services/` — бронирование, ERP, омниканал, AI, CRM, лояльность, формы, задачи и др.
- **Application:** `tests/application/` — RBAC-матрица, инвентарь прав роутеров, коды ошибок booking, tools registry.
- **Core:** `tests/core/` — edition, metrics path, PII, tokenization, omni SSE payload, контракт `http_exception_handler` и OpenAPI error schemas (`test_http_exception_envelope.py`, `test_openapi_error_schemas.py`), парсинг JSON Grafana (`test_grafana_dashboard_json.py`) и др. Граница сырого `HTTPException.detail` vs JSON — [TEST_HTTP_EXCEPTION_BOUNDARY.md](./TEST_HTTP_EXCEPTION_BOUNDARY.md).
- **Security:** `tests/security/` — чаты, AI agent, PD.
- **Unit:** `tests/unit/` — state machine лидов, waitlist, booking dedup, CRM AI и др.
- **E2E (Python):** `tests/e2e/` — например `test_booking_to_payment.py`, `test_money_flows.py`, `test_frontend_pages.py`, `test_kanban_workstation_flow.py`.

## Frontend

- **Глобальные инварианты:** `frontend/src/__tests__/` — `apiClientShellInvariants`, `queryKeys`, `routePaths`, `structurePhase4`, `adminNoRawMantineDrawer`.
- **Страницы админки:** `frontend/src/admin/pages/__tests__/` — выборочно (tasks, reports, sales pipeline).

## Пробелы (честно)

- Не каждая страница SPA покрыта юнит-тестом.
- Playwright: скрипт `npm run test:e2e` в `frontend/package.json`; образ и команда в `docker-compose.yml` (сервис с Playwright для e2e). Workflow в `.github/workflows_disabled/e2e.yml` — отключён; фактический прогон в CI не зафиксирован этим документом.

## Статус

- Backend API и сервисы: широкое покрытие по файлам.
- Frontend: в основном структурные и точечные тесты страниц.

## Непонятное

Точный процент покрытия и отчёт coverage — только из вывода `pytest --cov` / CI.

### Enterprise-аудит (честная оценка)

- **Критические риски:** отключённый Playwright workflow и отсутствие обязательного браузерного e2e в CI — регрессии UI/интеграций могут доезжать до прода.
- **Средние риски:** тесты изоляции тенанта покрывают выборочные пути, не всю матрицу роутеров.
- **Формально / недоделано:** нет публичного порога coverage как gate в описанном в этом файле наборе CI.
- **Рекомендуемые доработки:** включить smoke e2e в CI; периодический security scan зависимостей (отдельный pipeline).

### Соответствие фактам (проверка)

- Структура `tests/`, `conftest.py`, `frontend/src/__tests__/`, `workflows_disabled` — по дереву репозитория.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** отсутствие обязательного браузерного e2e в CI — регрессии цепочек оплаты и tenant-изоляции доезжают поздно.
- **Что усилить:** тесты двойного webhook ([U-006](./UNRESOLVED_AND_CONFUSION_LOG.md)); нагрузочный профиль критичных API.
- **С нуля:** включить минимальный Playwright smoke в активном workflow.
- **БД:** нагрузочные тесты с реалистичным объёмом — отдельный pipeline.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) (§2.3, §4).
