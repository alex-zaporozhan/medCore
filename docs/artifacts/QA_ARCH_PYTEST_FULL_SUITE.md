# QA_ARCH — полный pytest (parity с CI / gate перед Hub)

Каноничные пошаговые инструкции: **`documentation/DEVELOPMENT.md`** — раздел **«pytest: долгий прогон и зависания»**, подразделы **«Полный pytest с Playwright…»**, **«Повтор только упавших»**, **«Параллельный запуск»**.

Кратко:

| Цель | Действие |
|------|------------|
| Полный `tests/` + Playwright, как **Backend CI** / **release-gate** | `scripts/dev/full_pytest_with_frontend_e2e.ps1` или `full_pytest_with_frontend_e2e.sh` (поднимает Vite preview, задаёт `FRONTEND_E2E_URL`) |
| Догнать только последние падения | `poetry run pytest tests/ --lf -q --tb=short` |
| Избежать deadlocks на `TRUNCATE` | Не запускать **`pytest -n`** на **одну** общую `DATABASE_URL_TEST`; см. шапку **`tests/conftest.py`** |

Workflows: `.github/workflows/backend-ci.yml`, `.github/workflows/release-gate.yml`.

## Образы на Docker Hub при красных pytest (QA_ARCH / ops)

Сборка и push образов **не зависят** от pytest: **`.github/workflows/docker-hub-publish.yml`** делает только **`docker build`** (+ push при секретах). Подробности и разрыв с branch protection — **`CI_CD.md`** § «Pytest-gates и публикация образов». Локальный обход gates: **`scripts/docker_hub_release.ps1`** / **`.sh`**.
