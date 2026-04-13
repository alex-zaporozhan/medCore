# Кэш, Redis, Celery

## Как это работает (два потребителя Redis)

1. **Приложение API:** использует `REDIS_URL` (типично db `0` на инстансе) через `get_redis()` — блокировки, OAuth state, pub/sub омниканала, коды auth и т.д. Это **не** тот же логический канал, что очередь Celery, хотя физически может быть один сервер Redis.
2. **Celery:** брокер и result backend указывают на другие номера DB на том же Redis (`CELERY_BROKER_URL` db `1`, `CELERY_RESULT_BACKEND` db `2` в `docker-compose.yml`), чтобы не смешивать ключи приложения с ключами брокера.
3. **Воркер:** процесс `celery worker` импортирует `celery_app` и регистрирует задачи из списка `include`. Вызов `.delay()` / `apply_async()` из API попадает в очередь; выполнение — вне HTTP-транзакции.
4. **Задачи и БД:** синхронные функции `@celery_app.task` вызывают локальный хелпер `_run_async(coro)` (см. `src/infrastructure/messaging/tasks/notifications.py`): новый event loop, `run_until_complete` для корутины, внутри — `async with AsyncSessionLocal()` и работа с БД. Это **отдельные** транзакции от HTTP-запроса FastAPI.
5. **Beat:** процесс `celery beat` читает `beat_schedule` в `celery_app.py` и ставит периодические задачи брокеру по расписанию.

## Redis (приложение)

- Клиент: `src/infrastructure/database/redis_client.py` — `get_redis()`, `close_redis()`; пул и `TESTING` описаны в файле. URL: `settings.redis_url` (`src/core/config.py`).
- Закрытие при остановке: `close_redis` из lifespan в `src/main.py`.

Примеры использования в коде (не исчерпывающий список):

- `src/application/services/auth_service.py` — коды и сессии в Redis.
- `src/api/v1/routers/auth.py` — OAuth state, setex/get/exists/delete.
- `src/application/services/omnichannel_ai_orchestrator.py` — распределённый lock (`SET` с `nx`, TTL).
- `src/infrastructure/realtime/omni_pubsub.py` — publish.
- `src/api/v1/routers/admin_omni_chat.py` — pubsub для SSE/стриминга (см. файл).

Compose: сервис `redis`, переменные `REDIS_URL` у `backend`, `celery`, `celery-beat` — `docker-compose.yml`.

## Celery

- Приложение: `src/infrastructure/messaging/celery_app.py` — `celery_app`, broker `settings.celery_broker_url`, backend `settings.celery_result_backend` (в compose отдельные DB index 1 и 2 на том же Redis).
- Подключённые модули задач: `notifications`, `ai_tasks`, `loyalty_tasks`, `owner_integrations`, `export_tasks`, `backup_tasks`, `erp_tasks`, `crm_tasks`, `staff_collab_tasks` (список в `include=[...]` в том же файле).
- Расписание beat: в `celery_app.conf.update` — напоминания каждые 15 мин, ежедневные/ежечасные AI и loyalty задачи, owner brief/summary по crontab UTC, очистка экспортов, ночной refresh ERP aggregates, parity sample, напоминания staff calendar каждые 5 мин.

Команды контейнеров: `docker-compose.yml` — `celery` worker и `celery-beat` с `-A src.infrastructure.messaging.celery_app`.

## Статус

- Инфра в compose: реализовано.
- Сценарии «задача реально отрабатывает в проде»: не проверялось в этом документе; смотреть логи worker и метрики при наличии.

## Непонятное

Полный граф «кто ставит в очередь» — поиск по `.delay(` и `apply_async` в `src/`.

### Enterprise-аудит (честная оценка)

- **Критические риски:** при потере Redis теряются и кэш приложения, и брокер Celery — нужен runbook HA/backup ([UNRESOLVED U-003](./UNRESOLVED_AND_CONFUSION_LOG.md) про покрытие вызовов задач).
- **Средние риски:** отсутствие явного DLQ в коде репозитория для всех задач (проверять по задачам).
- **Формально / недоделано:** «beat работает» в проде не подтверждается этим документом.
- **Рекомендуемые доработки:** метрики очередей и возраста задач; алерты на рост backlog.

### Соответствие фактам (проверка)

- `redis_client.py`, `celery_app.py`, `docker-compose.yml`, `_run_async` в tasks — статическое чтение.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** потеря Redis блокирует и кэш приложения, и очередь; нет описанного в каталоге HA-runbook.
- **Что усилить:** метрики глубины очереди, DLQ для упавших задач, алерты ([U-003](./UNRESOLVED_AND_CONFUSION_LOG.md)).
- **С нуля:** отдельный брокер (RabbitMQ) при росте требований — ADR.
- **БД:** Celery не заменяет транзакционную согласованность с API ([FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) §2.1).
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) (§4).
