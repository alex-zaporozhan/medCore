# Наблюдаемость (публичная выжимка)

> **Версия:** 2026-04-13  
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

## Публичные заявки «Корпоратив» (`POST /api/v1/platform-leads/`)

Счётчики в `src/core/metrics.py` (экспорт на `GET /metrics`):

| Метрика | Метки | Смысл |
|---------|--------|--------|
| `enterprise_lead_submitted_total` | `lead_source` | Успешно принятая заявка |
| `enterprise_lead_rate_limited_total` | `reason` (`ip` \| `contact`) | Ответ 429 из-за лимита |
| `enterprise_lead_notify_webhook_total` | `result` (`ok` \| `failed`) | Исход POST на опциональный webhook (`ENTERPRISE_LEAD_NOTIFY_WEBHOOK_URL`) |

## Celery (воркер и beat)

Конфигурация приложения: `src/infrastructure/messaging/celery_app.py` (читает `Settings` из `src/core/config.py`). Локально и в Docker команды заданы в корневом **`docker-compose.yml`** (`celery` = worker, `celery-beat` = планировщик).

| Переменная окружения | Смысл |
|----------------------|--------|
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Брокер и backend результатов (часто отдельные DB Redis). |
| `CELERY_TASK_TIME_LIMIT_SECONDS` / `CELERY_TASK_SOFT_TIME_LIMIT_SECONDS` | Жёсткий и мягкий лимит времени на задачу (секунды); soft **строго меньше** hard. |
| `CELERY_TASK_ACKS_LATE` | `true` — подтверждение задачи брокеру **после** успешного завершения; при падении воркера задача может выполниться повторно (**нужна идемпотентность** сценариев). По умолчанию в коде `false` — безопасный старт; для прода включают после ревью задач. |
| `CELERY_TASK_REJECT_ON_WORKER_LOST` | В связке с `acks_late` — вернуть незавершённую задачу в очередь при потере воркера. |
| `CELERY_WORKER_PREFETCH_MULTIPLIER` | Сколько сообщений резервирует воркер на себя; при **`ACKS_LATE=true`** обычно ставят **`1`**, чтобы длинные задачи не «застревали» у одного воркера. |
| `CELERY_WORKER_CANCEL_LONG_RUNNING_TASKS_ON_CONNECTION_LOSS` | По умолчанию `true`: отмена «висящих» задач при обрыве соединения с брокером (Redis). |

**Runbook (кратко):** при росте `duplicate` side effects после включения `ACKS_LATE` — откатить флаг, усилить идемпотентность конкретных задач (`@celery_app.task` с `acks_late=False` для точечных исключений) или снизить prefetch. Мониторинг очереди и DLQ — на стороне OPS (Redis/Celery inspect, логи воркера).

## Omnichannel (исходящие сообщения и admin SSE)

| Метрика | Метки | Смысл |
|---------|--------|--------|
| `omni_outbound_dispatch_failed_total` | `reason` (низкая кардинальность: `no_channel`, `chat_missing`, `telegram_failed`, …) | Адаптер не доставил в провайдер; в `omni_messages.source_metadata` выставлены `delivery_status=FAILED`, `delivery_failure_reason`. |
| `omni_realtime_publish_failed_total` | `event` = `message_created` \| `chat_updated` | Redis publish для admin SSE не удался (мутация в БД всё равно закоммичена). |

**WEB_WIDGET:** при `WEBCHAT_REDIS_FANOUT_ENABLED=false` long-poll помечается как `delivery_status=NOTIFIED_WAITER` и `delivery_semantics=long_poll_same_worker` — не гарантия доставки в браузер при нескольких репликах API. При **`WEBCHAT_REDIS_FANOUT_ENABLED=true`**: `delivery_semantics=redis_fanout`, wake через Redis `PUBLISH` на канал `webchat:notify:{chat_id}`; клиент после wake получает сообщения из БД (OUTBOUND + `delivery_channel=WEB_WIDGET`). На **таймауте** long-poll без сообщения Redis возвращается **пустой список** (без повторной выдачи истории из окна 15s — иначе дубликаты на каждом poll).

| Метрика | Метки | Смысл |
|---------|--------|--------|
| `webchat_redis_fanout_total` | `op`=`publish`\|`subscribe`, `result`=`ok`\|`error` | Путь fan-out / ошибки Redis для webchat. |

**Celery — сверка платежей `local-pending` (P1-4 ops):** задача `payment_reconciliation.reconcile_local_pending` (beat в `celery_app.py`, по умолчанию раз в 600s). Метрика `payment_local_pending_reconcile_total{contour,result}`; алерт `PaymentLocalPendingReconcileErrors` в `deploy/prometheus/dental_booking_alerts.yml`. Переменные: `PAYMENT_LOCAL_PENDING_RECONCILE_*`, в `TESTING=1` reconcile выключен в `Settings`.

**ERP nightly:** метрика `erp_aggregate_nightly_run_total{result}` (`success` \| `partial_failures`) в конце `refresh_all_clinics_erp_aggregates_nightly`; алерт `ERP_NightlyRunPartialFailures`.

## JWT (tenant / founder, legacy dual-read)

| Переменная | Смысл |
|------------|--------|
| `JWT_ISSUER_*` / `JWT_AUDIENCE_*` | Issuer и audience для админских, пациентских и платформенных токенов — см. комментарии в **`.env.example`**. |
| `JWT_LEGACY_ALLOW_MISSING_ISS_AUD` | Пока `true` (по умолчанию), токены без `iss`/`aud` ещё принимаются. После выката задайте **`false`**, чтобы отсечь старые токены. |
| `PLATFORM_FOUNDER_JWT_SECRET` | В `APP_ENV=production` обязателен для маршрутов Основателя; см. код старта и governance в `src/main.py`. |

## Матрица «метрика → алерт» (черновик, QA_ARCH QA-AUDIT-005)

Полный реестр имён — `deploy/prometheus/dental_booking_alerts.yml`; регресс структуры правил — `tests/deploy/test_prometheus_alert_rules_yaml.py`. Ниже — якорные пары для недавних серий ремедиации (дополнять при добавлении `_total` / `_errors`).

| Метрика (серия) | Имя правила в YAML |
|-----------------|-------------------|
| `erp_aggregate_nightly_run_total{result="partial_failures"}` | `ERP_NightlyRunPartialFailures` |
| `payment_local_pending_reconcile_total{result="error"}` | `PaymentLocalPendingReconcileErrors` |
| `webchat_redis_fanout_total{op="publish",result="error"}` | `WebchatRedisFanoutPublishErrors` |

Остальные правила смотреть в YAML (`rg '^      - alert:' deploy/prometheus/dental_booking_alerts.yml`). Цель: при новой бизнес-метрике — строка в `docs/artifacts/METRICS_REGISTRY.md` (если ведётся) и явное решение «нужен ли алерт».

## См. также

- [DEVELOPMENT.md](./DEVELOPMENT.md) — локальный запуск API для проверки `/health` и `/metrics`
- Корневой `docker-compose.yml` — сервисы; в типичном стенде API рядом с БД/Redis; образы приложения для прод/staging — **GHCR** (см. комментарии в compose и **`CI_CD.md`**)
