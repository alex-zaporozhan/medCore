## PROJECT_INTERNALS_CURRENT_FACTS — внутрянка проекта (факты из кода/конфигов)

> **Статус (редакция 2026-04):** исходный снимок дополнен сверкой с `docker-compose.yml` и `.github/workflows/*`. Для актуального CI см. корневой **`CI_CD.md`** и **`AGENTS.md`**.

> Документ фиксирует то, что **подтверждается текущими файлами** репозитория: какие “сервисы” реально запускаются, какой есть CI/CD, как устроен деплой, что с тестами.
>
> Обозначения: если чего-то “нет в репозитории”, это также является фактом (например, нет workflow для тестов).

---

## 1) Какие “микросервисы” у нас фактически есть

С практической точки зрения, проект запускается как **модульный backend + отдельные worker/beat процессы**, и **отдельный frontend**.

В текущей конфигурации `docker-compose.yml` есть следующие unit’ы:

1. `db` — PostgreSQL 16 (`postgres:16-alpine`)
2. `redis` — Redis 7 (`redis:7-alpine`)
3. `migrations` — одноразовый job на образе backend: `alembic upgrade head`, затем контейнер завершается
4. `backend` — FastAPI (только `uvicorn`; стартует после успешного `migrations`)
5. `celery` — Celery worker
6. `celery-beat` — Celery beat
7. `frontend` — Nginx со статической сборкой и прокси `/api/` → `backend`

Важно: по текущим конфигам **отдельных микросервисов “по доменам” (CRM/ERP/Booking как разные deployables)** нет. Все domain-конечные точки обслуживаются **одним backend-контейнером**; различается только обработка фоновых задач (Celery worker/beat).

Источник: `docker-compose.yml`, `src/main.py`, `frontend/nginx.conf`.

---

## 2) Как устроен запуск (архитектурные компоненты runtime)

### 2.1. Backend

- Точка входа: `src.main:app`
- Присутствуют health/metrics:
  - `GET /health` — `{status: "ok", service: ...}`
  - `GET /metrics` — Prometheus-метрики
- На старте/останове:
  - регистрируются event handlers (CRM/ERP/Loyalty/Tasks/Marketing Attribution)
  - корректно закрывается Redis-клиент

Источник: `src/main.py`.

### 2.2. Миграции

Отдельный сервис **`migrations`** (тот же образ, что у `backend`) выполняет `python -m alembic -c alembic.ini upgrade head` и завершается. Контейнер **`backend`** запускает только **`uvicorn`** и ждёт успешного завершения `migrations` (`depends_on: service_completed_successfully`).

Источник: `docker-compose.yml` (сервисы `migrations` и `backend`).

### 2.3. Celery / очередь задач

- Брокер задач: Redis (`CELERY_BROKER_URL: redis://redis:6379/1`)
- Backend результатов: Redis (`CELERY_RESULT_BACKEND: redis://redis:6379/2`)
- Есть отдельные контейнеры:
  - `celery` — worker
  - `celery-beat` — планировщик

Источник: `docker-compose.yml`.

### 2.4. Frontend

- Собирается в Docker через `frontend/Dockerfile` (Vite build)
- Результат отдаёт `nginx:alpine`
- Nginx конфиг проксирует `/api/` в `backend:8000`

Источник: `frontend/Dockerfile`, `frontend/nginx.conf`.

---

## 3) CI/CD: что есть и как устроено по факту

### 3.1. Наличие CI в репозитории

Есть несколько GitHub Actions workflow в **`.github/workflows/`**, в т.ч.:

- **`backend-ci.yml`** — Poetry, pytest (часто с Postgres/Redis services и подъёмом Vite preview для браузерных тестов), gitleaks, pip-audit и др. по YAML.
- **`build-and-test-entitlements.yml`**, **`release-gate.yml`**, **`critical-path-gate.yml`** — расширенные/релизные прогоны pytest.
- **`docker-hub-publish.yml`** — опциональная сборка и push образов в Docker Hub при настроенных секретах (`DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`); триггеры и path-filter см. в файле.
- **`docker-images-build-verify.yml`** — только `docker build` без push (без секретов).
- **`documentation-markdown-links.yml`**, **`security-trivy.yml`**, **`dr-restore-drill.yml`** — качество документации и безопасность.

Имена образов на Hub задаёт владелец репозитория (`<user>/dental-booking-backend:<tag>` и аналогично frontend), а не фиксированный префикс в YAML.

Источник: перечисленные файлы под `.github/workflows/`.

### 3.2. CD (deplyment) в репозитории

В текущем репозитории **не найдено автоматического CD** (нет workflow/скрипта “deploy на staging/prod”).

По факту deployment сделан “Docker-как-истина”:
- есть образы (судя по CI),
- есть `docker-compose.yml` как runtime,
- а дальше предполагается ручной/внешний процесс “pull + up -d”.

---

## 4) План деплоя по факту (что реально можно повторить)

Поскольку CD-автоматизации в репозитории не обнаружено, деплой описывается через runtime Docker и конфиги окружения.

### 4.1. Как поднять “всё” через compose

Источник: `docker-compose.yml` и `.env.example`.

Минимальная схема запуска (на уровне примечаний в `.env.example` и compose):
1) поднять `postgres` и `redis`
2) поднять `backend`, `celery`, `celery-beat`, `frontend`

### 4.2. Миграции при деплое

Миграции выполняет одноразовый сервис **`migrations`** до старта **`backend`** (см. §2.2).

---

## 5) Тесты: что есть в репозитории

### 5.1. Backend test framework

В `pyproject.toml` в `tool.poetry.group.dev.dependencies`:
- `pytest`
- `pytest-asyncio`
- `pytest-playwright`

Также описаны тестовые markers в `tool.pytest.ini_options`:
- `regression_payments`
- `regression_pd`
- `regression_chats`
- `security`

Источник: `pyproject.toml`.

### 5.2. Frontend test framework

В `frontend/package.json`:
- dev script `test`: `vitest`

Источник: `frontend/package.json`.

### 5.3. Запуск тестов в CI

Pytest и связанные проверки запускаются в **`backend-ci.yml`** и других workflow (см. §3.1). Для E2E часто задаётся **`FRONTEND_E2E_URL`** и скрипт **`scripts/ci/run_pytest_with_e2e_preview.sh`**.

---

## 6) Что в репозитории отсутствует (важные “нет”, которые стоит проговорить команде)

1. Нет единого “нажал кнопку — задеплоилось на прод” workflow в GitHub Actions: типичный VPS-сценарий — образы в registry + ручной **`docker compose pull/up`** (см. **`CI_CD.md`**, **`documentation/VPS_IMAGE_AND_DATA.md`**).
2. В корне может не быть **`Makefile`** — это не обязательный элемент; команды смотреть в **`README.md`** и **`documentation/DEVELOPMENT.md`**.

---

## 7) Короткое резюме “как это выглядит на проде”

Продовый runtime по текущему дизайну:
- один backend endpoint слой (FastAPI) обслуживает API;
- фоновые операции исполняются отдельными Celery worker контейнерами;
- планировщик периодики — celery-beat;
- frontend — nginx + статическая сборка + reverse proxy на `/api/`.

---

## 8) Быстрые улучшения “минимум для коммерческого уровня” (не обязательные, но полезные)

- Добавить CI шаги: `pytest` (backend) + `vitest` (frontend) + security scans (SCA/dependency) + fail-on-critical.
- Добавить CD или хотя бы staging deploy workflow с простым canary/rollback чеклистом.
- Уход от `:latest` на версионные теги (например, git sha) для воспроизводимости.

