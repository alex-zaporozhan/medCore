# Dental Booking — обзор продукта

**Dental Booking** — веб-платформа для стоматологической клиники: онлайн-запись, операционная админка для персонала и PWA для пациентов, на одном репозитории с REST API.

## Что внутри (проверено кодом)

- **Backend:** Python 3.11, FastAPI, PostgreSQL, Redis, Celery (`pyproject.toml`, `docker-compose.yml`).
- **Frontend:** React, TypeScript, Vite (`frontend/`).
- **Зоны UI:** маркетинг `/`, админка `/admin/*`, приложение пациента `/app/*` (`frontend/src/routePaths.ts`).
- **API:** REST под префиксом по умолчанию `/api/v1` (`src/core/config.py`, `src/main.py`).

## Куда копать дальше

| Документ | Зачем |
|----------|--------|
| [PRODUCT_KNOWLEDGE_BASE.md](./PRODUCT_KNOWLEDGE_BASE.md) | Полный канон для AI и поддержки |
| [SALES_PITCH.md](./SALES_PITCH.md) | Короткий питч для B2B |
| [PROJECT_REPOSITORY_LAYOUT.md](./PROJECT_REPOSITORY_LAYOUT.md) | Дерево каталогов |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Запуск и тестовая БД |
| [UI_THEME.md](./UI_THEME.md) | Тема Mantine, токены, AdminDrawer |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | `/health`, `/metrics`, Prometheus/Grafana в репо |
| [E2E_TESTING.md](./E2E_TESTING.md) | Playwright |
| [API_V1_ROUTER_MANIFEST.md](./API_V1_ROUTER_MANIFEST.md) | Роутеры REST v1 (порядок как в коде) |
| [LEAD_DOC_AUDIT.md](./LEAD_DOC_AUDIT.md) | Аудит полноты документации |
| [USER_DOCS/INDEX.md](./USER_DOCS/INDEX.md) | Пользовательские гайды |
