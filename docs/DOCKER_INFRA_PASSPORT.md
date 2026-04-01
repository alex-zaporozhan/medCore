# Паспорт Docker и деплоя (dental_booking)

Единый источник правды для @DEV / @OPS / @LEAD по образам, CI и запуску. Заменяет раздельные протоколы: локальная сборка, реестр, VPS и общие принципы — в одном месте.

---

## 1. Цель и границы

 - **Прод:** образы собираются в **Jenkins**, публикуются в **GHCR**; на VPS — только `pull` + `up`, без прод-сборки с нуля.
 - **Качество перед push:** Jenkins pipeline может запускать те же проверки (pytest/ruff, npm/vitest) до сборки образов. Gate — зелёный CI → затем build/push.
 - **Секреты:** не в Dockerfile, не в Git; только **Jenkins Credentials** и `.env` на машине (не коммитить).

---

## 2. Артефакты в репозитории

| Что | Путь |
|-----|------|
| Backend-образ (контекст корня) | `./Dockerfile` |
| Frontend (Vite → nginx) | `./frontend/Dockerfile` |
| Локально / VPS стек | `./docker-compose.yml` |
| CI/CD: Jenkins pipeline | `./Jenkinsfile` |

Сервисы в `docker-compose.yml`: `db`, `redis`, `migrations`, `backend`, `celery`, `celery-beat`, `frontend`.

---

## 3. Образы в GHCR

- backend: `ghcr.io/<GHCR_OWNER>/dental-booking-backend:<sha>` (+ опционально `:main`)
- frontend: `ghcr.io/<GHCR_OWNER>/dental-booking-frontend:<sha>` (+ опционально `:main`)

Для деплоя предпочтительно фиксировать **digest**:

- `BACKEND_IMAGE=ghcr.io/<GHCR_OWNER>/dental-booking-backend@sha256:<digest>`
- `FRONTEND_IMAGE=ghcr.io/<GHCR_OWNER>/dental-booking-frontend@sha256:<digest>`

База: `postgres:16-alpine`, `redis:7-alpine` — официальные, не билдятся в нашем CI.

---

## 4. CI/CD: порядок и условный push

1. **Tests** (опционально, но рекомендуется) — ruff/pytest, npm/vitest (и при необходимости E2E).
2. **Build & push** — только для `main`, после зелёного gate.
3. **Deploy** — на VPS через `docker compose pull && docker compose up -d`.

Jenkins pipeline: `./Jenkinsfile`.
Секреты Jenkins: `ghcr-token`, `ghcr-username`, `deploy-ssh-key` (и переменные `GHCR_OWNER`, `DEPLOY_HOST`, `DEPLOY_SSH_USER` как job env).

---

## 5. Локальная разработка (Compose)

- Переменные: корневой `.env` (см. комментарии в `docker-compose.yml`); для фронта при необходимости `./frontend/.env`.
- Типовые порты из compose: backend `8010:8000`, frontend `3010:80`, Postgres `5442:5432`, Redis `6380:6379`.

**Что пересобирать при правках:**

| Изменения | Действие |
|-----------|----------|
| Только `frontend/**` | `docker compose build frontend` (или `build --no-cache` при подозрении на кэш) |
| Backend (`src/**`, `Dockerfile`, зависимости Poetry) | `docker compose build backend` (образ же для `migrations`, `celery`, `celery-beat`) |
| Оба / первый запуск | `docker compose build` нужных сервисов или полный build |

Затем `docker compose up -d`. Для миграций смотри `docs/MIGRATION_UPGRADE.md`.

---

## 6. РФ / медленная сеть: зеркала и buildx

- **Зеркало реестра** (Docker Desktop / `daemon.json`): например `registry-mirrors` с `https://mirror.gcr.io` и при необходимости провайдерским зеркалом — см. актуальные рекомендации вашей среды.
- Зависание на **«resolving provenance»** при локальной сборке: задать перед сборкой  
  `BUILDX_NO_DEFAULT_ATTESTATIONS=1`  
  или использовать `docker buildx build` с отключением attestations в вашей среде.
