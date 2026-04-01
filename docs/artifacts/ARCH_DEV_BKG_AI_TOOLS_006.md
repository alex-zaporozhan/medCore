## ARCH_DEV_BKG_AI_TOOLS_006 — AI‑tools для Booking/Schedule

> DEV_PROMPT_BKG_AI_TOOLS_006 — «AI‑tools для Booking/Schedule (BKG‑6, OMNI‑1/3)»

---

## 1. Контекст и существующее состояние

### 1.1. Booking/Schedule и AI‑слой

По `ARCH_BOOKING_NEXT.md` и `ARCH_DECISIONS_NEXT.md`:

- Booking‑домен уже реализует:
  - расписание (`DoctorWorkingHours`, `DoctorAbsence`, `ServiceDoctor`);
  - создание/перенос/отмену записей (`BookingService`, `ScheduleService`);
  - предоплату/платежи;
  - лист ожидания.
- Для vNext архитектурно заложен принцип:
  - **Injectability для AI‑Agent**:
    - `BookingService`/`ScheduleService` должны иметь чёткие, безопасные методы, которые AI‑tools смогут вызывать:
      - `get_available_slots`;
      - `create_booking`;
      - `cancel_booking` (и, опционально, `reschedule_booking`).

По `ARCH_OMNICHANNEL_NEXT.md` и `ARCH_DEV_OMNI_REGISTRY_015.md`:

- Omnichannel‑AI‑слой:
  - использует `tools_registry`:
    - Booking‑инструменты — одна из ключевых категорий;
  - AI‑агент в чатах должен уметь:
    - предлагать слоты;
    - создавать/отменять запись;
    - работать строго в пределах прав и `clinic_id` контекста.

### 1.2. GAP BKG‑6 и OMNI‑1/3

По `BACKEND_GAPS_Booking_NEXT.md` и `BACKEND_GAPS_Omnichannel_NEXT.md`:

- **BKG‑6:**
  - AI‑tools API поверх Booking/Schedule пока отсутствует:
    - нет явного слоя, предоставляющего операции расписания/записи как инструменты для AI‑Orchestrator’а.
- **OMNI‑1/3 (связанные):**
  - tools‑registry и Orchestrator проектируются в `ARCH_DEV_OMNI_REGISTRY_015.md`, но:
    - Booking‑инструменты ещё не спроецированы на реальные сервисы/DTO.

Риски:

- AI‑агент не может безопасно и предсказуемо:
  - предлагать слоты с учётом клиники/доктора/услуг;
  - создавать/отменять записи;
  - объяснять пользователю результат операции.
- Высокий риск «левых» AI‑интеграций напрямую в доменные сервисы без реестра/ограничений.

### 1.3. Связанные ARCH/DEV артефакты

- `ARCH_BOOKING_NEXT.md` — домен Booking/Schedule.
- `ARCH_DEV_BKG_CORE_001.md` — фасад завершения визита (опирается на те же сервисы).
- `ARCH_DEV_BKG_STATE_002.md` — статусы `Booking`.
- `ARCH_DEV_BKG_MULTI_003.md` — multi‑clinic логика (AI‑tools должны уважать `clinic_id`).
- `ARCH_DEV_BKG_ERRORS_005.md` — ошибки записи/платежей (AI‑tools должны возвращать понятные коды/сообщения).
- `ARCH_DEV_OMNI_REGISTRY_015.md` — tools‑registry и Orchestrator.
- `ARCH_DEV_OMNI_POLICY_016.md`, `ARCH_DEV_AI_TOKENIZATION_025.md` — политика ПД и tokenization.

---

## 2. Целевое состояние AI‑tools для Booking/Schedule

### 2.1. Жёсткие инварианты

1. **AI‑tools — тонкий адаптер над существующими сервисами Booking.**
   - Ни один tool:
     - не содержит собственной бизнес‑логики;
     - не обходит `BookingService`/`ScheduleService` и фасад завершения визита.

2. **AI‑tools полностью уважают статусы и инварианты Booking.**
   - Операции create/cancel/reschedule:
     - используют enum статусов (`ARCH_DEV_BKG_STATE_002.md`);
     - не позволяют некорректных переходов (например, отмена уже `completed` записи).

