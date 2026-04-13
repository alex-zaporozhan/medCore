# Dental Booking.

Backend (FastAPI) + frontend (Vite/React) для записи в стоматологию и смежных модулей клиники (расписание, чаты, CRM, ERP, лояльность — см. код и слой документации по коду ниже).

## Документация в репозитории

- **Что реально реализовано (RAG / онбординг):** [`docs/product_state/INDEX.md`](docs/product_state/INDEX.md) — паспорта backend и frontend, архитектура, структура репозитория, коммерческая интерпретация кода, полная карта всех `.md`.  
- **Порядок чтения для AI:** [`docs/RAG_CANON.md`](docs/RAG_CANON.md).  
- **Карта каталогов `docs/`:** [`docs/DOC_TOPOLOGY.md`](docs/DOC_TOPOLOGY.md).  
- **Политика (в т.ч. запрет ссылок на `.md` из прикладного кода):** [`DOCUMENTATION_POLICY.md`](DOCUMENTATION_POLICY.md).  
- **Запуск, миграции, типовые сбои:** [`docs/RUN_SERVICES.md`](docs/RUN_SERVICES.md), [`docs/MIGRATION_UPGRADE.md`](docs/MIGRATION_UPGRADE.md).  
- **Вклад в репозиторий:** [`CONTRIBUTING.md`](CONTRIBUTING.md).  
- **CI/CD:** VPS/демо по умолчанию — локальная сборка и push в **Docker Hub** ([`scripts/docker_hub_release.ps1`](scripts/docker_hub_release.ps1), [`documentation/VPS_IMAGE_AND_DATA.md`](documentation/VPS_IMAGE_AND_DATA.md)); корпоративный контур — **Jenkins + GHCR** ([`CI_CD.md`](CI_CD.md), [`AGENTS.md`](AGENTS.md)).  
- **Наблюдаемость (алерты, дашборды):** `deploy/prometheus/`, `deploy/grafana/README.md`.

Каталог **`documentation/`** — публичные материалы для клиентов и интеграторов (обзоры, USER_DOCS). Инженерный канон, архитектура, review и `docs/design/` — в **`docs/`** (см. [`DOCUMENTATION_POLICY.md`](DOCUMENTATION_POLICY.md)).

## Быстрый старт (разработка)

1. **Python 3.11**, **Poetry**, **Docker** (Postgres + Redis).
2. Скопируйте переменные окружения из `.env.example` в `.env` и задайте `DATABASE_URL`, `JWT_SECRET_KEY`, `SECRET_KEY`.
3. Поднимите БД и Redis: `docker compose up -d db redis`
4. Создайте тестовую БД (один раз):  
   `docker exec dental_booking_postgres psql -U postgres -c "CREATE DATABASE dental_booking_test;"`
5. Миграции: `alembic upgrade head` (или `python scripts/upgrade_test_db.py` для `dental_booking_test`).
6. Установка зависимостей: `poetry install`
7. Тесты API: `poetry run pytest tests/ -q`

Подробности по портам, compose и отладке: **`docs/RUN_SERVICES.md`**; переменная тестовой БД — комментарии в `tests/conftest.py` (`DATABASE_URL_TEST`).

### Docker: «Waiting», не поднимается, неверные имена сервисов

- В `docker-compose.yml` сервисы называются **`db`** и **`redis`**, не `postgres`. Команда вида `docker compose up -d postgres redis` завершится ошибкой `no such service: postgres` — используйте `docker compose up -d db redis`.
- Во время `docker compose up` строки **`Container … Waiting`** для Postgres/Redis — это ожидание успешного **healthcheck** перед сервисами с `depends_on: condition: service_healthy` (миграции, backend, celery). Не ошибка, если через короткое время появляется `Healthy` и контейнеры переходят в `Up`.
- Если «Waiting» действительно не заканчивается: `docker compose ps`, `docker compose logs db`, `docker compose logs redis` (порт 5442/6380 занят, повреждённый `./pgdata`, нехватка ресурсов WSL2). После сбоя Docker Desktop на Windows иногда помогает **Restart** из меню Docker или `wsl --shutdown`, затем снова запустить Docker Desktop.
- Полный стек: `docker compose up -d`. Если зависло после healthy db/redis — смотрите **`docker compose logs migrations`** (одноразовый job должен завершиться `Exited 0`).

## CI / CD

**Для одного VPS / демо:** соберите образы локально и отправьте в **Docker Hub** (пароль — только в интерактивном `docker login`): **[`scripts/docker_hub_release.ps1`](scripts/docker_hub_release.ps1)** или **[`scripts/docker_hub_release.sh`](scripts/docker_hub_release.sh)**; миграции и сиды — **[`documentation/VPS_IMAGE_AND_DATA.md`](documentation/VPS_IMAGE_AND_DATA.md)**.

**Корпоративный релиз:** **Jenkins** и **`Jenkinsfile`** — тесты (по параметру), сборка, push в **GHCR (`ghcr.io`)**, деплой на VM. Подробности: **[`CI_CD.md`](CI_CD.md)**.

**GitHub Actions** (`.github/workflows/`) — проверки PR, dry-run сборки образов без секретов, опциональный push на Hub при **`DOCKERHUB_USERNAME`** / **`DOCKERHUB_TOKEN`**. Не заменяют Jenkins, если у вас задействован корпоративный пайплайн.

### Образы Docker

- **Hub (VPS):** в `.env` — `docker.io/<user>/dental-booking-backend:<tag>` и аналогично frontend.
- **GHCR (Jenkins):** теги `:<git_sha>` / `:main`, для продакшена предпочтительно **digest**. Скан реестра — по политике организации.

### Локальный pre-push gate (блокирует push при любой ошибке)

Перед первым пушем включите репозиторные hooks:

`git config core.hooksPath .githooks`

Локальные hooks:

- `pre-commit`: быстрый gate (ruff + pytest smoke + frontend typecheck/build).
- `pre-push`: полный quality gate (backend + frontend), лог `.tmp_ci_logs/local-pre-push-gate.log`.
- прямой push в `main` запрещен hook-ом (override только вручную: `ALLOW_MAIN_PUSH=1 git push ...`).

Ручной запуск:

- macOS/Linux/Git Bash: `bash scripts/dev/pre_push_gate.sh`
- Windows PowerShell: `powershell -ExecutionPolicy Bypass -File scripts/dev/pre_push_gate.ps1`

Подробные процедуры резервного копирования, приёмки релизов и внутренние регламенты могут вестись вне публичного дерева этого репозитория.
