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
