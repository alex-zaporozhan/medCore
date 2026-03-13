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

