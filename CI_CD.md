# CI/CD в этом репозитории

## VPS и Docker Hub (практический путь по умолчанию для демо/одного сервера)

- **Рекомендуется:** собрать образы **локально**, убедиться что `docker build` прошёл, затем **`docker login`** (пароль или token только в запросе в терминале) и **`docker push`**.
- Скрипты из корня репозитория:
  - Windows: **`scripts/docker_hub_release.ps1`** (параметр `-Tag`, опционально `$env:DOCKERHUB_USERNAME`).
  - Linux/macOS: **`scripts/docker_hub_release.sh`** (`DOCKERHUB_USERNAME=... ./scripts/docker_hub_release.sh <tag>`).
- На VPS в `.env` задайте, например: `BACKEND_IMAGE=docker.io/<user>/dental-booking-backend:<tag>` и то же для frontend (см. **`documentation/VPS_IMAGE_AND_DATA.md`**).
- **GitHub Actions** с push на Hub возможны только с секретами **`DOCKERHUB_USERNAME`** / **`DOCKERHUB_TOKEN`** в настройках репозитория (**Settings → Secrets and variables → Actions**). Workflow **`.github/workflows/docker-hub-publish.yml`**: **workflow_dispatch** (поле тега, по умолчанию `main`), при merge/push в **`main`/`master`** (образы с тегом **`main`**, с фильтром путей — см. YAML), или при push **git-тега `v*`** (тег образа = имя git-тега). Сначала **два `docker build` без логина**, затем login и push. Без секретов job завершится ошибкой — используйте локальные **`scripts/docker_hub_release.*`**.

### Pytest-gates и публикация образов (частая путаница)

- **`.github/workflows/docker-hub-publish.yml`** и **`.github/workflows/docker-images-build-verify.yml` выполняют только `docker build` (и при наличии секретов — push)**. Они **не вызывают pytest** и **не читают** production-данные.
- **Красные проверки** обычно идут из других workflow: **`backend-ci.yml`**, **`build-and-test-entitlements.yml`**, **`critical-path-gate.yml`**, **`release-gate.yml`** — там Postgres/Redis из **services**, тестовая БД **пустая**, данные создают фикстуры (`tests/conftest.py`). Типичный CI **не требует** «лайв» продакшн-БД или реальных внешних API; если локально всё падает, чаще нет **`DATABASE_URL_TEST`**, Redis, **`FRONTEND_E2E_URL`** для Playwright или конфликт пула с запущенным API (см. **`documentation/DEVELOPMENT.md`**).
- **Обойти только «образный» шаг, не трогая тесты:**  
  1) **Локально:** **`scripts/docker_hub_release.ps1`** / **`.sh`** — сборка + push без pytest.  
  2) **В GitHub:** **Actions → Docker Hub publish → Run workflow** (`workflow_dispatch`) на нужной ветке/теге при настроенных секретах — job соберёт образы даже если последний **`backend-ci`** на PR был красным (это **отдельный** workflow).  
  3) Если в **Branch protection** в настройках репозитория обязательны именно **`backend-ci`** / **`critical-path-gate`**, merge в `main` без зелёных checks не пройдёт — это политика org, не YAML образов; тогда либо чинить тесты/инфру, либо временно ослабить required checks (owner), либо пушить образы с **ручного dispatch**, не ожидая merge.
- **Не рекомендуется:** общий «allowlist» тестов в файле, чтобы массово отключать gate — это скрывает регрессии. Допустимо точечно: **`@pytest.mark.skip`** / **`xfail`** с ссылкой на задачу, моки внешних API, отдельный маркер **`integration`** и отдельный workflow без него — по решению команды.
- **Локально `pytest -m critical_path`:** если выбран smoke Playwright и **`FRONTEND_E2E_URL`** не задан, тесты сами поднимают **`vite preview`** на **127.0.0.1:4173** (при необходимости выполняют **`npm run build`** в `frontend/`). Отключить автозапуск: **`PYTEST_DISABLE_VITE_AUTOSTART=1`**.

## Проверка Dockerfile без пуша и без секретов

- **`.github/workflows/docker-images-build-verify.yml`** — только `docker build` (`push: false`), в т.ч. для форков.

---

## Корпоративный контур: Jenkins и GHCR

- Для команд с **Jenkins**: сборка, публикация и деплой на VM — корневой **`Jenkinsfile`**; образы в **GitHub Container Registry (`ghcr.io`)** — см. переменные `GHCR_*` / `BACKEND_IMAGE_REPO` / `FRONTEND_IMAGE_REPO`.
- Учётные данные реестра и SSH задаются **в Jenkins**, не в git.
- **GitHub Actions** в **`.github/workflows/`** — дополнительные проверки PR (тесты, линки, Trivy и т.д.), **не заменяют** Jenkins, если у вас настроен этот пайплайн.

## Локально

- Pre-commit / pre-push (`.githooks`) — быстрый контроль перед push.

### Зависимости: устаревшие пакеты и pip-audit (вне CI)

Скрипт **`scripts/dev/check_dependency_updates.py`** — ручная сводка для ревью апдейтов; **не дублирует** обязательный шаг **`pip-audit`** в **`.github/workflows/backend-ci.yml`**, но удобен перед bump’ом версий.

- **`poetry run python scripts/dev/check_dependency_updates.py`** — печатает `poetry show --outdated` и при наличии **`npm`** в PATH — `npm outdated` в каталоге **`frontend/`**.
- **`poetry run python scripts/dev/check_dependency_updates.py --audit`** — то же плюс **`pip-audit`** в окружении Poetry; **ненулевой код выхода**, если найдены известные уязвимости (как в CI). Перед аудитом в CI обновляют **pip**, **setuptools** и **msgpack** в venv (они входят в отчёт `pip-audit`, хотя не в `pyproject.toml`; **msgpack** тянется самим `pip-audit`).
- **Windows:** если `npm` не находится или shim не запускается из `subprocess`, блок frontend помечается как пропущенный; для полной картины по фронту запустите скрипт из среды, где **`npm`** в PATH, или смотрите **`npm outdated`** вручную в **`frontend/`**.

Полный **`poetry run pytest tests/`** как в workflow (Postgres + Redis, **`DATABASE_URL_TEST`**, при необходимости **`RUN_REDIS_INTEGRATION_TESTS=1`**, для e2e — **`FRONTEND_E2E_URL`** / автоподъём preview) — см. **`documentation/DEVELOPMENT.md`**. Отдельная тестовая БД с **`alembic upgrade head`** ближе к CI, чем «живая» dev-БД с устаревшими или частичными данными: иначе сервисные тесты могут падать на бизнес-инвариантах (например, нет дефолтной кассы у клиники).

- **`DATABASE_URL` / `DATABASE_URL_TEST`:** в CI задают обе или только **`DATABASE_URL`** — тогда pytest подставляет имя БД **`dental_booking_test`** (тот же хост и пароль). Рекомендуемое имя — **`dental_booking_test`**; для очистки таблиц (`TRUNCATE`) в `tests/conftest.py` имя БД из URL должно **содержать подстроку `test`** — так снижается риск случайного запуска против не-тестовой БД.

Подробнее для разработчиков: **`README.md`** (раздел CI), **`CONTRIBUTING.md`**, данные для VPS и БД — **`documentation/VPS_IMAGE_AND_DATA.md`**.
