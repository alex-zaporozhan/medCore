# Поставка, эксплуатация, наблюдаемость

## Сборка и запуск

- **Локально:** Postgres и Redis через `docker compose up -d db redis`, миграции `alembic upgrade head`, API `poetry run uvicorn src.main:app --reload` (порты и нюансы — `README.md`, `docs/RUN_SERVICES.md`).
- **Полный стек:** `docker compose up -d` — поднимает миграции, backend, frontend static/nginx по конфигурации compose, Celery worker и beat (см. актуальный список сервисов в `docker-compose.yml`).
- **Образы приложения:** корневой `Dockerfile` (backend), `frontend/Dockerfile` (frontend). Переменные `BACKEND_IMAGE` / `FRONTEND_IMAGE` в `.env` задают теги для pull из реестра.

## CI (GitHub Actions)

Workflow в `.github/workflows/` (актуальный перечень — файловая система репозитория). Типовые группы:

- **Качество backend:** `backend-ci.yml` — установка Poetry, pytest (в т.ч. с поднятием Vite preview для e2e через `scripts/ci/run_pytest_with_e2e_preview.sh`), pip-audit, gitleaks по политике файла.
- **RBAC и entitlements:** `build-and-test-entitlements.yml` — расширенный прогон с Node-сборкой фронта и Playwright для chromium.
- **Критический набор тестов:** `critical-path-gate.yml` — `pytest -m critical_path`, junit и скрипт ворот `scripts/ci/assert_pytest_junit_xml_gate.py`.
- **Релизный gate:** `release-gate.yml` — полный pytest с preview фронта.
- **Безопасность:** `security-trivy.yml` — сканирование файловой системы.
- **Документация:** `documentation-markdown-links.yml`.
- **DR:** `dr-restore-drill.yml` — проверяемая процедура восстановления (см. описание внутри workflow).
- **Образы:** `docker-images-build-verify.yml` — сборка без push и без секретов; `docker-hub-publish.yml` — сборка и push при настроенных секретах Docker Hub (триггеры и фильтр путей — в YAML).

Переменные окружения для CI частично продублированы в workflow (OAuth-заглушки, секреты вебхуков для тестов и т.д.) — при добавлении новых тестов на старт роутов проверяйте необходимость новых env.

## CD: два контура

1. **Один сервер / VPS / демо** — локальная сборка образов и публикация в **Docker Hub** скриптами `scripts/docker_hub_release.ps1` или `scripts/docker_hub_release.sh`; на целевой машине задаются образы в `.env` (см. `documentation/VPS_IMAGE_AND_DATA.md`, `CI_CD.md`).
2. **Корпоративный Jenkins** — `Jenkinsfile`: тесты (параметры), build, push в **GHCR**, деплой по политике команды.

GitHub Actions не заменяют Jenkins автоматически: это отдельная политика организации (описано в `CI_CD.md` и `README.md`).

## Тестовая база и Redis

- Имя БД для pytest обычно `dental_booking_test`; в `tests/conftest.py` защита от случайного запуска против не-тестовой БД (подстрока `test` в имени БД из URL).
- Redis-интеграционные тесты — маркер `redis_integration`, переменная `RUN_REDIS_INTEGRATION_TESTS=1`.

## Наблюдаемость

- **Метрики** — эндпоинт `/metrics`, определения в `src/core/metrics.py` (десятки серий).
- **Правила алертов** — `deploy/prometheus/dental_booking_alerts.yml`.
- **Grafana** — JSON-дашборды и `deploy/grafana/README.md`; в compose может быть профиль observability с Grafana/Prometheus/Alertmanager (см. актуальный `docker-compose.yml`).

## Секреты и конфигурация

- Первичный источник имён переменных — `.env.example`.
- Опциональная загрузка секретов из **AWS Secrets Manager** до инициализации Settings — `src/core/runtime_secrets.py`, переменные `AWS_SECRETS_MANAGER_*` в `.env.example`.
- Редакция продукта (enterprise / box / basic) — `EDITION` на backend и `VITE_EDITION` на frontend (см. комментарии в `.env.example`).

## Полезные операционные ссылки

- Резервное копирование и BCP — ADR-008, runbook-и в `documentation/` / `docs/` по ссылкам из `docs/adr/README.md`.
- Настройка hooks для разработчиков — раздел в корневом `README.md` (`.githooks`, `scripts/dev/pre_push_gate.*`).
