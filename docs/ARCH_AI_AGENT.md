## 🧠 ARCH_AI_AGENT — Функциональный автопилот (V2, Phase 1)

> Роли: @ARCH, @BIZ, @LEAD.  
> Цель: спроектировать модуль AI Agent (Function Calling / Tool Use) поверх существующего Omnichannel и домена записей **без постановки задач @DEV**.  
> Входные артефакты: `BUSINESS_LOGIC_CURRENT.md`, `BUSINESS_LOGIC_V2.md`, `TECH_PASSPORT_BACKEND.md`, `FUNCTIONAL_MAP_CURRENT.md`, исходный код:
> - `src/application/services/omnichannel_ai_orchestrator.py`
> - `src/infrastructure/external_apis/ai_client.py`

---

## 1. Цель и рамки модуля

- **Цель:** перевести AI из режима «генерации текста» в режим **функционального агента**, который умеет:
  - понимать намерения клиента в чате;
  - вызывать заранее определённые Python‑инструменты (tools) поверх существующих сервисов;
  - записывать результаты действий в БД и объяснять их клиенту.
- **Рамки Phase 1:**
  - только **чаты и записи** (Omnichannel + Booking/Schedule);
  - базовые инструменты:
    - `get_available_slots`;
    - `create_booking`.
  - без изменений схем БД (используем текущие сущности и сервисы).

---

## 2. Архитектурная схема уровней

Слои и зависимости:

1. **AiClient (инфраструктура)** — уже существует:
   - отвечает за HTTP‑вызовы к LLM‑провайдеру;
   - в V2 должен уметь:
     - принимать список `tools` и, при необходимости, `tool_choice`;
     - возвращать структуру `{ messages, tool_calls? }` (формат зависит от выбранного API, но в архитектуре считаем абстрактным).

2. **Tools Registry (новый слой)** — `src/application/ai/tools_registry.py`:
   - содержит:
     - Python‑функции‑инструменты;
     - Pydantic‑схемы для аргументов/результатов (JSON‑схемы для LLM).
   - **Не** знает о HTTP/Omnichannel — только о доменных сервисах.

3. **OmnichannelAiOrchestrator (application layer)** — расширяется:
   - оркестрирует:
     - диалог (история сообщений, включая сообщения `tool`);
     - выбор и вызов инструментов;
     - повторные вызовы LLM до получения финального текстового ответа.

4. **OmnichannelChatService / BookingService / ScheduleService (application layer)** — остаются источником реальных действий:
   - инструменты используют **только** эти сервисы (и, при необходимости, репозитории) для работы с БД.

5. **Domain / Infrastructure (entities, repos, DB, Redis)** — без изменений в Phase 1.

Зависимости только сверху вниз: Orchestrator → Tools Registry → Services → Repositories.

---

## 3. Слой инструментов: `tools_registry.py`

### 3.1. Общий интерфейс инструмента

Логическая (языковая) модель для @DEV, без привязки к конкретной библиотеке LLM:

- Базовый протокол:

```python
class Tool(BaseModel):
    name: str
    description: str
    args_schema: type[BaseModel]  # Pydantic-модель для аргументов

    async def __call__(self, *, ctx: ToolContext, args: BaseModel) -> BaseModel:
        ...
```

- `ToolContext`:
  - содержит:
    - `clinic_id`;
    - `db: AsyncSession`;
    - `current_contact` / `current_patient` (если есть);
    - ссылки на `BookingService`, `ScheduleService` и др.;
    - настройки клиники (`Clinic` + `ClinicAiSettings`).

### 3.2. Инструмент `get_available_slots`

- **Назначение:** дать LLM список доступных слотов для записи.
- **ArgsSchema (примерное содержание):**
  - `clinic_id: UUID`;
  - `service_id: UUID | None`;
  - `doctor_id: UUID | None`;
  - `date_from: date`;
  - `date_to: date`.
- **Логика:**
  - использует `ScheduleService` и/или существующие репозитории;
  - применяет действующие правила:
    - рабочие часы;
    - отсутствия/блокировки;
    - уже существующие `Booking`.
  - возвращает нормализованный список слотов:
    - `[{ "doctor_id", "service_id", "start", "end", "is_preferred", "meta": {...} }, ...]`.
- **Инварианты:**
  - уважает `clinic_id` из контекста;
  - не создаёт сущности, только читает.

### 3.3. Инструмент `create_booking`

- **Назначение:** создать запись из чата.
- **ArgsSchema:**
  - `clinic_id: UUID`;
  - `patient_id: UUID`;  // или `contact_id` с маппингом на пациента;
  - `doctor_id: UUID`;
  - `service_id: UUID`;
  - `appointment_start: datetime`;
  - опционально: `source` (`"ai_agent"`), `channel` и др.
- **Логика:**
  - вызывает `BookingService` с тем же набором проверок, что и обычный API:
    - слот не занят (уникальный индекс);
    - доктор и услуга доступны для клиники;
    - политика предоплаты (на Phase 1 достаточно флагов: требуется предоплата/нет).
  - при успехе:
    - создаёт `Booking` с пометкой `source="ai_agent"`;
    - возвращает краткий DTO:
      - `booking_id`, `doctor_name`, `service_name`, `start`, `prepayment_required`, `payment_url?`.
  - при конфликте:
    - перехватывает исключение «слот занят»;
    - возвращает структурированную ошибку (`code="slot_conflict"`, список альтернативных слотов при возможности).