3. **AI‑tools работают строго в рамках клиники и RBAC.**
   - Любой вызов:
     - принимает `clinic_id` из `AiToolContext`;
     - проверяет права (через Orchestrator/контекст);
     - не может создавать/менять записи в чужой клинике.

4. **AI‑tools имеют чёткий контракт и возвращают безопасные DTO.**
   - Вход/выход:
     - чётко типизированы;
     - используют токены вместо «голых» id, если инициируются из AI;
     - не содержат ПД (ФИО, телефон и пр.) при `allow_personal_data=False`.

5. **Ошибки AI‑tools предсказуемы.**
   - Ошибки (например, слот недоступен, конфликт записи, ошибка прав) возвращаются:
     - в виде структурированных кодов ошибок;
     - логируются с `trace_id` и контекстом;
     - могут порождать Attention/Tasks при повторяющихся сбоях.

---

## 3. Архитектурный дизайн AI‑tools Booking

### 3.1. Базовые инструменты vNext

В соответствии с `ARCH_DEV_OMNI_REGISTRY_015.md`:

- `get_available_slots`
- `create_booking`
- `cancel_booking`
- (опционально v1) `reschedule_booking`

Каждый tool:

- описывается в `ai/tools_registry.py`:
  - `id`, `description`, `input_schema`, `output_schema`, `required_permissions`;
- реализует handler, который вызывает соответствующие методы `BookingService`/`ScheduleService`.

### 3.2. Пример DTO и handler’а (high‑level)

**get_available_slots**

- Вход (упрощённый эскиз):

```python
class GetAvailableSlotsInput(BaseModel):
    clinic_id: UUID
    service_id: UUID | None = None
    doctor_id: UUID | None = None
    date_from: date
    date_to: date
```

- Выход:

```python
class AvailableSlot(BaseModel):
    slot_id: UUID
    doctor_id: UUID
    service_id: UUID | None
    start: datetime
    end: datetime


class GetAvailableSlotsOutput(BaseModel):
    slots: list[AvailableSlot]
```

**create_booking**

- Вход (упрощённый, без ПД при `allow_personal_data=False`):

```python
class CreateBookingInput(BaseModel):
    clinic_id: UUID
    slot_id: UUID | None = None
    doctor_id: UUID | None = None
    service_id: UUID | None = None
    date_time: datetime | None = None
    patient_token: str  # PATIENT#... (см. tokenization)
    notes: str | None = None
```

- Выход:

```python
class CreateBookingOutput(BaseModel):
    booking_token: str  # BOOKING#...
    status: str
    warnings: list[str] = []
```

- handler:
  - через tokenization‑слой декодирует `patient_token` → `patient_id`;
  - вызывает `BookingService.create_booking(...)`;
  - упаковывает результат в DTO с токенами.

**cancel_booking**

- Вход:

```python
class CancelBookingInput(BaseModel):
    clinic_id: UUID
    booking_token: str  # BOOKING#...
    reason_code: str | None = None
```

- Выход:

```python
class CancelBookingOutput(BaseModel):
    success: bool
    status: str
    error_code: str | None = None
    error_message: str | None = None
```

---

## 4. Интеграция с Booking‑сервисами и инвариантами

### 4.1. BookingService / ScheduleService как источник правды

- AI‑tools **не** реализуют:
  - поиск слотов напрямую по БД;
  - логику конфликтов;
  - валидацию статусов/clinic_id;
  - предоплатные сценарии.

- Вместо этого:
  - `get_available_slots` → `ScheduleService.get_available_slots(...)`;
  - `create_booking` → `BookingService.create_booking(...)`;
  - `cancel_booking` → `BookingService.cancel_booking(...)` / `BookingStatusService.transition(...)`.

### 4.2. Статусы и ошибки

- Любые статусы/ошибки:
  - берутся из:
    - enum статусов и стейт‑машины (`ARCH_DEV_BKG_STATE_002.md`);
    - формата ошибок (`ARCH_DEV_BKG_ERRORS_005.md`);
  - AI‑tools:
    - транслируют эти статусы/коды наружу, не придумывая свои.

### 4.3. Multi‑clinic и контекст

- `clinic_id`:
  - всегда передаётся через `AiToolContext` / DTO;
  - используется сервисами:
    - для фильтрации слотов;
    - для проверки принадлежности `Booking`/`Doctor`/`Service`.

---

## 5. Связь с Omnichannel Orchestrator и security/PD

