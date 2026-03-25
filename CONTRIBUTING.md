# Contributing

## Pull requests (QA_ARCH / `DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG` §5)

When closing backlog items from `docs/artifacts/QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md` or related `ARCH_DEV_*_TASKS.md`:

1. **Traceability** — In the PR description, link the **ID** (e.g. A7, W1.1) and the **section or line** in the source TASK file or the unified backlog.
2. **Tests** — Run and note `pytest` / `vitest` for **modules you touched** (full suite if feasible). Локально: тестовая БД `dental_booking_test` и `DATABASE_URL_TEST` — см. [`docs/development/TEST_DATABASE.md`](docs/development/TEST_DATABASE.md).
3. **Config** — New env vars: `.env.example` and `docs/MIGRATION_UPGRADE.md` when operators must act.
4. **NFR** — If metrics, alerts, or runbooks change, update `docs/artifacts/NONFUNCTIONAL_AUDIT_NEXT.md` as needed.

GitHub will show `.github/pull_request_template.md` when opening a PR.

## API: частичные обновления (PUT/PATCH)

Один контракт для тел админских **PUT** и **PATCH**:

- В сервис передавайте **`body.model_dump(exclude_unset=True)`** (или эквивалент), чтобы не затирать поля `None` / значения по умолчанию при частичном теле запроса.
- DTO ответа и полная замена ресурса там, где клиент обязан прислать весь объект — по отдельной договорённости; для «полей по желанию» предпочтительны PATCH + `exclude_unset`.

## Supply chain (backend)

JWT: **PyJWT** only (`src/core/security.py`), без `python-jose`. В CI **`pip-audit` без исключений** (`.github/workflows/backend-ci.yml`). После смены зависимостей выполняйте `poetry sync` (или переустановку venv), чтобы не оставались старые транзитивные пакеты в локальном окружении.
