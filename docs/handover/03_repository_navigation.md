# Карта репозитория

Краткий указатель «что где лежит» для навигации по коду и сопутствующим артефактам.

## Корень репозитория

| Путь | Назначение |
|------|------------|
| `README.md` | Быстрый старт, ссылки на основную документацию. |
| `pyproject.toml`, `poetry.lock` | Зависимости и инструменты Python; настройки pytest/ruff/black/mypy. |
| `Dockerfile` | Сборка образа backend. |
| `docker-compose.yml` | Локальный полный стек: Postgres, Redis, migrations job, backend, frontend, Celery, опционально observability-профиль. |
| `.env.example` | Полный перечень переменных окружения с пояснениями. |
| `CI_CD.md`, `AGENTS.md` | Сводка пайплайнов (Hub vs GHCR, Jenkins). |
| `CONTRIBUTING.md`, `DOCUMENTATION_POLICY.md` | Правила вклада и границы каталогов документации. |
| `Jenkinsfile` | Корпоративный pipeline (сборка, тесты по параметрам, GHCR). |
| `alembic.ini`, `alembic/versions/` | Миграции БД; архив старых ревизий — `alembic/versions/README.md`. |

## Backend (`src/`)

| Путь | Назначение |
|------|------------|
| `src/main.py` | FastAPI-приложение, lifespan, CORS, обработчики ошибок, `/metrics`, `/health`. |
| `src/core/config.py` | Pydantic Settings: все переменные окружения приложения. |
| `src/core/security.py`, `src/core/metrics.py`, `src/core/logging.py` | JWT, метрики, логирование. |
| `src/api/v1/router.py` | Сборка API v1. |
| `src/api/v1/routers/` | Порядка **95** файлов модулей маршрутов (admin / patient / public / platform / owner). |
| `src/api/v1/dependencies.py` | Инъекции сессии БД, контекст запроса, `require_permissions`, rate limit. |
| `src/application/services/` | Бизнес-логика по доменам. |
| `src/application/dto/` | Схемы передачи данных между слоями. |
| `src/application/events/` | EventBus и регистрация обработчиков по подсистемам. |
| `src/application/rbac_matrix.py` | Канон матрицы RBAC. |
| `src/domain/entities/` | SQLAlchemy-модели. |
| `src/domain/interfaces/repositories/` | Протоколы репозиториев. |
| `src/infrastructure/database/` | Реализации репозиториев, сессии, RBAC-репозиторий. |
| `src/infrastructure/messaging/` | Celery app, задачи в `tasks/`. |
| `src/infrastructure/external_apis/` | Клиенты внешних API (в т.ч. YooKassa). |
| `src/infrastructure/storage/` | S3-совместимое хранилище, пресайны. |
| `src/scripts/` | Утилиты сидирования, one-off, операционные скрипты. |

## Frontend (`frontend/`)

| Путь | Назначение |
|------|------------|
| `package.json`, `package-lock.json` | Зависимости и скрипты сборки/тестов. |
| `vite.config.ts` | Vite, PWA, прокси на API. |
| `src/App.tsx`, `src/routes/` | Корень SPA и маршруты. |
| `src/api/` | HTTP-клиент и обвязка запросов. |
| `src/hooks/` | Хуки доменной логики UI. |

## Тесты (`tests/`)

| Путь | Назначение |
|------|------------|
| `tests/conftest.py` | Фикстуры БД, Redis, клиенты, политика имён тестовой БД. |
| `tests/api/` | Интеграционные тесты HTTP API. |
| `tests/application/`, `tests/services/` | Сервисный уровень и доменные сценарии. |
| `tests/e2e/` | Playwright из pytest; для CI часто нужен `FRONTEND_E2E_URL` и скрипт `scripts/ci/run_pytest_with_e2e_preview.sh`. |

Маркеры pytest перечислены в `pyproject.toml` (`critical_path`, `redis_integration`, и т.д.).

## Скрипты и автоматизация (`scripts/`)

| Путь | Назначение |
|------|------------|
| `scripts/ci/` | Обёртки для GitHub Actions (pytest + vite preview, junit-gate и т.д.). |
| `scripts/docker_hub_release.ps1`, `.sh` | Локальная сборка и push в Docker Hub. |
| `scripts/audit_rbac_endpoints.py` | Сверка RBAC в роутерах со снимком в `documentation/`. |
| `scripts/dev/` | Локальные gate и вспомогательные проверки. |

## Деплой и наблюдаемость

| Путь | Назначение |
|------|------------|
| `deploy/prometheus/` | `dental_booking_alerts.yml`, записи для Prometheus. |
| `deploy/grafana/` | Дашборды и provisioning datasource. |

## Документация

| Каталог | Назначение |
|---------|------------|
| `docs/` | Внутренняя инженерная документация, ADR, product state, архитектурные обзоры. |
| `docs/handover/` | Этот пакет передачи. |
| `documentation/` | Материалы для разработчиков/интеграторов вне глубокого дерева `docs/product_state` (DEVELOPMENT, VPS, USER_DOCS по наличию). |

## Где искать конкретный сценарий

1. **HTTP-контракт** — файл роутера в `src/api/v1/routers/`, затем вызываемый сервис в `src/application/services/`.
2. **Правило доступа** — `require_permissions` в роутере + код в `rbac_matrix.py` + при необходимости миграции в `alembic/versions/`.
3. **Схема БД** — сущность в `src/domain/entities/`, миграция в `alembic/versions/`.
4. **Фоновая задача** — `src/infrastructure/messaging/celery_app.py` (`include`, `beat_schedule`), реализация в `src/infrastructure/messaging/tasks/`.
5. **Поведение в production** — `src/core/config.py` (валидаторы `_apply_production_*`), проверки в `src/main.py` lifespan.
