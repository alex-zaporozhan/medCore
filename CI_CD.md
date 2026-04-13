# CI/CD в этом репозитории

## VPS и Docker Hub (практический путь по умолчанию для демо/одного сервера)

- **Рекомендуется:** собрать образы **локально**, убедиться что `docker build` прошёл, затем **`docker login`** (пароль или token только в запросе в терминале) и **`docker push`**.
- Скрипты из корня репозитория:
  - Windows: **`scripts/docker_hub_release.ps1`** (параметр `-Tag`, опционально `$env:DOCKERHUB_USERNAME`).
  - Linux/macOS: **`scripts/docker_hub_release.sh`** (`DOCKERHUB_USERNAME=... ./scripts/docker_hub_release.sh <tag>`).
- На VPS в `.env` задайте, например: `BACKEND_IMAGE=docker.io/<user>/dental-booking-backend:<tag>` и то же для frontend (см. **`documentation/VPS_IMAGE_AND_DATA.md`**).
- **GitHub Actions** с push на Hub возможны только с секретами **`DOCKERHUB_USERNAME`** / **`DOCKERHUB_TOKEN`** в настройках репозитория (интерактивный ввод в CI недоступен). Workflow **`.github/workflows/docker-hub-publish.yml`** сначала выполняет **два `docker build` без логина**, затем логин и push — при падении сборки push не выполняется.

## Проверка Dockerfile без пуша и без секретов

- **`.github/workflows/docker-images-build-verify.yml`** — только `docker build` (`push: false`), в т.ч. для форков.

---

## Корпоративный контур: Jenkins и GHCR

- Для команд с **Jenkins**: сборка, публикация и деплой на VM — корневой **`Jenkinsfile`**; образы в **GitHub Container Registry (`ghcr.io`)** — см. переменные `GHCR_*` / `BACKEND_IMAGE_REPO` / `FRONTEND_IMAGE_REPO`.
- Учётные данные реестра и SSH задаются **в Jenkins**, не в git.
- **GitHub Actions** в **`.github/workflows/`** — дополнительные проверки PR (тесты, линки, Trivy и т.д.), **не заменяют** Jenkins, если у вас настроен этот пайплайн.

## Локально

- Pre-commit / pre-push (`.githooks`) — быстрый контроль перед push.

Подробнее для разработчиков: **`README.md`** (раздел CI), **`CONTRIBUTING.md`**, данные для VPS и БД — **`documentation/VPS_IMAGE_AND_DATA.md`**.
