# Dental Booking

Backend (FastAPI) + frontend (Vite/React) для записи в стоматологию. Одна кодовая база, профили Enterprise / Box — см. `docs/artifacts/MASTER_PRODUCT_ROADMAP_2026.md`.

## Быстрый старт (разработка)

1. **Python 3.11**, **Poetry**, **Docker** (Postgres + Redis).
2. Скопируйте переменные окружения из `.env.example` в `.env` и задайте `DATABASE_URL`, `JWT_SECRET_KEY`, `SECRET_KEY`.
3. Поднимите БД и Redis: `docker compose up -d db redis`
4. Создайте тестовую БД (один раз):  
   `docker exec dental_booking_postgres psql -U postgres -c "CREATE DATABASE dental_booking_test;"`
5. Миграции: `alembic upgrade head` (или `python scripts/upgrade_test_db.py` для `dental_booking_test`).
6. Установка зависимостей: `poetry install`
7. Тесты API: `poetry run pytest tests/ -q`

Подробности подключения к тестовой БД — в комментариях в `tests/conftest.py` (`DATABASE_URL_TEST`).

### Docker: «Waiting», не поднимается, неверные имена сервисов

- В `docker-compose.yml` сервисы называются **`db`** и **`redis`**, не `postgres`. Команда вида `docker compose up -d postgres redis` завершится ошибкой `no such service: postgres` — используйте `docker compose up -d db redis`.
- Во время `docker compose up` строки **`Container … Waiting`** для Postgres/Redis — это ожидание успешного **healthcheck** перед сервисами с `depends_on: condition: service_healthy` (миграции, backend, celery). Не ошибка, если через короткое время появляется `Healthy` и контейнеры переходят в `Up`.
- Если «Waiting» действительно не заканчивается: `docker compose ps`, `docker compose logs db`, `docker compose logs redis` (порт 5442/6380 занят, повреждённый `./pgdata`, нехватка ресурсов WSL2). После сбоя Docker Desktop на Windows иногда помогает **Restart** из меню Docker или `wsl --shutdown`, затем снова запустить Docker Desktop.
- Полный стек: `docker compose up -d`. Если зависло после healthy db/redis — смотрите **`docker compose logs migrations`** (одноразовый job должен завершиться `Exited 0`).

## CI

На PR/push в `main`:

- **Backend CI** (`.github/workflows/backend-ci.yml`) — ruff, pytest, **tenant ORM audit** (`scripts/audit_tenant_columns.py`), pip-audit, gitleaks.
- **Security (Trivy FS)** (`.github/workflows/security-trivy.yml`) — уязвимости в зависимостях (CRITICAL).
- **DR restore drill** (`.github/workflows/restore-drill.yml`) — `pg_dump` / `pg_restore` и сверка `alembic_version` (по расписанию и вручную).

**CI/CD образы (GHCR через Jenkins)**: публикация Docker-образов и деплой выполняются Jenkins pipeline (`Jenkinsfile`) после зелёного gate. Runbook: `docs/operations/JENKINS_GHCR_RUNBOOK.md`.

### Образы Docker

Jenkins пушит минимум immutable-теги `:<git_sha>` (и при желании `:main`). Для деплоя предпочтительно использовать **digest**. **Trivy FS** в CI дополняет (не заменяет) скан **слоёв образа** в реестре — по политике SME и @LEAD.

### Локальный pre-push gate (блокирует push при любой ошибке)

Перед первым пушем включите репозиторные hooks:

`git config core.hooksPath .githooks`

Локальные hooks:

- `pre-commit`: быстрые проверки по staged-файлам (ruff/eslint), лог `.tmp_ci_logs/local-pre-commit-gate.log`.
- `pre-push`: полный quality gate (backend + frontend), лог `.tmp_ci_logs/local-pre-push-gate.log`.
- прямой push в `main` запрещен hook-ом (override только вручную: `ALLOW_MAIN_PUSH=1 git push ...`).

Ручной запуск:

- macOS/Linux/Git Bash: `bash scripts/dev/pre_push_gate.sh`
- Windows PowerShell: `powershell -ExecutionPolicy Bypass -File scripts/dev/pre_push_gate.ps1`

## Документация для операций

- Резервное копирование и восстановление БД: `docs/operations/DR_RUNBOOK.md`
- Журнал restore drill: `docs/operations/DR_DRILL_LOG.md`
- Smoke после деплоя: `docs/operations/DEPLOY_SMOKE.md`
- SME «коробка»: `docs/artifacts/SME_BOX_NFR_CHECKLIST.md`
- Первый прогон @LEAD (prod-smoke, скан образов в реестре): `docs/operations/LEAD_FIRST_RUN_OPS.md`
- **@LEAD — ворота продукта (GATE-0…6), коммерческий L-вердикт, DoD релиза:** `docs/LEAD_PRODUCT_GATE_PROTOCOL.md` · антигалочка: `docs/LEAD_ANTI_CHECKBOX_PROTOCOL.md` · эталон бизнес-логики UI: `docs/LEAD_PRODUCT_LOGIC_EXCELLENCE.md`
- Бэклог NFR (smoke URL, cosign, evidence pack, алерты backup и др.): `docs/operations/BACKLOG_NFR.md`
- Вклад в репозиторий: `CONTRIBUTING.md`