### 5.1. Orchestrator и tools_registry

- В `ai/tools_registry.py` Booking‑инструменты регистрируются с:
  - `required_permissions` (например, `booking.ai_tools.use` для операторов);
  - `allowed_roles` (операторы, возможно, AI‑системный актор);
  - проверкой `clinic_id` и tokenization.

- Orchestrator:
  - предоставляет LLM‑уровню:
    - сигнатуры Booking‑tools;
    - описания («подбери слоты», «создай запись», «отмени запись»).

### 5.2. Политика ПД и tokenization

- При работе через внешних AI‑провайдеров:
  - все идентификаторы пациентов/записей:
    - используются в текстах/структурах **только** как токены (`PATIENT#...`, `BOOKING#...`);
  - `AiSanitizer`:
    - не маскирует токены, но убирает ФИО/телефоны/адреса при `allow_personal_data=False`.

---

## 6. Наблюдаемость и Tasks/Attention

### 6.1. Логирование и метрики

- Для каждого вызова Booking‑tool:
  - логируем:
    - `trace_id`, `tool_id`, `clinic_id`, тип действия (`get_slots`/`create`/`cancel`);
    - успех/ошибку и `error_code` (если есть).
- Метрики:
  - количество успешных/ошибочных вызовов по типам;
  - время выполнения (особенно для поиска слотов).

### 6.2. Tasks & Attention

- Повторяющиеся ошибки Booking‑tools:
  - могут создавать Attention/Tasks:
    - e.g. `BOOKING_AI_TOOL_FAILURE`, `BOOKING_AI_TOOL_MISUSE` (если AI часто пытается сделать запрещённое действия).

---

## 7. Dev‑чек‑лист для DEV_PROMPT_BKG_AI_TOOLS_006

### 7.1. Аналитика

1. Найти в коде:
   - существующие методы `BookingService`/`ScheduleService`, которые:
     - отдают свободные слоты;
     - создают/отменяют/переносят записи.
2. Проверить:
   - что они:
     - корректно работают с `clinic_id` (см. `ARCH_DEV_BKG_MULTI_003.md`);
     - уважают статусы/инварианты (`ARCH_DEV_BKG_STATE_002.md`);
     - используют ожидаемый формат ошибок (`ARCH_DEV_BKG_ERRORS_005.md`).

### 7.2. Проектирование DTO для Booking‑tools

3. Определить:
   - входные/выходные модели для:
     - `get_available_slots`, `create_booking`, `cancel_booking` (и `reschedule_booking`, если входит в v1);
   - разместить DTO в подходящем модуле (например, `src/application/dto/booking_ai_dto.py` или рядом с `erp_finance_dto.py`).

### 7.3. Реализация handlers в tools_registry

4. В `ai/tools_registry.py`:
   - зарегистрировать Booking‑tools с:
     - `id`, `description`;
     - `input_schema`, `output_schema`;
     - `required_permissions`/`allowed_roles`.
5. Реализовать handlers:
   - которые:
     - принимают `AiToolContext` + DTO;
     - конвертируют токены в id (через tokenization‑слой);
     - вызывают `BookingService`/`ScheduleService` и возвращают DTO.

### 7.4. Интеграция с Orchestrator/Omnichannel

6. Обновить Orchestrator:
   - включить Booking‑tools в список доступных при соответствующем контексте;
   - обеспечить корректную передачу `clinic_id`, `trace_id`, ролей.

### 7.5. Наблюдаемость, security, PД

7. Добавить логирование/метрики вокруг Booking‑tools.
8. Проверить соответствие:
   - политике ПД (`ARCH_DEV_OMNI_POLICY_016`);
   - tokenization‑слою (`ARCH_DEV_AI_TOKENIZATION_025`).

### 7.6. Тесты и документация

9. Написать/обновить тесты:
   - позитивные сценарии:
     - подбор слотов, создание записи, отмена;
   - негативные:
     - недоступный слот;
     - недостаток прав (RBAC);
     - некорректные токены.
10. Обновить:
    - `DEV_PROMPTS_NEXT.md` (статус DEV_PROMPT_BKG_AI_TOOLS_006);
    - `BACKEND_GAPS_Booking_NEXT.md` (закрытие BKG‑6);
    - при необходимости `BACKEND_GAPS_Omnichannel_NEXT.md` (связь OMNI‑1/3).

