# Карта репозитория

> **Версия:** 2026-04-03

## Корень

| Путь | Назначение |
|------|------------|
| `src/` | Backend FastAPI |
| `frontend/` | Vite + React + TypeScript |
| `alembic/` | Миграции БД |
| `tests/` | Pytest |
| `scripts/` | Утилиты (tenant audit, RBAC, pre-push) |
| `deploy/` | Prometheus, Grafana JSON |
| `documentation/` | Публичная документация |
| `docker-compose.yml` | Postgres, Redis, API, Celery, beat, frontend |
| `pyproject.toml` | Poetry, зависимости |

## Backend

| Путь | Назначение |
|------|------------|
| `src/main.py` | FastAPI app, middleware, health, metrics |
| `src/api/v1/router.py` | Сборка роутеров |
| `src/api/v1/routers/` | HTTP-эндпоинты по доменам |
| `src/application/` | Сервисы, события |
| `src/domain/` | Сущности |
| `src/infrastructure/` | БД, Redis, Celery tasks, storage |
| `src/core/` | config, logging, metrics, security |

## Frontend

| Путь | Назначение |
|------|------------|
| `frontend/src/routePaths.ts` | Канон URL |
| `frontend/src/App.tsx` | Маршруты |
| `frontend/src/admin/` | Админка |
| `frontend/e2e/` | Playwright |

## Очереди

`src.infrastructure.messaging.celery_app`, задачи в `src/infrastructure/messaging/tasks/`.

Reference: `documentation/PRODUCT_KNOWLEDGE_BASE.md`
