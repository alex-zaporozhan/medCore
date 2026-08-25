# Технологический стек

Ниже перечислены компоненты, которые фактически зафиксированы в `pyproject.toml`, `frontend/package.json`, `docker-compose.yml` и связанных workflow. Версии зависимостей уточняйте по lock-файлам: `poetry.lock`, `frontend/package-lock.json`.

## Backend

- **Python** 3.11 (ограничение в Poetry: `python = "^3.11"`).
- **FastAPI**, **Starlette**, **Uvicorn** — HTTP API и ASGI-сервер.
- **SQLAlchemy 2** с **asyncpg** — асинхронный доступ к PostgreSQL.
- **Alembic** — миграции схемы (`alembic/`, `alembic.ini`).
- **Pydantic v2**, **pydantic-settings** — настройки и схемы запросов/ответов.
- **Celery 5** (брокер/бэкенд Redis) — фоновые задачи и расписание (`src/infrastructure/messaging/celery_app.py`).
- **Redis** (клиент `redis`, также `aioredis` в зависимостях) — брокер Celery, кэш отчётных JSON, rate limiting и прочие сценарии из `src/core/config.py`.
- **HTTP-клиенты:** `httpx`, `requests`.
- **Безопасность и крипто:** `cryptography`, `passlib[bcrypt]`, `PyJWT`, `pyotp`.
- **Интеграции:** `boto3` (S3-совместимое хранилище, опционально AWS Secrets Manager / KMS по настройкам), `python-telegram-bot`.
- **Наблюдаемость:** `prometheus-client` (`/metrics`, метрики в `src/core/metrics.py`).

## Данные и очереди

- **PostgreSQL 16** — основное хранилище (образ в `docker-compose.yml`). Для compose задано повышение `max_connections` (см. комментарий в YAML) — учитывать при совместном запуске API, Celery и полного pytest на одном инстансе.
- **Redis 7** — отдельные DB index в URL для приложения, брокера и result backend Celery (см. `.env.example` и compose).

## Frontend

- **React 18**, **TypeScript ~5.6**, **Vite 6**.
- **Mantine 7** — UI-компоненты и тема.
- **TanStack Query 5** — серверное состояние и кэш запросов.
- **React Router 7** (`react-router-dom`) — маршрутизация SPA (`createBrowserRouter`).
- **PWA:** `vite-plugin-pwa` + Workbox (сборка в `frontend/`).
- **Тесты:** Vitest, Playwright (`frontend/package.json`); браузерные сценарии также вызываются из Python-pytest через `pytest-playwright` (см. `tests/`, workflow в `.github/workflows/`).

## Интеграции (по коду и конфигурации)

Подключение опционально: не заданные секреты и endpoint обычно отключают соответствующий контур или переводят его в упрощённый режим (см. комментарии в `.env.example` и проверки в `src/core/config.py` / lifespan).

- **Платежи YooKassa:** клиент `src/infrastructure/external_apis/yookassa_client.py`, вебхуки и контуры описаны в `.env.example` (раздельные секреты для контура пациентских платежей и контура платформенного биллинга).
- **Платёжные шлюзы клиники:** сущность `ClinicPaymentGateway` (`src/domain/entities/clinic_payment_gateway.py`), админ-роуты `src/api/v1/routers/admin_payment_gateway.py`, бизнес-логика в `src/application/services/payment_service.py` и связанных сервисах.
- **Уведомления:** SMTP, SMSC (переменные в `.env.example`), Telegram-бот.
- **OAuth пациента:** VK и Яндекс — поля `vk_*`, `yandex_*` в `Settings` (`src/core/config.py`), сервис `src/application/services/oauth_auth_service.py`.
- **Captcha:** Cloudflare Turnstile (флаги `turnstile_*` в настройках).
- **Объектное хранилище:** S3-совместимый API (`s3_*` в настройках; медиа и пресайны — инфраструктурный слой `src/infrastructure/storage/`).
- **AI:** OpenAI-совместимый HTTP API (`AI_PROVIDER_*` в `.env.example`); при пустом base URL используются локальные заглушки (см. код AI-клиента и сервисов в `src/application/services/ai_*`).

## CI/CD и качество

- **Poetry** — зависимости backend; **npm** — frontend.
- **GitHub Actions** — workflow в `.github/workflows/` (pytest, entitlements, критический набор тестов, релизный gate, Trivy, проверка ссылок в markdown, опциональная публикация в Docker Hub, dry-run сборки образов).
- **Jenkins** — `Jenkinsfile`, публикация в GHCR для корпоративного контура (см. `CI_CD.md`).
- **Docker** — `Dockerfile` (backend), `frontend/Dockerfile`, `docker-compose.yml`.
- Статический анализ и форматирование: **Ruff**, **Black**, **mypy** (настройки в `pyproject.toml`).

## Где смотреть актуальный список пакетов

- Backend: `[tool.poetry.dependencies]` и группа dev в `pyproject.toml`.
- Frontend: `dependencies` / `devDependencies` в `frontend/package.json`.
