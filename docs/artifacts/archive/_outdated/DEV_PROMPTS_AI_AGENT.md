## DEV_PROMPTS_AI_AGENT — Реализация функционального AI‑агента

> Роли: @DEV, @ARCH, @QA.  
> Читается после: `BUSINESS_LOGIC_V2.md`, `TECH_PASSPORT_BACKEND.md`, `ARCH_AI_AGENT.md`, `ARCH_CROSSCUT_EVENT_CONTEXT_AI.md`, `FUNCTIONAL_MAP_CURRENT.md`.

---

## 1. Цели реализации

- Добавить в систему **AI‑агента**, который:
  - работает в Omnichannel‑чатах;
  - понимает намерения клиента;
  - вызывает безопасные Python‑инструменты (`get_available_slots`, `create_booking`) через LLM Function Calling;
  - соблюдает ограничения по ПД и работает в рамках `clinic_id`.
- Не ломать существующую логику чатов; новый функционал должен быть:
  - включаемым/отключаемым через настройки клиники (`ClinicAiSettings`);
  - покрыт тестами (в том числе security‑тестами).

---

## 2. Подготовка инфраструктуры (AiConfigService, RequestContext)

### 2.1. Внедрить RequestContext

- **Файлы/слои:**
  - создать `src/core/context.py` с моделью `RequestContext` (см. ARCH_CROSSCUT_EVENT_CONTEXT_AI.md);
  - создать dependency `get_request_context` в `src/api/v1/dependencies.py`.
- **Шаги:**
  1. Определить `RequestContext` с полями:
     - `clinic_id`, `user_id`, `user_type`, `roles`, `permissions`.
  2. В `get_current_admin` и `get_current_patient` добавить функцию построения `RequestContext`.
  3. В Omnichannel/AI‑сервисах использовать `RequestContext` как аргумент (не во всех сервисах сразу, а минимум — в новых AI‑сервисах).

### 2.2. Реализовать AiConfigService

- **Файлы:**
  - новый: `src/application/services/ai_config_service.py`.
- **Шаги:**
  1. Создать `AiProviderConfig` (Pydantic) с полями:
     - `base_url`, `api_key`, `model`, `allow_personal_data`, `provider_type`.
  2. Реализовать `AiConfigService.get_clinic_ai_config(clinic_id)`:
     - читает дефолтные значения из `Settings`;
     - переопределения — из `ClinicAiSettings` (если сущность уже есть; иначе использовать только `Settings`).
  3. Обновить `AiClient`:
     - принимать `AiProviderConfig` вместо raw `settings.*`;
     - не тянуть настройки напрямую.

---

## 3. Слой инструментов (`tools_registry`)

### 3.1. Структура модуля

- **Новый пакет:** `src/application/ai/`.
- **Файлы:**
  - `tools_base.py` — базовые интерфейсы `Tool`, `ToolContext`.
  - `tools_booking.py` — реализация `get_available_slots`, `create_booking`.
  - `tools_registry.py` — реестр инструментов (по имени).

### 3.2. Реализовать ToolContext и базовый Tool

- **ToolContext:**
  - `db: AsyncSession`;
  - `clinic_id: UUID`;
  - `request_context: RequestContext`;
  - сервисы:
    - `booking_service`, `schedule_service`, `patient_service`, и др. при необходимости.
- **Tool:**
  - базовый абстрактный класс:
    - `name: str`, `description: str`, `args_schema: type[BaseModel]`;
    - `async def __call__(self, ctx: ToolContext, args: BaseModel) -> BaseModel | ToolError`.

### 3.3. Инструмент `get_available_slots`

- **TODO:**
  1. Определить `GetAvailableSlotsArgs` (Pydantic):
     - `clinic_id`, `service_id | None`, `doctor_id | None`, `date_from`, `date_to`.
  2. Определить `AvailableSlot` DTO для результата.
  3. Реализовать функцию:
     - внутри использовать `ScheduleService`/репозитории;
     - уважать границы клиники (`ctx.clinic_id` приоритетнее, чем значение из аргументов).
  4. Добавить обработку ошибок:
     - некорректные даты, неизвестные `service_id`/`doctor_id` → ToolError с понятным `code`.

