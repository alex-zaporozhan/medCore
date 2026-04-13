# Домен: запись (booking) и цепочка событий

> Сквозной разбор с якорями в коде. In-process шина, не внешний брокер.

## Назначение

Показать путь от HTTP до `BookingService`, публикации `DomainEvent` и подписчиков, без дублирования общего описания слоёв.

## Точка входа HTTP

Файл `src/api/v1/routers/bookings.py`: на эндпоинтах создаётся `BookingService(session)` и вызываются методы сервиса (например строки с `service = BookingService(session)` — см. grep по файлу).

**Контракт смены статуса (LEAD / QA_ARCH):** `PATCH /admin/bookings/{id}` принимает только поле `notes` (`BookingPatchAdmin`, `extra=forbid`). Статус меняется через **`PUT /admin/bookings/{id}/status`** (`set_booking_status_admin`): для `cancelled` / `completed` / `no_show` вызываются те же цепочки, что и на узких маршрутах (`/cancel`, `/complete`, `/mark-no-show`); остальные переходы — `transition_booking_status_admin_light` + FSM. Так расписание, waitlist, уведомления, ERP/outbox не обходятся «тихим» PATCH.

## Сервис и публикация событий

Файл `src/application/services/booking_service.py`:

- Импорт: `from src.application.events.event_bus import get_event_bus`.
- Вызовы: `event_bus = get_event_bus()` и `await event_bus.publish(...)` в нескольких местах файла (создание, отмена, завершение, no-show и т.д.; точные номера строк меняются — поиск по `get_event_bus` и `publish` в файле).

События строятся через фабрики вида `make_booking_*_event` (импорты в том же модуле).

## Регистрация подписчиков при старте

`src/main.py` в `lifespan` до `yield`:

- `register_lead_event_handlers(event_bus)`
- `register_erp_event_handlers(event_bus)`
- `register_loyalty_event_handlers(event_bus)`
- `register_tasks_event_handlers(event_bus)`
- `register_marketing_event_handlers(event_bus)`

## Какие обработчики завязаны на жизненный цикл booking

Пример: `src/application/events/lead_event_handlers.py` — `register_lead_event_handlers` подписывает обработчики на константы `BOOKING_CREATED`, `BOOKING_COMPLETED`, `BOOKING_CANCELLED`, `BOOKING_NO_SHOW`, `PAYMENT_SUCCESS` (и `CONTACT_CREATED` для омни).

`src/application/events/erp_event_handlers.py` — реакция на `BOOKING_COMPLETED`, `PAYMENT_SUCCESS` и связка с ERP/агрегатами (отдельные транзакции через `AsyncSessionLocal` внутри обработчиков — см. файл).

Loyalty, tasks, marketing — см. `register_*` в соответствующих модулях `src/application/events/`.

## Ограничения (важно для Enterprise-оценки)

- **EventBus** — процессный, в памяти одного воркера API (`src/application/events/event_bus.py`): при нескольких репликах uvicorn события **не** дублируются между процессами; тяжёлая асинхронная работа — через **Celery** ([`../06_cache_redis_celery.md`](../06_cache_redis_celery.md)).
- **Outbox (ADR-009, фаза 2):** для **`PaymentSuccess`** на контуре A — как раньше (`get_session_payment_webhook` + Celery). Для жизненного цикла **booking** (`BookingCreated`, `BookingCancelled`, `BookingCompleted`, `BookingNoShow`) при `DOMAIN_OUTBOX_BOOKING_EVENTS_ENABLED=true` — запись в `domain_outbox` в той же транзакции, что изменение `bookings`; drain после `commit` на маршрутах `bookings` через `get_session_booking_domain_outbox` и Celery `domain_outbox.dispatch_pending`. **`BookingCompleted`** из `BookingCompletionService`: enqueue до внутреннего `commit`, drain — тем же dependency на HTTP-маршрутах завершения визита. Тесты redelivery/dedup (booking + контур B): `tests/application/test_domain_outbox_platform_provision.py`. Отключение флага = прежний in-process `EventBus` для этих событий.
- Обработчик при ошибке не роняет остальные, но инцидент — счётчик `domain_event_handler_failures_total` и лог в `EventBus.publish`.

## Статус документа

- Якоря: статическое чтение кода.
- Рантайм-трасса одного сценария end-to-end: не фиксируется здесь.

### Enterprise-аудит (честная оценка)

- **Критические риски:** цепочка booking→downstream зависит от порядка обработчиков и отдельных транзакций в хендлерах; при масштабировании API — риск рассинхрона без outbox ([INDEX.md](../INDEX.md)).
- **Средние риски:** нет единого документа со всеми именами `DomainEvent` и подписчиками — только обход модулей `events/`.
- **Формально / недоделано:** интеграционные тесты «один HTTP → N побочных эффектов» могут быть неполными.
- **Рекомендуемые доработки:** тесты на идемпотентность хендлеров для повторной доставки события.

### Соответствие фактам (проверка)

- `bookings.py`, `booking_service.py`, `lead_event_handlers.register_*`, `main.py` lifespan — статическое чтение.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** после `publish` хендлеры выполняют работу в **других** транзакциях — «booking изменён, CRM нет» возможен при сбое.
- **Что усилить:** интеграционные тесты «один вызов API → все ожидаемые побочные эффекты в БД» с учётом асинхронности.
- **С нуля:** outbox вместо прямого вызова хендлеров ([U-007](../UNRESOLVED_AND_CONFUSION_LOG.md)).
- **БД:** согласованность ERP/лидов с booking — проверять под нагрузкой и при ретраях.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) §2.1.
