## ARCH_DOCKER_RUNTIME — стратегия сборки и запуска

> Роли: @LEAD, @ARCH, @DEV  
> Цель: единая, предсказуемая схема Docker‑окружения для backend, Celery, фронтенда и инфраструктурных сервисов (Postgres, Redis) для локальной разработки и базового стенда demo/stage.

---

### 1. Общая картина

- **Оркестрация**: один `docker-compose.yml` в корне проекта:
  - `db` — Postgres 16;
  - `redis` — Redis 7;
  - `backend` — FastAPI‑backend (Uvicorn + Alembic миграции);
  - `celery`, `celery-beat` — воркер и планировщик на том же backend‑образе;
  - `frontend` — статический фронт под Nginx.
- **Сборка образов**:
  - backend: `Dockerfile` в корне, multi-stage, Poetry, non-root пользователь `appuser`;
  - frontend: `frontend/Dockerfile`, multi-stage (Node → Nginx).
- **Секреты и конфиг**:
  - корневой `.env` — только для локальной разработки и `docker-compose` (НЕ коммитить);
  - `frontend/.env` — только build-time конфиг для Vite/SPA (коммитится при необходимости).

---

### 2. Backend: Dockerfile и запуск

**Dockerfile (корень проекта)**:

- **Stage 1 — builder**:
  - базовый образ: `python:3.11-slim`;
  - устанавливается Poetry (`poetry==1.7.1`) без virtualenv внутри контейнера;
  - по `pyproject.toml` / `poetry.lock` устанавливаются все зависимости.
- **Stage 2 — runtime**:
  - базовый образ: `python:3.11-slim`;
  - копируются установленные пакеты и `bin` из builder‑слоя;
  - копируется весь код (`COPY . .`);
  - создаётся non-root пользователь `appuser`, `WORKDIR /app`;
  - добавлен image‑level `HEALTHCHECK` на `http://localhost:8000/health`;
  - `EXPOSE 8000`, `CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

**Запуск в compose**:

- Сервис `backend`:
  - использует этот Dockerfile через:

    - `build.context: .`
    - `build.dockerfile: Dockerfile`
  - при запуске в `docker-compose` `CMD` из Dockerfile переопределяется:

    - `command: sh -c "python -m alembic -c alembic.ini upgrade heads && exec uvicorn src.main:app --host 0.0.0.0 --port 8000"`
  - зависимости:
    - ждёт `db` и `redis` до состояния `healthy` (`depends_on` + healthcheck-и).

- Сервисы `celery` и `celery-beat`:
  - используют тот же backend‑образ (`image: moircreator/dental-booking-backend:latest`);
  - переопределяют `command` на:
    - `celery -A src.infrastructure.messaging.celery_app worker --loglevel=info`;
    - `celery -A src.infrastructure.messaging.celery_app beat --loglevel=info`;
  - получают те же `DATABASE_URL` / `REDIS_URL` / `CELERY_*` из compose.

**Контракты по окружению**:

- В `docker-compose.yml` backend и воркеры получают:
  - `DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-dental_booking}`;
  - `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` с адресами `redis:6379`;
  - `env_file: - .env` — для остального конфига (CORS, JWT, интеграции и т.п.).
- Внутренние python‑компоненты должны опираться именно на эти переменные, не шить `localhost`.

---

### 3. Frontend: Dockerfile и Nginx

**Сборка** (`frontend/Dockerfile`):

- Stage `build`:
  - базовый образ: `node:20-alpine`;
  - `WORKDIR /app`;
  - `COPY package.json package-lock.json* ./` → `npm ci`;
  - `COPY . .` → `npm run build` (результат в `dist`).
- Stage runtime:
  - базовый образ: `nginx:alpine`;
  - `COPY --from=build /app/dist /usr/share/nginx/html`;
  - `COPY nginx.conf /etc/nginx/conf.d/default.conf`;
  - `EXPOSE 80`, `CMD ["nginx", "-g", "daemon off;"]`.

**Запуск в compose**:

- Сервис `frontend`:
  - `build.context: ./frontend`, `dockerfile: Dockerfile`;
  - публикуется наружу как `3004:80`;
  - получает `env_file: - ./frontend/.env` (для случаев, когда образ пересобирается с учётом Vite‑переменных).

**Контракты по окружению**:

- Все переменные, потребляемые фронтендом на build‑этапе, должны быть в `frontend/.env` и иметь префикс `VITE_`.
- Nginx-конфиг должен проксировать API на backend (порт 8000 внутри docker‑сети) по стабильному пути (`/api` или `/api/v1`).

---

### 4. Docker Compose: сервисы и сети

**Сервисы**:

- `db`:
  - `image: postgres:16-alpine`;
  - данные в volume `pgdata`;
  - healthcheck через `pg_isready`.
- `redis`:
  - `image: redis:7-alpine`;
  - данные в volume `redis_data`;
  - healthcheck через `redis-cli ping`.
- `backend`, `celery`, `celery-beat`, `frontend`:
  - объединены общей сетью по умолчанию (`bridge` docker-compose);
  - обращаются друг к другу по service‑имени (`db`, `redis`, `backend`, `frontend`).

**Порты наружу** (локальная разработка):

- Postgres: `5433:5432` (чтобы не конфликтовать с локальным Postgres);
- Redis: `6380:6379`;
- Backend (Uvicorn): `8004:8000`;
- Frontend (Nginx): `3004:80`.

---

### 5. .dockerignore и контекст сборки

**Корневой `.dockerignore`**:

- Очищает контекст backend‑сборки от:
  - виртуальных окружений (`.venv`, `venv`);
  - локального `.env` и производных;
  - `.git`, `.cursor`, IDE‑конфигов;
  - кешей (`.mypy_cache`, `.pytest_cache`, `.cache`) и логов;
  - node‑артефактов (`node_modules`, `frontend/node_modules`);
  - build‑артефактов (`dist`, `build`).
- Это ускоряет `docker build`, снижает вес контекста и исключает утечку секретов внутрь образа.

**`frontend/.dockerignore`**:

- Исключает:
  - `node_modules`, логи, IDE‑папки, кеши, build‑фолдеры;
  - при этом **не** исключает `frontend/.env`, чтобы Vite мог прочитать `VITE_*` переменные при сборке.

---

### 6. Операционные сценарии

**Локальная разработка (полный стек)**:

```bash
docker compose up -d --build
```

- поднимаются все сервисы, миграции применяются автоматически при старте backend;
- фронт доступен на `http://localhost:3004`;
- API — `http://localhost:8004` (или через Nginx‑прокси с фронта, в зависимости от `nginx.conf`).

**Пересборка только backend**:

```bash
docker compose build backend
docker compose up -d backend
```

**Пересборка только frontend**:

```bash
docker compose build frontend
docker compose up -d frontend
```

---

### 7. Расширение и новые модули

- **Новые backend‑модули** (CRM/ERP/Loyalty/Attribution):
  - по умолчанию живут внутри того же backend‑образа (единый FastAPI monolith);
  - фоновые задачи — в Celery (используются существующие `celery`/`celery-beat` сервисы).
- **Выделение в отдельный сервис** (по мере роста нагрузки):
  - создаётся новый Dockerfile по тому же паттерну (multi-stage, non-root, healthcheck);
  - в `docker-compose.yml` добавляется новый сервис с зависимостями `db`/`redis` и своей командой;
  - контракты по окружению и сетям документируются рядом (`ARCH_*.md` для конкретного модуля).

Этот файл — исходная точка для всех дальнейших изменений Docker‑окружения. При изменении образов, портов, healthcheck-ов или схемы сервисов его нужно обновлять в первую очередь.