### 3.4. Инструмент `create_booking`

- **TODO:**
  1. Определить `CreateBookingArgs`:
     - `clinic_id`, `patient_id`, `doctor_id`, `service_id`, `appointment_start`, может быть `source="ai_agent"`.
  2. Реализовать:
     - использовать `BookingService` с теми же проверками, что и API;
     - в случае успешного создания:
       - проставлять `source="ai_agent"` или аналогичное поле/мету;
       - вызывать `session.flush()` и `session.refresh(booking)`.
  3. Обработка конфликтов:
     - если слот занят (уникальный индекс или бизнес‑ошибка) — вернуть `ToolError` с `code="slot_conflict"` и, по возможности, список альтернативных слотов (через `get_available_slots`).

### 3.5. Реестр инструментов

- **TODO:**
  1. Создать `get_default_tools_for_clinic(clinic_id: UUID) -> dict[str, Tool]`:
     - на Phase 1 — возвращать `{"get_available_slots": GetAvailableSlotsTool(...), "create_booking": CreateBookingTool(...)}`
     - далее можно расширять (cancel_booking и т.п.).
  2. Обеспечить, чтобы re‑использование сервисов/репозиториев не плодило новые подключения к БД (использовать переданный `AsyncSession` и уже сконфигурированные сервисы).

---

## 4. Orchestrator loop в `OmnichannelAiOrchestrator`

### 4.1. Подготовка интерфейсов

- **TODO:**
  1. Определить DTO:
     - `ChatMessage` (role: `user|assistant|tool|system`, `content`, `name?`);
     - `ToolCall` (id, name, arguments_json);
     - `AgentResult` (reply_message, tool_events, error?).
  2. Расширить `AiClient`:
     - добавить метод `chat_with_tools(messages, tools_schema, tool_choice)`:
       - возвращает текст + struct `tool_calls`.

### 4.2. Реализация цикла

- **TODO:**
  1. В `OmnichannelAiOrchestrator` реализовать функцию `run_ai_agent` (см. ARCH_AI_AGENT.md):
     - собрать историю сообщений по чату/пациенту;
     - получить `AiProviderConfig` через `AiConfigService`;
     - получить нужный набор `Tool` для клиники.
  2. Первый вызов LLM:
     - `AiClient.chat_with_tools(messages, tools_schema=..., tool_choice="auto")`.
  3. Обработка `tool_calls`:
     - для каждого вызова:
       - найти `Tool` по имени;
       - распарсить аргументы в `args_schema`;
       - вызвать `tool(ctx, args)` внутри текущей async‑сессии;
       - добавить в `messages` сообщение `role="tool"`.
  4. Финальный вызов (без tools или `tool_choice="none"`):
     - получить чистый текст ответа;
     - сформировать `AgentResult`.
  5. Интеграция с Omnichannel:
     - записать новый `OmnichannelMessage` от AI (используя существующий сервис);
     - при ошибках вернуть fallback‑ответ и, при необходимости, создать `Task`/событие в `AttentionFeed`.

---

## 5. Интеграция с политикой ПД и настройками клиники

- **TODO:**
  1. При каждом вызове AI:
     - получать `AiProviderConfig` (`allow_personal_data` и `provider_type`);
  2. Обновить/использовать `AiSanitizer`:
     - если `allow_personal_data=False`:
       - обезличивать ФИО/телефоны/email в истории до вызова LLM;
     - если `True`:
       - пропускать полный текст.
  3. В `ClinicAiSettings` убедиться, что есть флаги, соответствующие `BUSINESS_LOGIC_V2`:
     - `provider_type`, `allow_personal_data`, дополнительные настройки (лимиты и режимы).

---

## 6. Логирование и аудит действий AI‑агента

