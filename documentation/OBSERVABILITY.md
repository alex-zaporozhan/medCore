# Наблюдаемость (публичная выжимка)

> **Версия:** 2026-04-08  
> **Источник в коде:** `src/main.py`, `src/core/metrics.py`, каталоги `deploy/prometheus/`, `deploy/grafana/`.

## CI/CD и реестр образов (согласовано с политикой репозитория)

- **Релиз приложения (сборка образов, push, деплой):** основной контур — **Jenkins**, корневой **`Jenkinsfile`**. Не путать с GitHub Actions: workflow в `.github/workflows/` — вспомогательные проверки PR, они **не** заменяют Jenkins для публикации образов и прод-деплоя.
- **Реестр контейнеров:** **GitHub Container Registry (`ghcr.io`)**. **Docker Hub** для этого потока **не обязателен**; платный тариф Docker Hub **не предполагается**.
- Подробности: корневые **`CI_CD.md`**, **`AGENTS.md`**, **`README.md`** (раздел CI/CD).

Наблюдаемость в проде (Prometheus/Grafana/алерты) разворачивается **вместе с** инфраструктурой, которую вы гоните через Jenkins/compose на своих хостах; пути к артефактам ниже — то, что лежит в git.

## Эндпоинты API

| Путь | Назначение |
|------|------------|
| `GET /health` | Быстрая проверка живости процесса. |
| `GET /health/replica` | Проверка реплики БД (если настроена), пороги лага — переменные окружения (см. `.env.example`). |
| `GET /health/s3` | Проверка доступности S3-совместимого хранилища (медиа). |
| `GET /metrics` | Экспорт метрик в формате **Prometheus** (`render_prometheus_metrics`). |

Запросы к `/health`, `/health/replica` и `/metrics` не учитываются в middleware длительности HTTP так же, как остальной трафик (см. `prometheus_http_duration_middleware` в `main.py`).

## Trace ID

В ответах API и логах может использоваться **`X-Trace-Id`** (middleware); детали формата ошибок — `documentation/PRODUCT_KNOWLEDGE_BASE.md` §6.

## Артефакты в репозитории

- **`deploy/prometheus/dental_booking_alerts.yml`** — правила алертов Prometheus. У каждого правила с `alert:` заданы **`labels.owner`**, **`labels.severity`** и **`annotations.runbook_url`** (политика Phase 4 / QA_ARCH); регрессия ловится тестом `tests/deploy/test_prometheus_alert_rules_yaml.py`.
- **`deploy/grafana/dashboards/*.json`** — дашборды Grafana (импорт с выбором datasource в вашей среде).

Пороги и SLO согласуются с эксплуатацией; ориентиры — комментарии в YAML и текстовые панели в JSON.

## См. также

- [DEVELOPMENT.md](./DEVELOPMENT.md) — локальный запуск API для проверки `/health` и `/metrics`
- Корневой `docker-compose.yml` — сервисы; в типичном стенде API рядом с БД/Redis; образы приложения для прод/staging — **GHCR** (см. комментарии в compose и **`CI_CD.md`**)
