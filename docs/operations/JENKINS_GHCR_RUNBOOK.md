# Jenkins + GHCR CI/CD Runbook (dental_booking)

Цель: уйти от Docker Hub и публиковать образы в **GHCR**, деплоить на VM через **Docker Compose**.

## 1) Jenkins: prerequisites

На хосте Jenkins:

- Linux agent (pipeline использует `sh` и рассчитан на стандартный Docker CLI).
- Docker Engine (доступ к `docker buildx`, `docker login`, `docker buildx build --push`)
- Git
- Python 3.11 + Node 20 (если запускаете тесты на агенте до сборки)

Рекомендуемые настройки job:

- `disableConcurrentBuilds()` (в `Jenkinsfile` уже включено)
- один pipeline на repo (Multibranch Pipeline)

## 2) Jenkins Credentials / variables

### 2.1 Credentials (Jenkins → Manage Credentials)

- `ghcr-username` (Secret text): GitHub username / bot-user
- `ghcr-token` (Secret text): GitHub PAT с правами:
  - `write:packages`
  - `read:packages`
  - (если нужно удалять/управлять — `delete:packages`)
- `deploy-ssh-key` (SSH Username with private key или Private key как secret) — ключ для доступа на VM

### 2.2 Job environment variables (в конфиге job, не в git)

- `GHCR_OWNER`: владелец пакетов в GHCR (org/user), например `my-org`
- `DEPLOY_HOST`: DNS/IP VM
- `DEPLOY_SSH_USER`: пользователь для SSH на VM

Опционально:

- `DEPLOY_SSH_PORT` (если нестандартный порт; тогда нужно расширить `Jenkinsfile`)

## 3) GitHub → Jenkins trigger

Вариант A (предпочтительно): GitHub Webhook

1. Jenkins: Multibranch Pipeline → GitHub repo.
2. GitHub repo settings → Webhooks → Add webhook:
   - Payload URL: URL Jenkins GitHub webhook endpoint (зависит от плагина/конфига)
   - Content type: `application/json`
   - Events: `Just the push event`
3. Убедиться, что Jenkins видит ветку `main` и запускает билд при push.

Вариант B: SCM polling (если webhooks недоступны)

- Jenkins job: включить polling по cron (например раз в 1–2 минуты).

## 4) GHCR packages access

Если packages private:

- VM должна логиниться в GHCR сервисным пользователем с `read:packages`.

Если packages public:

- `docker login` на VM можно не делать, но лучше держать доступ единообразным.

## 5) Deploy VM: one-time setup

На VM деплоя (в каталоге приложения, например `/opt/dental_booking`):

1. Должны лежать:
   - `docker-compose.yml` (из репо)
   - `.env` (локально на сервере, не в git)
2. Выполнить логин в GHCR:

```bash
echo "$GHCR_READ_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
```

3. Первый запуск:

```bash
docker compose pull
docker compose up -d
```

## 6) Как Jenkins делает деплой

`Jenkinsfile` на `main` (при `DEPLOY=true`) по SSH создаёт/обновляет файл:

- `${REMOTE_APP_DIR}/jenkins-images.env`

в котором задаёт:

- `BACKEND_IMAGE=ghcr.io/<owner>/dental-booking-backend@sha256:<digest>`
- `FRONTEND_IMAGE=ghcr.io/<owner>/dental-booking-frontend@sha256:<digest>`

Затем выполняет:

- `docker compose pull`
- `docker compose up -d`
- smoke: `curl -fsS $SMOKE_URL`

## 7) Smoke / rollback (оператор)

Smoke: см. `docs/operations/DEPLOY_SMOKE.md`.

Rollback (быстро):

- заменить `jenkins-images.env` на предыдущие digest-значения
- `docker compose pull && docker compose up -d`

