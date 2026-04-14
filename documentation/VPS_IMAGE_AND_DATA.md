# VPS: образы Docker Hub и данные в БД

## Образы (рекомендуемый путь для одного VPS)

1. **Сборка и push с вашей машины** (пароль Docker Hub только в интерактивном запросе `docker login`, без секретов в GitHub):

   - Windows (PowerShell из корня репозитория):

     ```powershell
     .\scripts\docker_hub_release.ps1 -Tag demo
     ```

   - Linux / macOS:

     ```bash
     chmod +x scripts/docker_hub_release.sh
     DOCKERHUB_USERNAME=youruser ./scripts/docker_hub_release.sh demo
     ```

   Сначала выполняются **два `docker build`**; при ошибке push **не выполняется**.

2. На сервере в `.env` укажите теги, например:

   ```env
   BACKEND_IMAGE=docker.io/youruser/dental-booking-backend:demo
   FRONTEND_IMAGE=docker.io/youruser/dental-booking-frontend:demo
   ```

3. **GitHub Actions** (опционально): если удобнее хранить `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` в secrets репозитория — workflow **`.github/workflows/docker-hub-publish.yml`** сначала собирает образы **без** учётных данных реестра, затем логинится и пушит. Интерактивный ввод пароля в Actions **невозможен** — только secrets.

4. **Проверка Dockerfile без push** (форки, PR): **`.github/workflows/docker-images-build-verify.yml`**.

Корпоративный контур **Jenkins → GHCR** остаётся в **`Jenkinsfile`** и **`CI_CD.md`** для команд, которые так задеплоены.

---

## Минимальный чеклист VPS (стандартный `docker-compose.yml`)

Ниже — короткий путь «поднять и показать»; полный compose (Celery, nginx и т.д.) не выкидывается — это тот же файл в корне репозитория.

1. **На сервере:** клон репозитория или только `.env` + `docker-compose.yml` (если образы уже на Hub и правки compose не нужны).
2. **`.env`:** скопируйте из **`.env.example`**, задайте сильные **`SECRET_KEY`**, **`JWT_SECRET_KEY`**, пароль **`POSTGRES_PASSWORD`**, при необходимости **`PLATFORM_FOUNDER_JWT_SECRET`** (см. комментарии в `.env.example`).
3. **Образы с Docker Hub** (после push из Actions или `scripts/docker_hub_release.*`):

   ```env
   BACKEND_IMAGE=docker.io/<DOCKERHUB_USER>/dental-booking-backend:main
   FRONTEND_IMAGE=docker.io/<DOCKERHUB_USER>/dental-booking-frontend:main
   ```

4. **Запуск:** из корня репозитория:

   ```bash
   docker compose pull   # если используете готовые образы с registry
   docker compose up -d
   ```

   Сервис **`migrations`** (в compose) сам выполнит **`alembic upgrade head`** до старта **`backend`**; пустой volume Postgres — нормальное «нулевое» состояние: появится только схема.

5. **Порты по умолчанию в этом compose:** API **8010→8000**, SPA **3010→80**, Postgres **5442→5432**, Redis **6380→6379**. Проверка API: `GET http://<host>:8010/health`, витрина: `http://<host>:3010/`.
6. **Первый вход «под ключ» для демо:** после миграций — **`create_platform_founder_user`**, опционально **`seed_rbac_baseline`** / **`seed_multi_tenant_showcase`** / тяжёлое **`seed_presentation_showcase`** (см. ниже и **`documentation/DEMO_MULTI_TENANT_CREDENTIALS.md`**).

GitHub Actions: зелёные **pytest-gates** и публикация образов — разные workflow; см. **`CI_CD.md`**.

---

## Схема БД (клиент: «пустая» система)

Только структура, без демо-пользователей:

```bash
# Postgres уже запущен (docker compose или хост)
poetry run alembic upgrade head
# или контейнер миграций из docker-compose.yml
```

Отдельная «пустая» миграция Alembic не нужна: `upgrade head` поднимает всю актуальную схему.

---

## Наполнение для кабинета Основателя платформы и мультиклиник

После миграций и при необходимости RBAC-матрицы:

```bash
poetry run python -m src.scripts.seed_rbac_baseline
poetry run python -m src.scripts.seed_multi_tenant_showcase
```

Учётная запись **Основателя** скриптом не создаётся:

```bash
poetry run python -m src.scripts.create_platform_founder_user --email ... --password ...
```

Список демо-логинов клиник и пароль: **`documentation/DEMO_MULTI_TENANT_CREDENTIALS.md`**.

Моноклиника «тяжёлое» демо (омниканал, воронка, много записей): **`src/scripts/seed_presentation_showcase.py`** — не смешивайте на одной БД без осознанного сброса; см. docstring скрипта.
