# Слой Application

Сервисы: `src/application/services/` (около 74 файлов). DTO: `src/application/dto/`. События: `src/application/events/`.

## Назначение

Оркестрация: репозитории, транзакции, внешние API, доменные события. In-process **EventBus** в `src/application/events/event_bus.py` (подписки по имени события, изоляция ошибок обработчиков, метрика `domain_event_handler_failures_total`). Регистрация обработчиков — в `src/main.py` lifespan.

## Как это работает (логика слоя)

1. **Вход из API:** роутер создаёт сервис, передавая **`AsyncSession`** (и иногда `RequestContext` или отдельные id). Сервис **не** открывает сессию сам — граница транзакции = HTTP-запрос (кроме явных `async with session.begin()` внутри сервиса, если есть).
2. **Доступ к данным:** предпочтительно через `*RepositoryImpl` из `src/infrastructure/database/`; многие сервисы принимают интерфейс репозитория в конструкторе. Альтернатива — прямой `session.execute(select(...))` в теле сервиса (тот же session, те же модели из `domain/entities`).
3. **События:** после изменения сущности сервис вызывает `event_bus = get_event_bus()` и `await event_bus.publish(DomainEvent(...))`. Пример цепочки: `booking_service` публикует события завершения/отмены; подписчики зарегистрированы в `register_erp_event_handlers`, `register_loyalty_event_handlers` и т.д. Обработчики **асинхронные**, выполняются **последовательно** по списку подписчиков; исключение в одном обработчике **не** отменяет остальные, но увеличивает `domain_event_handler_failures_total` и логируется (`event_bus.py`).
4. **DTO:** входные/выходные структуры для HTTP описываются в `application/dto/` и в схемах роутеров; сервисы работают с entity и DTO, маппинг — явные функции или конструкторы Pydantic.
5. **Внешние системы:** HTTP к платёжкам, AI, SMS и т.д. обычно инкапсулированы в сервисах (`ai_client_factory`, `payment_service`, …) с настройками из `src/core/config.py`.

## Кластеры сервисов (по именам файлов)

- **Запись и очереди:** `booking_service`, `booking_status_service`, `booking_completion_service`, `schedule_service`, `waitlist_service`, `recall_service`.
- **Платежи и финансы:** `payment_service`, `finance_service`, `clinic_payment_gateway_service`, `wallet_service`.
- **CRM и лиды:** `lead_service`, `lead_lifecycle_service`, `lead_stage_state_machine`, `lead_stage_semantics_service`, `crm_attribution_sync_service`.
- **Омниканал:** `omnichannel_chat_service`, `omnichannel_outbound_dispatcher`, `omnichannel_ai_orchestrator`, `chat_service`, `integration_gateway_service`, связанные policy/storage.
- **Задачи:** `task_service`, `ai_task_manager_service`, `ai_task_settings_service`.
- **Staff:** `staff_directory_service`, `staff_directory_cache`, `staff_collaboration_service`.
- **ERP и отчёты:** модули с префиксом `erp_`, `report_service`, `erp_report_cache`, `erp_aggregate_service`, refresh/audit.
- **Лояльность:** `loyalty_service`, `loyalty_campaign_engine`, `erp_loyalty_service`, `family_link_service`.
- **Формы:** `forms_service`, `form_status_service`.
- **RBAC:** `rbac_service`, `rbac_user_roles_write`.
- **AI:** `ai_client_factory`, `chat_ai_service`, `conversation_analysis_service`, `ai_config_service`, `clinic_ai_settings_service`.
- **Прочее:** `notification_service`, `messaging_service`, `auth_service`, `oauth_auth_service`, `csv_import_service`, `slug_service`, …

## DTO

`src/application/dto/` — Pydantic-схемы для границы API/сервис.

## Статус

- Логика в services: да.
- Покрытие тестами: частичное; см. `tests/services/` и `tests/api/`.

## Непонятное

Граф вызовов сервис-сервис не построен; вход обычно из роутера в один главный сервис.

### Enterprise-аудит (честная оценка)

- **Критические риски:** обработчики событий открывают **собственные** `AsyncSessionLocal` транзакции (см. `lead_event_handlers.py`) — при сбое возможны частично применённые цепочки; нужны явные идемпотентные ключи и компенсации на уровне продукта.
- **Средние риски:** отсутствие единого каркаса saga/outbox для критичных цепочек booking→ERP→CRM ([domains/booking_event_chain.md](../domains/booking_event_chain.md)).
- **Формально / недоделано:** EventBus in-process — ось «Надёжность» в рубрике максимум уровень 1 при горизонтальном масштабировании API.
- **Рекомендуемые доработки:** outbox таблица или публикация в брокер для событий, влияющих на деньги и отчётность.

### Соответствие фактам (проверка)

- `get_event_bus`, `publish` в `booking_service.py`; регистрация хендлеров в `main.py`; отдельные сессии в хендлерах — по чтению `src/application/events/lead_event_handlers.py`.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** коммит HTTP-транзакции до завершения побочных эффектов в хендлерах с отдельными сессиями — см. [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) §2.1; [U-007](../UNRESOLVED_AND_CONFUSION_LOG.md).
- **Что усилить:** явные идемпотентные ключи в хендлерах для событий денег и CRM.
- **С нуля:** outbox + воркер ([U-007](../UNRESOLVED_AND_CONFUSION_LOG.md)).
- **БД:** outbox как таблица в той же БД — идея в §3 фундаментального документа.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md).
