## 🧩 ARCH_CROSSCUT_EVENT_CONTEXT_AI — Events, RequestContext и AI‑конфиг

> Роли: @ARCH, @LEAD, @DEV.  
> Цель: описать три поперечных слоя, которые нужно укрепить до начала реализации модулей V2,  
> чтобы все изменения стыковались без жёстких связей:
> 1) доменные события/хуки,  
> 2) Request/ClinicContext,  
> 3) централизованная конфигурация AI‑провайдера и политики ПД.

---

## 1. Доменные события и application‑хуки

### 1.1. Задача

- Избежать копипасты логики между CRM/ERP/Loyalty/Tasks/Attribution.
- Дать единые точки, на которые могут «подписываться» разные модули:
  - `on_booking_created`
  - `on_booking_completed`
  - `on_payment_success`
  - `on_contact_created` (новый OmnichannelContact)

### 1.2. Архитектурный подход

- Новый модуль, например: `src/application/events/`:

```python
class DomainEvent(BaseModel):
    name: str
    payload: dict

class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[DomainEvent], Awaitable[None]]]] = {}

    def subscribe(self, name: str, handler: Callable[[DomainEvent], Awaitable[None]]) -> None:
        ...

    async def publish(self, event: DomainEvent) -> None:
        ...
```

- Внутри одного процесса:
  - EventBus можно хранить в `src/core/deps` или инстанцировать как singleton (с учётом тестов).
  - подписчики — функции уровня application‑сервисов (CRM/ERP/Tasks).

### 1.3. Примеры событий

- `BookingCreated`:
  - payload: `{ "clinic_id", "booking_id", "doctor_id", "patient_id", "source" }`.
  - подписчики:
    - CRM: создание/обновление `LeadCard`;
    - Tasks: задачи «подтвердить запись» (если требуется).

- `BookingCompleted`:
  - payload: `{ "clinic_id", "booking_id" }`.
  - подписчики:
    - ERP: финансы/ЗП/склад;
    - Loyalty: начисление кэшбэка/списание пакетов;
    - CRM: перевод лида на стадию «Успех»;
    - Tasks: отметка связанных задач как выполненных.

- `PaymentSuccess`:
  - payload: `{ "clinic_id", "payment_id", "booking_id", "amount" }`.
  - подписчики:
    - ERP (фаза 2): финансовые транзакции;
    - CRM: переход в стадию «Предоплата внесена»;
    - Loyalty (при покупке пакета).

- `ContactCreated`:
  - payload: `{ "clinic_id", "omnichannel_contact_id", "channel", "metadata" }`.
  - подписчики:
    - CRM: создание `LeadCard`;
    - Attribution: привязка `VisitAttribution`.

### 1.4. Карта контрактов стандартных событий V2 (фактическая реализация)

Ниже — «источник правды» по стандартным событиям, которые сейчас формируются через
`src/application/events/standard_events.py` и используются в хендлерах CRM/ERP/Loyalty/Attribution.

#### BookingCreated (`BOOKING_CREATED`)

- **Фабрика**: `make_booking_created_event(booking: Booking) -> DomainEvent`
- **Имя события**: `"BookingCreated"`
- **Payload (ключи и типы)**:
  - `booking_id: str` — UUID бронирования;
  - `clinic_id: str` — UUID клиники;
  - `patient_id: str` — UUID пациента;
  - `doctor_id: str` — UUID врача;
  - `service_id: str` — UUID услуги;
  - `status: str` — статус бронирования (например, `"confirmed"`);
  - `appointment_date: str` — дата приёма в ISO‑формате (`YYYY-MM-DD`);
  - `appointment_time: str` — время приёма в ISO‑формате (`HH:MM:SS[.ffffff]`).
- **Инварианты**:
  - `booking_id`, `clinic_id`, `patient_id`, `doctor_id`, `service_id` заполнены валидными UUID‑строками;
  - `status` соответствует одному из допустимых статусов доменной сущности `Booking`;
  - дата/время соответствуют полям `Booking.appointment_date` и `Booking.appointment_time`.
- **Сценарий публикации**:
  - после успешного создания бронирования в `BookingService` (после валидаций, но до внешних сайд‑эффектов);
  - публикуется один раз на каждое новое бронирование.
- **Типовые подписчики**:
  - CRM (`handle_lead_on_booking_created`) — связывает бронирование с уже существующим лидом.

#### BookingCompleted (`BOOKING_COMPLETED`)

