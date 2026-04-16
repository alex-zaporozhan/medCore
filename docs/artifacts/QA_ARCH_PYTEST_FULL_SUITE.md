# QA_ARCH — полный pytest (parity с CI / gate перед Hub)

Каноничные пошаговые инструкции: **`documentation/DEVELOPMENT.md`** — раздел **«pytest: долгий прогон и зависания»**, подразделы **«Полный pytest с Playwright…»**, **«Повтор только упавших»**, **«Параллельный запуск»**.

Кратко:

| Цель | Действие |
|------|------------|
| Полный `tests/` + Playwright, как **Backend CI** / **release-gate** | `scripts/dev/full_pytest_with_frontend_e2e.ps1` или `full_pytest_with_frontend_e2e.sh` (поднимает Vite preview, задаёт `FRONTEND_E2E_URL`) |
| Догнать только последние падения | `poetry run pytest tests/ --lf -q --tb=short` |
| Избежать deadlocks на `TRUNCATE` | Не запускать **`pytest -n`** на **одну** общую `DATABASE_URL_TEST`; см. шапку **`tests/conftest.py`** |

Workflows: `.github/workflows/backend-ci.yml`, `.github/workflows/release-gate.yml`.

### Vite preview + отдельный uvicorn (Playwright)

Скрипт **`scripts/ci/run_pytest_with_e2e_preview.sh`** поднимает **uvicorn** на `127.0.0.1:8000` и **preview** на `4173`, затем выполняет pytest. В job с **`TESTING=1`** для pytest процесс uvicorn **обязан** стартовать с инициализированным async-движком БД в своём процессе (в скрипте для uvicorn выставляется **`TESTING=0`** на одну команду): при `TESTING=1` движок в `src/infrastructure/database/base.py` откладывается до `init_engine_for_testing()`, которую вызывает только pytest внутри своего процесса, а не отдельный uvicorn — иначе **`GET /api/v1/clinics`** и любые DB-запросы из браузера уходят в **500**.

**Playwright / белый экран:** при падении по API-ошибкам логируйте **URL + фрагмент тела** для ответов **≥500** (см. pillar в **`docs/ROLE_QA_ARCH.md`** § Pillars и `tests/e2e/test_frontend_pages.py`).

**Windows (локально, Git Bash / тот же скрипт):** перед `poetry run pytest` с Playwright задайте **`PYTEST_WIN32_USE_PROACTOR=1`**, иначе sync Playwright падает на **`NotImplementedError`** в `asyncio.create_subprocess_exec` (политика цикла по умолчанию — Selector; см. шапку **`tests/conftest.py`**). В Linux CI переменная не нужна.

## Образы на Docker Hub при красных pytest (QA_ARCH / ops)

Сборка и push образов **не зависят** от pytest: **`.github/workflows/docker-hub-publish.yml`** делает только **`docker build`** (+ push при секретах). Подробности и разрыв с branch protection — **`CI_CD.md`** § «Pytest-gates и публикация образов». Локальный обход gates: **`scripts/docker_hub_release.ps1`** / **`.sh`**.
