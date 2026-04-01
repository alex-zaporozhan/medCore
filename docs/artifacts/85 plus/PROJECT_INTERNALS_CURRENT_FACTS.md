## PROJECT_INTERNALS_CURRENT_FACTS — внутрянка проекта (факты из кода/конфигов)

> Документ фиксирует то, что **подтверждается текущими файлами** репозитория: какие “сервисы” реально запускаются, какой есть CI/CD, как устроен деплой, что с тестами.
>
> Обозначения: если чего-то “нет в репозитории”, это также является фактом (например, нет workflow для тестов).

---

## 1) Какие “микросервисы” у нас фактически есть

С практической точки зрения, проект запускается как **модульный backend + отдельные worker/beat процессы**, и **отдельный frontend**.

В текущей конфигурации `docker-compose.yml` есть следующие unit’ы:

1. `db` — PostgreSQL 16 (`postgres:16-alpine`)
2. `redis` — Redis 7 (`redis:7-alpine`)
3. `backend` — FastAPI приложение (uvicorn) + автозапуск миграций Alembic перед стартом
4. `celery` — Celery worker (очереди фоновых задач)
5. `celery-beat` — Celery beat (периодические задания)
6. `frontend` — Nginx, отдающий собранный frontend (dist) и проксирующий `/api/` на `backend`

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

Перед запуском uvicorn контейнер `backend` выполняет:
1) `alembic ... upgrade head`
2) затем `uvicorn ...`

Источник: `docker-compose.yml` (команда контейнера `backend`).

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

Есть GitHub Actions workflow:
- `.github/workflows/docker-images.yml`

Ключевые характеристики:
- Trigger: `push` в ветку `main`
- Conditional builds через `dorny/paths-filter`:
  - backend image пересобирается только если поменялись backend-файлы (Dockerfile/pyproject/poetry.lock/src/**/alembic/**)
  - frontend image пересобирается только если поменялись frontend-файлы (frontend/**)
- Из образов делается push в Docker Hub:
  - backend: `moircreator/dental-booking-backend:latest`
  - frontend: `moircreator/dental-booking-frontend:latest`

Важно: в workflow **не видно шагов запуска unit/integration/e2e тестов**, анализа покрытия или линтинга.

Источник: `.github/workflows/docker-images.yml`.

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

Миграции запускаются автоматически в `backend` контейнере при старте через команду контейнера (upgrade `head`).

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

По текущему workflow `.github/workflows/docker-images.yml` тесты **не запускаются**.

---

## 6) Что в репозитории отсутствует (важные “нет”, которые стоит проговорить команде)

1. Нет явного CD workflow (staging/prod deploy) — найден только build+push в Docker Hub.
2. Нет workflow шагов тестирования/линтинга/сканирования зависимостей (хотя инструменты есть в dev dependencies).
3. В корне репозитория не обнаружены `Makefile` и `README.md` (возможно, это было в “карте файлов”, но фактически их нет в текущем дереве).

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

