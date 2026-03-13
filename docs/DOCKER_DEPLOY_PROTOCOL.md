## Протокол Docker‑деплоя для проекта

**Цель**: всегда деплоить только через образы, собранные на GitHub Actions и опубликованные в Docker Hub, без ручных билдов на VPS.

### 1. Базовые принципы

- **Единый источник образов**: все прод‑образы бекенда и фронтенда собираются только на GitHub Actions и пушатся в Docker Hub (`moircreator/web-landing-*`).
- **VPS никогда не собирает образы с нуля** (кроме отладки). На сервере выполняются только:
  - `git pull`
  - `docker compose pull`
  - `docker compose up -d`
- **Секреты (пароли, токены)**:
  - не хранятся в репозитории в открытом виде;
  - для GitHub Actions — только через `Repository secrets`;
  - для Docker Hub на VPS — через `docker login` (файл `~/.docker/config.json`).
- **docker-compose.yml** описывает _как запускать_ контейнеры на VPS; Dockerfile’ы — _как их собирать_ (делает GitHub Actions).

---

### 2. Структура Docker‑файлов в проекте

- `backend/Dockerfile` — FastAPI + Uvicorn, порт 8000 внутри контейнера.
- `frontend/Dockerfile` — Vite → сборка статики → nginx, порт 80 внутри контейнера.
- `docker-compose.yml` (корень проекта) — один файл для VPS:
  - `backend`:
    - `image: moircreator/web-landing-backend:latest`
    - порт на VPS: `8004:8000`
    - `DATABASE_URL`, `ALLOWED_ORIGINS` и пр.
  - `frontend`:
    - `image: moircreator/web-landing-frontend:latest`
    - порты на VPS: `3004:80` (прод под nginx), `3001:80` (прямой доступ — опционально)
  - `db`:
    - `image: postgres:16-alpine`
    - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

> Правило: при изменении Dockerfile’ов убедиться, что GitHub Actions по‑прежнему может собрать образы из `./backend` и `./frontend`.

---

### 3. Образы и реестр (Docker Hub)

- Бекенд:
  - образ: `moircreator/web-landing-backend:latest`
  - собирается из `backend/Dockerfile`.
- Фронтенд:
  - образ: `moircreator/web-landing-frontend:latest`
  - собирается из `frontend/Dockerfile`.
- БД:
  - официальный образ `postgres:16-alpine`, не билдится в CI.

#### Никогда не менять в `docker-compose.yml`:

- `image: moircreator/web-landing-backend:latest`
- `image: moircreator/web-landing-frontend:latest`

Если нужны версии — добавлять тег, например `:v1`, последовательно меняя:

- теги в GitHub Actions;
- теги в `docker-compose.yml`.

---

### 4. GitHub Actions: pipeline сборки образов

Файл: `.github/workflows/docker-images.yml`

- Триггер: `push` в ветку `main`.
- Шаги (упрощённо):
  1. `actions/checkout` — забирает код.
  2. `dorny/paths-filter` — определяет, какие части проекта изменились:
     - если тронуты файлы в `backend/**` → `backend_changed = true`;
     - если тронуты файлы в `frontend/**` → `frontend_changed = true`.
  3. `docker/login-action` — логин в Docker Hub по секретам:
     - `DOCKERHUB_USERNAME`
     - `DOCKERHUB_TOKEN`
     - выполняется **только если** изменился backend или frontend.
  4. `docker/setup-buildx-action` — подготовка билдера (также только при изменениях).
  5. `docker/build-push-action` (backend) → пуш в `moircreator/web-landing-backend:latest`, **только если** `backend_changed = true`.
  6. `docker/build-push-action` (frontend) → пуш в `moircreator/web-landing-frontend:latest`, **только если** `frontend_changed = true`.

> Принцип: **не пересобирать образы без необходимости**. Если в коммите изменились только доки или файл фронта, который не затрагивает бэкенд, GitHub Actions пересобирает и пушит только соответствующий образ (или вообще пропускает сборку, если код не трогали).

**Требование:** секрета `DOCKERHUB_TOKEN` в GitHub достаточно, чтобы пушить только в репозитории пользователя `moircreator`. Не хранить этот токен в коде или в `.env`.

---

### 5. Правила по `docker-compose.yml`

- Хранится в репозитории; **это контракт для VPS**.
- Разрешённые изменения:
  - порты публикации (`"3004:80"`, `"8004:8000"`);
  - переменные окружения (но без секретов для GitHub Actions);
  - доп. опции `restart`, `depends_on`, `volumes` и т.п.
- Неразрешённые изменения без явного запроса:
  - смена `image` на другие реестры/имена;
  - удаление сервисов `backend` или `frontend`;
  - добавление новых секретов прямо в файл (лучше вынести в `.env`).

---

### 6. Правила по `.env` и конфигурации

Бекенд:

- `backend/.env.example` — **эталон** структуры, можно коммитить.
- `backend/.env`:
  - локально: хранится у разработчика, **может быть в .gitignore**;
  - для VPS: значения можно передавать через `docker-compose.yml` (как сейчас) или отдельным `.env` файлом на сервере, который не пушится.

Рекомендуемая схема:

- В репо:
  - `backend/.env.example` c фейковыми логином/паролем и комментариями.
- На VPS:
  - реальное `.env` (или переменные окружения в `docker-compose.yml`).

---

### 7. Поведение на VPS

Нормальный сценарий:

1. `docker login -u moircreator` (однажды на сервере).
2. Перед деплоем:
   - `git pull origin main`
   - `docker compose pull` — затягивает последние образы из Docker Hub.
   - `docker compose up -d` — пересоздаёт контейнеры с новыми образами.
3. Проверка:
   - `docker ps` — контейнеры `app-backend-1`, `app-frontend-1`, `app-db-1` в статусе `Up`.
   - `curl -I http://127.0.0.1:3004` — фронтенд жив.
   - `curl -I https://goodcode-app.ru` — домен отдаёт сайт через nginx.

> Важно: на VPS **не используем** `docker compose build` для прод‑деплоя. Если билд нужен для отладки — только по отдельному решению.

---

### 8. Роль @DEV (докер‑часть)

Когда @DEV меняет код:

1. При необходимости обновить Dockerfile’ы (`backend` или `frontend`), не трогая `image` в `docker-compose.yml`.
2. Проверить локальную сборку (по желанию):
   - `docker compose build`
   - `docker compose up`
3. Сделать `git commit` + `git push main`.
4. Убедиться, что GitHub Actions успешно собрал и запушил образы.

Только после успешного CI запускать деплой на VPS.