- Базовые образы в Dockerfile: `python:3.11-slim`, `node:20-alpine`, `nginx:alpine` — при желании закреплять digest для воспроизводимости (отдельным изменением в Dockerfile).

### 6.1 Ошибка: `dockerhub1.beget.com` и `127.0.0.1:12334` (actively refused)

Сообщение вида `Head "https://dockerhub1.beget.com/...": ... connecting to 127.0.0.1:12334: connectex: ... actively refused` означает:

1. В **Docker Engine** настроено **зеркало Docker Hub** (часто провайдерское, например Beget), и запросы к нему идут не напрямую.
2. Для исходящих HTTPS-запросов демон использует **HTTP(S) proxy на локальном порту** (здесь `12334`). Отключение VPN **не сбрасывает** прокси в Docker Desktop — это отдельная настройка.

**Что сделать (Windows, Docker Desktop):**

1. **Docker Desktop** → **Settings** → **Resources** → **Proxies**  
   - Отключите **Manual proxy configuration** или очистите поля HTTP/HTTPS proxy и сохраните.  
   - Либо укажите **рабочий** прокси, если он вам нужен (порт должен совпадать с реально запущенным приложением).

2. Перезапустите **Docker Desktop** (Quit → снова запустить).

3. Если ошибка сохраняется, проверьте JSON демона (путь может отличаться по версии):  
   `%USERPROFILE%\.docker\daemon.json`  
   Временно уберите или закомментируйте блок **`registry-mirrors`**, если там указано зеркало Beget / другое зеркало, которое ломается с вашим прокси; сохраните файл и снова перезапустите Docker Desktop. Прямой pull с `registry-1.docker.io` часто оказывается стабильнее, чем зеркало + «мёртвый» локальный прокси.

4. Убедитесь, что в **системных** переменных Windows / профиле PowerShell не заданы `HTTP_PROXY` / `HTTPS_PROXY` на `127.0.0.1:12334` для сценариев, где Docker их подхватывает (реже, но встречается).

После этого повторите: `docker compose build frontend`.

---

## 7. VPS (нормальный деплой)

1. Один раз: `docker login ghcr.io` под учёткой с **read** доступом к GHCR (service user / PAT).
2. Обновить compose из Git: `git pull`.
3. `docker compose pull` — подтянуть новые образы.
4. `docker compose up -d`.
5. Проверка: `docker ps`, health backend, ответ фронта на опубликованном порту.

Прод-деплой **не** опирается на `docker compose build` на сервере (исключение — явная отладка по решению @LEAD).

---

## 8. Правила для @DEV (изменения инфраструктуры)

- Не менять имена `image:` в `docker-compose.yml` на другой реестр/репозиторий без согласования с @LEAD и правок Jenkins pipeline.
- Dockerfile: многостадийность где уместно, слои зависимостей отдельно от кода, без секретов в `ENV`/`COPY`, по возможности не root в runtime (backend уже `USER appuser`).
- Любые сомнения по тегам, новым сервисам или секретам — короткая запись в задаче/отчёте и согласование с @LEAD / @ARCH.

---

## 9. Зрелость (Enterprise): текущее и опционально

**Уже есть:** conditional rebuild, тестовый gate до push, кэш buildx (`gha`), healthcheck backend в compose и Dockerfile, отдельный сервис миграций, Celery/beat на том же backend-образе.

**Опционально под отдельную задачу:** сканирование образов (Trivy и т.д.), подпись образов, SBOM, прогон части тестов в контейнере как отдельный job — не смешивать с текущим обязательным контрактом без явного решения @ARCH/@LEAD.

---

## 10. Минимальный чеклист перед merge Docker-изменений

- [ ] Затронутые пути совпадают с ожиданием от path-filter (нужен ли реальный push образа).
- [ ] Локально или в CI образ собирается без утечки секретов.
- [ ] При смене портов/env обновлены примеры (`.env.example` и т.д., если есть).
- [ ] После merge: на `main` дождаться зелёного workflow перед деплоем на VPS.

---

Reference: `docker-compose.yml` · `Jenkinsfile` · `docs/MIGRATION_UPGRADE.md`
