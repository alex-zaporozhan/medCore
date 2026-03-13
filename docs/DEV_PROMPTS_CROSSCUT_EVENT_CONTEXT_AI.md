## DEV_PROMPTS_CROSSCUT_EVENT_CONTEXT_AI — Events, RequestContext, AI‑config

> Роли: @DEV, @ARCH, @QA.  
> Читается после: `ARCH_CROSSCUT_EVENT_CONTEXT_AI.md`, `BUSINESS_LOGIC_V2.md`, `TECH_PASSPORT_BACKEND.md`, `FUNCTIONAL_MAP_CURRENT.md`.

---

## 1. Цели реализации

- Ввести **единый поперечный слой**, который используют все модули V2 (AI Agent, CRM, ERP, RBAC/Tasks, Loyalty, Paperless, Attribution):
  - in‑process **EventBus + DomainEvent** для доменных событий;
  - типизированный **RequestContext** для новых сервисов;
  - централизованный **AiConfigService** и политика работы с ПД.
- Обеспечить, чтобы:
  - CRM/ERP/Loyalty/Tasks/Attribution не «подписывались» напрямую на HTTP‑контроллеры;
  - выбор AI‑провайдера и режим работы с ПД был сконцентрирован в одном месте;
  - новые модули принимали `clinic_id` и полномочия пользователя явным контрактом.

---

## 2. EventBus и доменные события

### 2.1. Базовые типы и каркас EventBus

- **Файлы:**
  - `src/application/events/domain_event.py`
  - `src/application/events/event_bus.py`

- **TODO:**
  1. Определить `DomainEvent` (Pydantic‑модель, см. ARCH):
     - поля минимум:
       - `name: str`
       - `payload: dict`
  2. Реализовать in‑process `EventBus`:
     - методы:
       - `subscribe(name: str, handler: Callable[[DomainEvent], Awaitable[None]]) -> None`
       - `async publish(event: DomainEvent) -> None`
     - хранить подписчиков в памяти (`dict[name, list[handler]]`).
  3. Продумать способ доступа к `EventBus`:
     - простой singleton в модуле `event_bus.py` либо фабрика в `src/core/deps.py`;
     - важно, чтобы в тестах можно было сбрасывать/подменять подписчиков.

### 2.2. Стандартные события V2

- **TODO:**
  1. Описать и задокументировать набор базовых событий (см. ARCH):
     - `BookingCreated`
     - `BookingCompleted`
     - `PaymentSuccess`
     - `ContactCreated`
  2. Создать helper‑функции/фабрики:
     - `make_booking_created_event(booking: Booking) -> DomainEvent`
     - `make_booking_completed_event(booking: Booking) -> DomainEvent`
     - и т.п.
  3. В существующих application‑сервисах:
     - в местах, где **уже** создаётся/завершается `Booking`, успешный `Payment` или `OmnichannelContact`:
       - добавить публикацию соответствующего события через `EventBus.publish(...)`.
  4. Гарантировать, что публикация происходит:
     - внутри активной async‑сессии;
     - но после успешного выполнения бизнес‑логики (до внешнего `commit`), чтобы подписчики могли использовать те же сущности.

### 2.3. Базовые подписчики (сквозное поведение)

- **TODO:**
  1. Создать заготовки подписчиков в отдельных модулях (минимум логирующие):
     - `lead_event_handlers.py` (CRM);
     - `erp_event_handlers.py` (финансы/склад);
     - `loyalty_event_handlers.py`;
     - `tasks_event_handlers.py`;
     - `marketing_attribution_event_handlers.py`.
  2. На первом этапе:
     - подписчики могут просто логировать получение событий + выполнять минимальные действия (если соответствующий модуль уже реализован);
     - дальнейшая бизнес‑логика (создание `LeadCard`, ERP‑узел, задачи и т.п.) реализуется в рамках соответствующих DEV‑промптов, используя этот EventBus.

---

## 3. RequestContext

### 3.1. Тип и зависимость FastAPI

- **Файлы:**
  - `src/core/context.py`
  - `src/api/v1/dependencies.py`

