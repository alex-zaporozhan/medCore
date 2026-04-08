# CI/CD в этом репозитории

## Источник правды: Jenkins

- **Сборка образов, публикация в реестр и деплой на VM** выполняются **Jenkins** по корневому **`Jenkinsfile`** (не GitHub Actions).
- В пайплайне: тесты (опционально), `docker buildx`, push, затем обновление `docker compose` на сервере по SSH (см. параметры в `Jenkinsfile`).
- Учётные данные для реестра и SSH настраиваются **в Jenkins** (credentials), не хранятся в git.

## Реестр образов: GHCR, не Docker Hub

- Образы пушатся в **GitHub Container Registry** (`ghcr.io`), см. переменные `GHCR_*` / `BACKEND_IMAGE_REPO` / `FRONTEND_IMAGE_REPO` в `Jenkinsfile`.
- **Docker Hub и платные лимиты Docker Hub для этого проекта не используются** и не являются обязательными: деплой строится на GHCR + digest (см. `docker-compose.yml` и комментарии там).

## GitHub Actions

- Workflow в **`.github/workflows/`** — дополнительные проверки (PR: линты, тесты, ссылки в markdown, Trivy и т.д.), **не заменяют** Jenkins для релизного образа и прод-деплоя.
- Часть workflow может лежать в **`workflows_disabled/`** — это осознанный долг или резерв; первичный контур релиза остаётся Jenkins.

## Локально

- Pre-commit / pre-push (`.githooks`) — быстрый контроль перед push; не путать с Jenkins.

Подробнее для разработчиков: **`README.md`** (раздел CI), **`CONTRIBUTING.md`**.