- **Инварианты:**
  - все действия в рамках предоставленной `AsyncSession`;
  - при создании:
    - обязательный `session.flush()` и, при необходимости, `session.refresh(booking)` до возврата результата;
  - **никакого** внутреннего `commit` — транзакцией управляет вызывающий код Orchestrator.

---

## 4. Оркестратор: The Loop

### 4.1. Высокоуровневая сигнатура

Логическая функция (архитектурный контракт):

```python
async def run_ai_agent(
    *,
    clinic_id: UUID,
    contact_or_patient: ContactContext,
    messages: list[ChatMessage],
    db: AsyncSession,
) -> AgentResult:
    ...
```

- `messages` — история диалога (user/assistant/tool) в унифицированном формате.
- `AgentResult`:
  - `reply_message: str` — текст ответа клиенту;
  - `tool_events: list[ToolEvent]` — структурированное описание вызванных инструментов;
  - флаги (`requires_handoff_to_human`, `error_code?`).

### 4.2. Цикл обработки

1. **Подготовка:**
   - собрать `ToolContext`;
   - получить активный набор инструментов (на Phase 1: `get_available_slots`, `create_booking`).
2. **Первый вызов LLM:**
   - сформировать prompt из истории и бизнес‑контекста (правила клиники, языковые ограничения, что агент обязан объяснять клиенту свои действия простым языком);
   - вызвать `AiClient` с `tools=[...]`, `tool_choice="auto"`.
3. **Разбор ответа:**
   - если **нет `tool_calls`**:
     - вернуть текст как `reply_message`;
     - `tool_events=[]`.
   - если **есть `tool_calls`**:
     - для каждого `tool_call`:
       - найти инструмент по имени;
       - валидировать и распарсить аргументы через `args_schema`;
       - выполнить инструмент:
         - в одном `AsyncSession`;
         - без `commit`;
       - добавить результат в `messages` как:
         - `role="tool"`, `name=tool_name`, `content=json`.
       - записать `ToolEvent` (для аудита).
4. **Финальный вызов LLM (без tools или c `tool_choice="none"`):**
   - отправить обновлённую историю (`user` + `assistant?` + `tool`‑сообщения);
   - получить чистый текст ответа для клиента (`reply_message`).
5. **Фиксация и возврат:**
   - в вызывающем сервисе:
     - записать новый `OmnichannelMessage` от AI;
     - при необходимости — обновить `Conversation`/`ConversationAiAnalysis`;
     - **после успешной фиксации всех действий** — выполнить `commit` снаружи.

### 4.3. Обработка ошибок

- **Ошибки инструментов (бизнес/валидация):**
  - возвращаются в виде структурированной `ToolError`:
    - `code` (`slot_conflict`, `validation_error`, `prepayment_required`, и т.п.);
    - `message` (для LLM, а не напрямую для пользователя);
    - `user_friendly_hint` (можно использовать как подсказку в промпте).
- **Ошибки LLM/сети:**
  - фиксируются в логах;
  - клиенту отправляется безопасное сообщение:
    - «Сейчас техническая ошибка, администратор свяжется с вами»;
  - опционально создаётся `Task`/запись в `AttentionFeed`.

---

## 5. AiClient и провайдеры

### 5.1. Требования к AiClient

- Должен поддерживать:
  - вызов без tools (старый режим);
  - вызов с tools (Function Calling);
  - возврат:
    - `content` (текст/части);
    - `tool_calls` (масив структур вида `{ id, name, arguments_json }`).
- Не должен:
  - знать о домене или о конкретных инструментах;
  - содержать бизнес‑правила по ПД — только технический уровень.

### 5.2. ПД и выбор провайдера

- Решения по ПД и выбору провайдера зафиксированы в `BUSINESS_LOGIC_V2.md`:
  - `ClinicAiSettings.provider_type` и `allow_personal_data`.
- На уровне `OmnichannelAiOrchestrator` + `AiSanitizer`:
  - если `allow_personal_data=False` или провайдер внешнехостинговый:
    - ФИО, телефоны, email, адреса из истории **маскируются** перед отправкой в LLM;
  - если провайдер «разрешённый в РФ» и есть соответствующие согласия:
    - можно передавать ПД (но по умолчанию — **нет**).

---

## 6. TODO для @ARCH (без DEV‑реализации)

1. **Уточнить границы Phase 1:**
   - какие сценарии агент точно должен уметь закрыть (только «найти слот и создать запись» или ещё «отменить/перенести»);
   - какие ошибки и кейсы важно покрыть в первую очередь.
2. **Специфицировать JSON‑схемы для инструментов:**
   - финальные Pydantic‑модели для `get_available_slots` и `create_booking`;
   - формат ответа, пригодный для UI и для последующих фаз (ERP/CRM).
3. **Проектно описать API оркестратора:**
   - сигнатуру функции уровня application;
   - формат `ChatMessage` и `AgentResult` (Pydantic‑модели).
4. **Прописать политику ретраев и таймаутов:**
   - что делать при тайм‑ауте LLM или tools;
   - сколько попыток допустимо.
5. **Подготовить последующие архитектурные документы:**
   - обеспечить, чтобы CRM/ERP/RBAC могли в будущем добавлять свои инструменты в `tools_registry` без ломки базового протокола.

После завершения этих пунктов @LEAD создаст `DEV_PROMPTS_AI_AGENT.md` с пошаговыми задачами для @DEV («Полный flow», без моков), опираясь на этот документ.