- **Фабрика**: `make_booking_completed_event(booking: Booking) -> DomainEvent`
- **Имя события**: `"BookingCompleted"`
- **Payload**:
  - те же ключи, что и у `BookingCreated`:
    `booking_id`, `clinic_id`, `patient_id`, `doctor_id`, `service_id`,
    `status`, `appointment_date`, `appointment_time`;
  - в ряде хендлеров также ожидаются дополнительные поля (например, `amount_paid` со стороны ERP/Finance),
    которые добавляются на этапе обогащения события.
- **Инварианты**:
  - `status` отражает финальный статус визита (обычно `"completed"`);
  - клиника/пациент/врач/услуга соответствуют фактическим связям в БД.
- **Сценарий публикации**:
  - после успешного завершения приёма (изменения статуса `Booking` на «завершено»),
    когда данные по визиту уже зафиксированы в транзакции.
- **Типовые подписчики**:
  - ERP (`handle_erp_on_booking_completed`) — проводка финансов, ЗП, склада;
  - Loyalty (`handle_loyalty_on_booking_completed`) — начисление кэшбэка и баллов;
  - CRM (`handle_lead_on_booking_completed`) — перевод лида в успешное состояние;
  - Tasks — завершение связанных задач (планируется/расширяется в рамках DEV_PROMPTS_RBAC_AND_TASKS).

#### PaymentSuccess (`PAYMENT_SUCCESS`)

- **Фабрика**: `make_payment_success_event(payment: Payment) -> DomainEvent`
- **Имя события**: `"PaymentSuccess"`
- **Payload**:
  - `payment_id: str` — UUID платежа;
  - `clinic_id: str` — UUID клиники;
  - `booking_id: str` — UUID бронирования, к которому относится платёж;
  - `status: str` — статус платежа (ожидается успешный, например `"succeeded"` / `"paid"`);
  - `amount: str` — сумма платежа в виде строки, совместимой с `Decimal`;
  - `currency: str` — код валюты (например, `"RUB"`).
- **Инварианты**:
  - `amount` парсится в `Decimal` без ошибок;
  - `booking_id` указывает на существующее бронирование в той же клинике.
- **Сценарий публикации**:
  - после успешного подтверждения платежа платёжным шлюзом и фиксации записи `Payment` в БД.
- **Типовые подписчики**:
  - ERP (`handle_erp_on_payment_success`) — отражение движения денег в ERP‑узле;
  - CRM (`handle_lead_on_payment_success`) — обновление `actual_value` лида;
  - Loyalty (`handle_erp_on_payment_success` → `LoyaltyService.purchase_subscription`) — покупка пакета/подписки.

#### ContactCreated (`CONTACT_CREATED`)

- **Фабрика**: `make_contact_created_event(contact_id, clinic_id, patient_id | None) -> DomainEvent`
- **Имя события**: `"ContactCreated"`
- **Payload**:
  - `contact_id: str` — UUID `OmnichannelContact`;
  - `clinic_id: str` — UUID клиники (business account);
  - `patient_id: str | None` — UUID пациента, если контакт уже линкуется к существующему пациенту, иначе `null`.
- **Инварианты**:
  - `contact_id` всегда заполнен и соответствует существующему контакту;
  - `clinic_id` — валидный UUID клиники;
  - если `patient_id` задан, он указывает на пациента в той же клинике.
- **Сценарий публикации**:
  - сразу после создания нового `OmnichannelContact` (первое сообщение/инициализация чата).
- **Типовые подписчики**:
  - CRM (`handle_lead_on_contact_created`) — создание первичного лида по чату;
  - Attribution — привязка visit/traffic‑источника к контакту (расширяется в маркетинговом модуле).

> Для любых новых модулей (CRM/ERP/Loyalty/Tasks/Attribution) **запрещено** полагаться на поля,
> которых нет в этой карте контрактов, без явного расширения `standard_events` и обновления данного раздела.

---

## 2. Request/ClinicContext

### 2.1. Задача

- Стандартизировать доступ к:
  - `clinic_id`;
  - текущему пользователю (`AdminUser`/`Doctor`/`Patient`);
  - его ролям и permissions.
- Избавиться от ситуаций, когда сервисы тянут `AdminUser` напрямую из зависимостей или контекста HTTP‑запроса.

### 2.2. Архитектурная модель

- Новый тип, например `src/core/context.py`:

```python
class RequestContext(BaseModel):
    clinic_id: UUID | None
    user_id: UUID | None
    user_type: Literal["admin", "doctor", "patient", "system"] | None
    roles: set[str]
    permissions: set[str]
```

- На уровне FastAPI dependencies:
  - `get_request_context()`:
    - получает токен (`get_current_admin`/`get_current_patient`);
    - определяет `clinic_id`, роли и permissions (см. ARCH_RBAC_AND_TASKS);
    - отдаёт `RequestContext`.

- Application‑сервисы новых модулей принимают `ctx: RequestContext` первым аргументом (или в конструкторе):
  - ERP/CRM/Loyalty/Tasks/Attribution всегда видят, в какой клинике и от имени кого выполняется операция.

### 2.3. Консистентный источник clinic_id (V2)

Для всех admin API‑роутеров **единственный источник** `clinic_id` и прав — `RequestContext`, получаемый через dependency `get_request_context()` (тип в эндпоинтах: `AdminContext`). Роутеры не используют напрямую `get_current_admin()` для получения клиники; вместо этого инжектируют `context: AdminContext = Depends(get_request_context)` и берут `context.clinic_id`, `context.user_id`, `context.permissions`.

- **CRM** (`admin_crm.py`), **Loyalty** (`admin_loyalty.py`), **Tasks** (`admin_tasks.py`), **Marketing Attribution** (`admin_marketing_attribution.py`): во всех эндпоинтах используется `context: AdminContext = Depends(get_request_context)`; при отсутствии `context.clinic_id` возвращается 400 с сообщением «Clinic context is required».
- **ERP** (`BookingErpService`): вызывается из обработчиков событий и из сервисов бронирования; `clinic_id` берётся из контекста визита (booking), а не из HTTP‑запроса.
- **Event handlers** (CRM/ERP/Loyalty/Tasks/Attribution): получают `clinic_id` из payload доменного события (`event.payload["clinic_id"]`), а не из RequestContext.
- **Celery/batch‑джобы**: см. раздел про системные режимы (user_type="system"); при необходимости передаётся явный `clinic_id` в задачу.

---

## 3. Централизованный AI‑конфиг и политика ПД

### 3.1. Задача

- Избавиться от разбросанной логики выбора провайдера и работы с ПД.
- Обеспечить единые правила для:
  - AI Agent (Omnichannel);
  - AI‑отчётов/аналитики;
  - AI Task Generator.

### 3.2. AiConfigService

- Новый сервис, например `src/application/services/ai_config_service.py`:

```python
class AiProviderConfig(BaseModel):
    base_url: str
    api_key: str
    model: str
    allow_personal_data: bool
    provider_type: Literal["external", "ru_compliant", "on_premise"]

class AiConfigService:
    async def get_clinic_ai_config(self, clinic_id: UUID) -> AiProviderConfig:
        ...
```

- Источники:
  - `Settings` (глобальные дефолты);
  - `ClinicAiSettings` (переопределения на уровне клиники).

### 3.3. Политика ПД

- На уровне `AiConfigService`:
  - решается, можно ли передавать ПД этому провайдеру (`allow_personal_data`) и в каком режиме:
    - `external` + `allow_personal_data=False` → только обезличенные тексты;
    - `ru_compliant` + `allow_personal_data=True` → допустима передача ПД (при наличии согласий).
- На уровне `AiClient`/`AiSanitizer`:
  - вход получает флаг `allow_personal_data`;
  - если `False`:
    - вырезает/заменяет ФИО, телефоны, email и др.;
  - если `True`:
    - пропускает текст как есть (при условии, что бизнес зафиксировал это в политике).

Все модули, использующие AI (орchestrator, отчёты, task generator), сначала запрашивают `AiProviderConfig` из `AiConfigService`, а не читают настройки напрямую.

---

## 4. Приоритет и реализация

1. **Domain Events / хуки** — ввести каркас EventBus + первые события для Booking/Payment/Contact:
   - на первых фазах можно использовать простой in‑process EventBus без очередей;
   - в дальнейшем его можно заменить на более сложное решение, не меняя интерфейс.
2. **RequestContext** — оформить тип и dependency, начать использовать в новых модулях V2.
3. **AiConfigService** — вынести выбор провайдера и PД‑политику в один сервис, перевести существующий AI‑код на его использование.

Эти слои не меняют бизнес‑контракты, но обеспечивают аккуратную стыковку всех последующих пакетов изменений (CRM, ERP, RBAC/Tasks, Loyalty, Paperless, Attribution, Frontend Business OS).