- **TODO:**
  1. Расширить `AgentResult` и/или оркестратор так, чтобы:
     - каждая успешная операция инструмента (`create_booking`, `get_available_slots` и др.) порождала структурированное событие `ToolEvent` с:
       - именем инструмента;
       - аргументами (в безопасном/обезличенном виде);
       - результатом (`success`/`error`, код ошибки).
  2. Сохранить эти события в БД:
     - либо через существующую сущность `ConversationAiAnalysis`;
     - либо через отдельную таблицу для действий AI‑агента.
  3. Для ключевых действий (например, успешное создание записи):
     - создавать сервисное сообщение в Omnichannel‑чате в виде:
       - `AI_ACTION_SUCCESS: Created Booking #id` / `AI_ACTION_ERROR: ...`;
     - это сообщение должно быть видно администратору при просмотре диалога и однозначно объяснять, что сделал агент.
  4. При фатальных ошибках (падение инструмента, сбой LLM):
     - логировать ошибку на уровне backend;
     - по необходимости создавать запись в `AttentionFeed` / задачу, чтобы человек мог проверить ситуацию.

---

## 7. Ограничения цикла Function Calling

- **TODO:**
  1. В оркестраторе ввести:
     - максимальное количество итераций цикла tool‑вызовов на один пользовательский запрос (например, 2–3 шага);
     - таймауты на:
       - суммарное время работы агента;
       - время вызова LLM;
       - время работы инструмента.
  2. При достижении лимитов:
     - прекращать цикл;
     - возвращать пользователю безопасное сообщение («Сейчас техническая пауза, администратор подключится лично»);
     - при необходимости фиксировать это событие в логах/`AttentionFeed`.

---

## 8. Тестирование (unit + интеграционные)

### 8.1. Unit‑тесты tools

- **TODO:**
  - для `get_available_slots`:
    - кейсы: обычный день, полностью занятый день, фильтрация по врачу/услуге;
  - для `create_booking`:
    - успешное создание;
    - конфликт слота (ожидаем `ToolError` с `slot_conflict`);
    - несоответствие клиники/врача/услуги.

### 8.2. Интеграционные тесты Orchestrator

- **TODO:**
  - смоделировать сценарии:
    1. AI отвечает только текстом (без `tool_calls`);
    2. AI вызывает `get_available_slots`, затем выдаёт текст с вариантами;
    3. AI вызывает `create_booking` (успех) → проверка, что запись появилась;
    4. AI пытается создать запись в занятый слот → корректное текстовое объяснение для пользователя.
  - использовать **mock‑реализацию AiClient**, которая возвращает предопределённые `tool_calls` и ответы.

### 8.3. Security‑тесты

- **TODO:**
  - тесты на утечку ПД:
    - убедиться, что при `allow_personal_data=False` в payload, отправляемом в mock‑LLM, нет фамилий/телефонов/email;
  - тесты на ограничения по клинике:
    - AI‑инструменты не могут создавать/читать данные другой клиники (проверка clinic_id).

---

## 9. Флаги включения и деградация

- **TODO:**
  1. Добавить в `ClinicAiSettings` или отдельный флаг:
     - `ai_agent_enabled: bool` (по умолчанию `False` для существующих инсталляций).
  2. В Omnichannel:
     - при выключенном флаге AI‑агент не вызывается; UI ведёт себя как сейчас.
  3. При ошибках провайдера:
     - graceful degradation:
       - лог ошибок;
       - сообщение клиенту в стиле «Сейчас техническая пауза, администратор ответит лично».

---

## 10. Порядок выполнения для @DEV

1. Внедрить `RequestContext` и `AiConfigService`.
2. Реализовать слой инструментов (`tools_base`, `tools_booking`, `tools_registry`).
3. Расширить `AiClient` для поддержки tools.
4. Реализовать основной цикл в `OmnichannelAiOrchestrator` и интеграцию с Omnichannel.
5. Включить/настроить политику ПД через `AiSanitizer` + `AiConfigService`.
6. Реализовать логирование и аудит действий AI‑агента (сохранение ToolEvent, сервисные сообщения в чате, интеграция с AttentionFeed при ошибках).
7. Добавить ограничения на глубину цикла Function Calling и таймауты.
8. Написать unit и интеграционные тесты, обновить security‑тесты.
9. Включить флаги (`ai_agent_enabled`) и проверить деградацию при отключении/ошибках.

