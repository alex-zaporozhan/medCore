# Contributing

Политика публичной документации и границы git: **`DOCUMENTATION_POLICY.md`**.

**CI/CD:** для VPS/демо по умолчанию — локальная сборка и **Docker Hub** (`scripts/docker_hub_release.ps1` / `.sh`, см. **`CI_CD.md`**). Корпоративный контур — **Jenkins** + **GHCR**. GitHub Actions — вспомогательные проверки PR и опциональный push на Hub при secrets.

## Pull requests

When closing backlog items, link the task/issue in the PR description. If your team keeps an internal engineering log, reference it there (paths are not fixed in this public file).

1. **Traceability** — In the PR description, link the **ID** (issue, task key) and the section or acceptance criteria you implemented.
2. **Tests** — Run and note `pytest` / `vitest` for **modules you touched** (full suite if feasible). Test DB: **`documentation/DEVELOPMENT.md`**, запуск сервисов — **`docs/RUN_SERVICES.md`**; `tests/conftest.py` (`DATABASE_URL_TEST`, `dental_booking_test`).
3. **Config** — New env vars: `.env.example` and operator-facing notes per team process.
4. **NFR** — If metrics, alerts, or dashboards change, update what your team tracks (see **`documentation/OBSERVABILITY.md`** for repo paths) and internal records as required.

GitHub will show `.github/pull_request_template.md` when opening a PR.

## API: частичные обновления (PUT/PATCH)

Один контракт для тел админских **PUT** и **PATCH**:

- В сервис передавайте **`body.model_dump(exclude_unset=True)`** (или эквивалент), чтобы не затирать поля `None` / значения по умолчанию при частичном теле запроса.
- DTO ответа и полная замена ресурса там, где клиент обязан прислать весь объект — по отдельной договорённости; для «полей по желанию» предпочтительны PATCH + `exclude_unset`.

## Supply chain (backend)

JWT: **PyJWT** only (`src/core/security.py`), без `python-jose`. После смены зависимостей выполняйте `poetry sync` (или переустановку venv), чтобы не оставались старые транзитивные пакеты в локальном окружении. Аудит зависимостей и тесты в релизном контуре — по **`Jenkinsfile`** и при необходимости workflow в `.github/workflows/`.
