# Слой Infrastructure

> БД: `src/infrastructure/database/`. Сообщения: `src/infrastructure/messaging/`. Realtime: `src/infrastructure/realtime/`. Хранилище: `src/infrastructure/storage/`.

## Как это работает (инфраструктура как рантайм)

1. **Сессия БД:** `get_db()` в `src/infrastructure/database/base.py` открывает `async with AsyncSessionLocal() as session`, `yield session` в FastAPI-зависимость, после выхода из эндпоинта — `commit()` если не было исключения, иначе `rollback()`. Для отчётов `get_db_reporting()` использует `AsyncSessionLocalReporting` (отдельный engine при заданном `DATABASE_REPLICA_URL`) и при необходимости выставляет `SET LOCAL statement_timeout`.
2. **Репозитории:** классы `*RepositoryImpl` принимают `AsyncSession` в конструкторе и выполняют `select`/`update`/`delete` по entity из `domain/entities`. Это основной способ удержать SQL в одном месте; если его обходят, SQL живёт в сервисе.
3. **Redis:** `get_redis()` возвращает async-клиент с пулом; в тестах (`TESTING=1`) создаётся отдельная конфигурация, чтобы не ломать event loop. Закрытие пула — при shutdown приложения.
4. **Celery:** воркер — отдельный процесс, импортирует те же `settings` и модули задач; задачи **не** проходят через FastAPI Depends — они сами создают сессии или вызывают сервисы по внутренним правилам модулей в `tasks/`.
5. **S3:** `MedicalFilesStorage` инкапсулирует boto3-совместимый клиент; health-check дергается с корня приложения `GET /health/s3`.

## Database

| Файл | Назначение |
|------|------------|
| `base.py` | `Base`, фабрики async-сессий (в т.ч. reporting/replica — см. настройки в `core/config.py`). |
| `redis_client.py` | Async Redis pool; `close_redis` на shutdown; ветка `TESTING` для event loop. |
| `*_repo_impl.py` | Реализации репозиториев: `booking`, `clinic`, `conversation`, `chat_message`, `doctor`, `finance`, `inventory`, `lead`, `loyalty`, `omnichannel_chat`, `patient`, `payment`, `payroll`, `rbac`, `service`, `task` (**16** impl-файлов). |

Часть запросов может выполняться напрямую в сервисах через сессию без отдельного класса repo — это не противоречит слою, но усложняет инвентаризацию.

## Messaging (Celery)

- Точка входа приложения воркера: `src/infrastructure/messaging/celery_app.py` (импортируется из compose как `celery -A src.infrastructure.messaging.celery_app`).
- Задачи в `src/infrastructure/messaging/tasks/`: `erp_tasks`, `staff_collab_tasks`, `notifications`, `owner_integrations`, `ai_tasks`, `loyalty_tasks`, `crm_tasks`, `export_tasks`, `backup_tasks`.

Детали очередей и вызовов — [../06_cache_redis_celery.md](../06_cache_redis_celery.md).

## Realtime

- `src/infrastructure/realtime/omni_pubsub.py` и смежные — pub/sub для омниканала (SSE/WebSocket уточнять по роутерам и фронту).

## Storage

- `src/infrastructure/storage/s3_storage.py` — S3-совместимое API для медфайлов; используется в `GET /health/s3`.

## Статус

| Аспект | Статус |
|--------|--------|
| Async SQLAlchemy + Alembic | Реализовано |
| Redis как брокер Celery и кэш | Реализовано |
| Изоляция тенанта в репозиториях | Реализовано на уровне запросов (проверять по каждому repo) |

## Непонятное

- Не все внешние интеграции сосредоточены в одном каталоге; часть HTTP-клиентов может жить в `application/services`.

### Enterprise-аудит (честная оценка)

- **Критические риски:** секреты внешних API в БД/настройках клиники — поверхность для злоупотребления при компрометации админки; требуется политика ротации и аудита (вне объёма этого файла).
- **Средние риски:** 16 файлов `*_repo_impl.py` не покрывают все сущности; обход через сервисы усложняет аудит доступа к данным ([UNRESOLVED U-002](../UNRESOLVED_AND_CONFUSION_LOG.md)).
- **Формально / недоделано:** нет описанного в репо runbook restore из бэкапа (ось «Операции» рубрики).
- **Рекомендуемые доработки:** инвентаризация всех путей записи в БД вне repo_impl.

### Соответствие фактам (проверка)

- Число `*_repo_impl.py` = 16 — по glob в `src/infrastructure/database/`. Паттерн `get_db` — по `base.py`.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** Redis как единая точка для кэша приложения и брокера Celery — при отказе одновременно теряются оба контура.
- **Что усилить:** пул соединений БД и таймауты reporting-сессий мониторить в проде.
- **С нуля:** HA Redis / Sentinel или managed cache; runbooks backup Postgres.
- **БД:** реплика reporting уже есть; lag — метрика/health (см. `main.py`).
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) (§3, §4).