- **TODO:**
  1. Определить `RequestContext` (см. ARCH):
     - `clinic_id: UUID | None`
     - `user_id: UUID | None`
     - `user_type: Literal["admin", "doctor", "patient", "system"] | None`
     - `roles: set[str]`
     - `permissions: set[str]`
  2. Реализовать dependency `get_request_context`:
     - использовать существующие зависимости `get_current_admin` / `get_current_patient` / системные сервисы;
     - подгружать роли/права через `rbac_service` (см. `DEV_PROMPTS_RBAC_AND_TASKS.md`);
     - формировать `RequestContext`, который затем передаётся в новые сервисы.

### 3.2. Использование в новых модулях

- **TODO:**
  1. Обновить сигнатуры новых сервисов V2 (AI Agent, ERP, CRM, Tasks, Loyalty, Attribution), как минимум:
     - добавить аргумент `ctx: RequestContext` либо хранить его в контексте объекта‑сервиса.
  2. В местах, где сейчас явно прокидывается только `clinic_id`:
     - по возможности заменить на передачу `RequestContext` (без переписывания всего legacy).

---

## 4. AiConfigService и политика ПД

### 4.1. AiConfigService

- **Файлы:**
  - `src/application/services/ai_config_service.py`

- **TODO (если ещё не сделано в рамках `DEV_PROMPTS_AI_AGENT.md`):**
  1. Реализовать `AiProviderConfig`:
     - `base_url: str`
     - `api_key: str`
     - `model: str`
     - `allow_personal_data: bool`
     - `provider_type: Literal["external", "ru_compliant", "on_premise"]`
  2. Реализовать `AiConfigService.get_clinic_ai_config(clinic_id: UUID) -> AiProviderConfig`:
     - источники: `Settings` (дефолты) + `ClinicAiSettings` (переопределения).
  3. Обновить `AiClient`:
     - принимать `AiProviderConfig` вместо прямого чтения `settings`.

### 4.2. Интеграция с AiSanitizer и политикой ПД

- **TODO:**
  1. В местах вызова AI (Omnichannel AI Agent, AI‑отчёты, AI Task Generator):
     - перед вызовом `AiClient` получать `AiProviderConfig`;
     - прокидывать флаг `allow_personal_data` в `AiSanitizer`.
  2. В `AiSanitizer`:
     - если `allow_personal_data=False`:
       - маскировать ФИО, телефоны, email и др. ПДн в истории диалогов и текстах;
     - если `True`:
       - пропускать текст как есть (при условии наличия согласий и корректной настройки клиники).

---

## 5. Тестирование

### 5.1. EventBus и доменные события

- **TODO:**
  - Unit‑тесты:
    - подписка/отписка и публикация событий в `EventBus`;
    - корректный вызов нескольких подписчиков для одного события.
  - Интеграционные тесты:
    - имитация создания/завершения `Booking`, успешного `Payment`, создания `OmnichannelContact`:
      - проверка, что публикуются соответствующие `DomainEvent`;
      - базовые подписчики получают событие (хотя бы лог или простое изменение в тестовом репозитории).

### 5.2. RequestContext

- **TODO:**
  - протестировать формирование `RequestContext` для:
    - админа с разными ролями/permissions;
    - врача/пациента;
    - системных задач (user_type="system").
  - убедиться, что новые сервисы корректно используют `clinic_id` и права из `RequestContext`.

### 5.3. AiConfigService и ПД

- **TODO:**
  - Unit‑тесты:
    - комбинации настроек `Settings` и `ClinicAiSettings` → ожидаемый `AiProviderConfig`;
  - Security‑тесты:
    - сценарии, где `allow_personal_data=False`:
      - проверка, что в payload, передаваемом mock‑LLM, отсутствуют ПДн.

---

## 6. Порядок выполнения для @DEV

1. Реализовать `DomainEvent` и `EventBus`, добавить публикацию базовых событий и заготовки подписчиков.
2. Ввести `RequestContext` и использовать его минимум в новых сервисах V2 (AI Agent, ERP, CRM, Tasks, Loyalty, Attribution).
3. Реализовать/доработать `AiConfigService` и интеграцию с `AiClient` и `AiSanitizer`.
4. Пройти unit‑ и интеграционные тесты для EventBus, RequestContext и AiConfigService (включая сценарии защиты ПД).

