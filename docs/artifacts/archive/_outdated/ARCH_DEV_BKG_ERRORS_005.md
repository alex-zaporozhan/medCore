## ARCH_DEV_BKG_ERRORS_005 — явное поведение при ошибках записи/платежей

> DEV_PROMPT_BKG_ERRORS_005 — «явное поведение при ошибках записи/платежей (BKG‑5, FPWA‑4)»

---

## 1. Контекст и существующее состояние

### 1.1. Ошибки в цепочке записи/платежа

Критичная цепочка (см. `ARCH_BOOKING_NEXT.md`, `ARCH_DECISIONS_NEXT.md`, `NONFUNCTIONAL_AUDIT_NEXT.md`):

1. Пациент/админ выбирает слот (`Schedule` / `BookingWizardPage` / `SchedulePage`).
2. Создаётся `Booking` (с учётом `clinic_id`, статусов BKG‑STATE).
3. Возможно, требуется предоплата:
   - `PrepaymentPolicy`, `PrepaymentTransaction`, платёжные шлюзы.
4. Визит проводится/завершается (ERP‑узел, фасад BKG‑CORE).

Ошибки могут возникнуть:

- на этапе создания/валидации записи;
- на этапе предоплаты/платежа;
- при частичных сбоях в ERP/LOYALTY при завершении визита (но DEV_PROMPT_BKG_ERRORS_005 фокусируется на **создании записи и оплате**).

### 1.2. Фактические GAPS (BKG‑5, FPWA‑4, OBS‑1/2)

По `BACKEND_GAPS_Booking_NEXT.md` и `FRONTEND_GAPS_AppPWA_NEXT.md`:

- **BKG‑5 (backend):**
  - API‑поведение при ошибках не везде доведено до понятного UX:
    - хуки `useCreatePatientBooking` / `useCreatePayment` обрабатывают ошибки,
    - но не всегда формируется единый, структурированный ответ для фронта.
- **FPWA‑4 (frontend):**
  - в `BookingWizardPage`:
    - отсутствие явного отображения ошибок создания записи/платежа;
    - ошибки могут «теряться» или отображаться как общая техническая проблема без бизнес‑смысла.
- **OBS‑1/OBS‑2 (observability):**
  - критичные цепочки (Booking → Payments → ERP) недостаточно покрыты логами/метриками;
  - AI/Tasks‑слой не всегда получает сигналы о повторяющихся ошибках.

Риски:

- пользователь не понимает, создана ли запись и прошла ли оплата;
- возможны «подвисшие» состояния (оплата прошла, запись не создалась / наоборот);
- трудно расследовать инциденты (нет trace‑идентификаторов и понятных логов).

### 1.3. Связанные ARCH/DEV артефакты

- `ARCH_BOOKING_NEXT.md` — домен Booking/Prepayment/Payments.
- `ARCH_DEV_BKG_CORE_001.md` — фасад завершения визита.
- `ARCH_DEV_BKG_STATE_002.md` — статусы `Booking` (используются и для ошибок).
- `ARCH_TASKS_NEXT.md`, `ARCH_DEV_TASKS_MODEL_020.md` — Tasks & AttentionFeed.
- `ARCH_DEV_OBS_CHAINS_023.md` — критичные цепочки и метрики.
- `NONFUNCTIONAL_AUDIT_NEXT.md` — OBS/SEC/PERF требования.
- `FRONTEND_GAPS_AppPWA_NEXT.md` — FPWA‑4.

---

## 2. Целевое состояние обработки ошибок записи/платежей

### 2.1. Жёсткие инварианты

1. **Ни одна ошибка не «теряется».**
   - Любой сбой в цепочке создания записи/платежа:
     - возвращается на фронт в структурированном виде;
     - логируется на backend с `trace_id`, `clinic_id`, типом ошибки;
     - для критичных кейсов создаёт Attention/Task.

2. **Пользователь всегда понимает, что произошло.**
   - PWA/админка:
     - отображают бизнес‑понятные сообщения (нет только «Something went wrong»);
     - чётко разделяют:
       - «не прошла оплата»;
       - «не удалось создать запись»;
       - «сервис временно недоступен».

3. **Идём по принципу «всё или ничего» для пары запись+платёж, где возможно.**
   - Если запись зависит от предоплаты:
     - состояние «оплата прошла, запись не создана» должно:
       - либо не возникать вообще (транзакционный подход с компенсацией);
       - либо обрабатываться как Attention/Task с понятным recovery‑планом.

4. **Ошибки становятся сигналами для Tasks/Attention и OBS.**
   - Повторяющиеся ошибки (по клинике/шлюзу/типу) автоматически видны в:
     - AttentionFeed;
     - базовых метриках (количество ошибок по типам).

---

## 3. Архитектурный дизайн: backend

### 3.1. Структурированные ответы и коды ошибок

Для операций:

- создания записи с/без предоплаты;
- создания/подтверждения платежа;

нужен явный формат ошибок. Подход:

- Ввести/уточнить единый DTO для ошибок на Booking/Payments‑уровне, например:

```python
class BookingErrorCode(str, Enum):
    SLOT_UNAVAILABLE = "slot_unavailable"
    PATIENT_NOT_FOUND = "patient_not_found"
    PAYMENT_FAILED = "payment_failed"
    PREPAYMENT_REQUIRED = "prepayment_required"
    VALIDATION_ERROR = "validation_error"
    SERVICE_UNAVAILABLE = "service_unavailable"


class BookingErrorResponse(BaseModel):
    code: BookingErrorCode
    message: str
    details: dict | None = None
    trace_id: str | None = None
```

- Роутеры `bookings.py`, `payments.py`, `admin_prepayment.py`:
  - при известных бизнес‑ошибках:
    - возвращают 4xx с `BookingErrorResponse`;
  - при внутренних ошибках:
    - возвращают 5xx, но в логах фиксируется полный контекст и `trace_id`.

### 3.2. Интеграция с OBS‑цепочкой

- Использовать `trace_id`/`correlation_id` (см. `ARCH_DEV_OBS_CHAINS_023.md`):
  - создавать/прокидывать его от момента вызова PWA/админ‑API;
  - включать в каждый лог и ответ об ошибке.

- Логирование:
  - в ключевых местах Booking/Payments:
    - логировать:
      - `trace_id`, `clinic_id`, `patient_id?`, `slot_id/booking_id?`;
      - тип операции (`create_booking`, `create_prepayment`, `confirm_payment`);
      - `error_code`, важные детали (без ПД).

### 3.3. Связь с Tasks & Attention

- Определить порог для Attention/Tasks:
  - единичные ошибки валидации/слота → только фронт/логи;
  - повторяющиеся ошибки провайдера/шлюза/ERP‑связки:
    - создают `AttentionItem` типа:
      - `BOOKING_PAYMENT_GATEWAY_FAILURE`;
      - `BOOKING_CREATION_DEGRADED`.

- `AttentionFeedService`:
  - добавить методы/места вызова из Booking/Payments:
    - при достижении порогов (например, N ошибок за M минут по одной клинике/шлюзу).

---

## 4. Архитектурный дизайн: frontend (PWA + admin)

### 4.1. PWA `/app` — BookingWizardPage (FPWA‑4)

Цели:

- Показать пользователю:
  - чёткий прогресс операций (статусы шагов);
  - явные ошибки и возможные действия.

Подход:

- В хук(и) `useCreatePatientBooking`, `useCreatePayment`:
  - принимать и пробрасывать `BookingErrorResponse` (code/message/details).

- В UI `BookingWizardPage`:
  - отобразить ошибки в отдельных зонах:
    - banner/alert над формой;
    - toast для «узких» сообщений (например, «слот уже занят, обновите расписание»).
  - маппинг `code → текст/действие`, например:
    - `SLOT_UNAVAILABLE` → «Выбранный слот уже занят. Пожалуйста, выберите другое время.»;
    - `PAYMENT_FAILED` → «Платёж не прошёл. Попробуйте ещё раз или выберите другой способ оплаты.»;
    - `SERVICE_UNAVAILABLE` → «Сервис временно недоступен. Попробуйте позже или свяжитесь с клиникой.».

- UX‑инварианты:
  - кнопки:
    - `disabled` во время запросов (исключить дабл‑клик и дублирование);
  - при ошибке:
    - wizard остаётся на текущем шаге;
    - пользователь всегда видит, что именно не получилось.

### 4.2. Admin `/admin` — страницы Booking/Payments

- Аналогично PWA:
  - в `AdminBookingsPage`, `AdminPrepaymentPage`, формах создания/редактирования:
    - использовать структурированные ответы,
    - отображать понятные бизнес‑ошибки.

- Для админа/оператора:
  - при системных проблемах (gateway down, ERP не отвечает и т.п.):
    - явный alert +, по возможности, ссылка на Attention/Tasks, если сигнал уже создан.

---

## 5. Связь с другими DEV_PROMPTS

- **DEV_PROMPT_BKG_CORE_001:**
  - фасад завершения визита опирается на тот же подход к структуре ошибок;
  - BKG‑ERRORS задаёт паттерн для части «создание/платёж», который можно переиспользовать.

- **DEV_PROMPT_OBS_CHAINS_023:**
  - ошибки создания записи/платежей становятся частью observability‑цепочек Booking → ERP/CRM;
  - `trace_id` и метрики ошибок по типам — основа для перф‑/надёжностных дашбордов.

- **DEV_PROMPT_TASKS_MODEL_020 / DEV_PROMPT_TASKS_AI_021:**
  - повторяющиеся ошибки и деградации в Booking/Payments формируют сигналы и задачи;
  - AI Task Manager может использовать статистику ошибок для предложения действий (сменить политику предоплаты, проверить шлюз и т.п.).

---

## 6. Dev‑чек‑лист для DEV_PROMPT_BKG_ERRORS_005

### 6.1. Аналитика

1. Backend:
   - найти все места в:
     - `bookings.py`, `payments.py`, `admin_prepayment.py`, `BookingService`, платёжных сервисах,
   - где:
     - ловятся/бросаются исключения;
     - формируются ответы об ошибках;
     - сейчас ошибки «теряются» или сворачиваются в общий 500.
2. Frontend:
   - в PWA:
     - `BookingWizardPage`, хуки записи/платежей;
   - в админке:
     - формы работы с предоплатой/платежами.
3. Сопоставить с:
   - `BACKEND_GAPS_Booking_NEXT.md` (BKG‑5);
   - `FRONTEND_GAPS_AppPWA_NEXT.md` (FPWA‑4);
   - `NONFUNCTIONAL_AUDIT_NEXT.md` (OBS‑1/2).

### 6.2. Backend: единый формат ошибок

4. Ввести/уточнить enum и DTO ошибок Booking/Payments.
5. Обновить роутеры:
   - вместо «сырых» исключений/общих сообщений:
     - возвращать структурированный `BookingErrorResponse` с корректными HTTP‑кодами.
6. Интегрировать `trace_id` в обработку ошибок:
   - прокидывать его в ответы и логи.

### 6.3. Backend: интеграция с Attention/Tasks

7. Определить критерии для создания AttentionItem:
   - N ошибок одного типа/клиники за интервал T;
   - «невосстановимые» ошибки (например, misconfig шлюза).
8. Реализовать вызовы `AttentionFeedService` из соответствующих мест ошибок.

### 6.4. Frontend: PWA

9. Обновить хук(и) записи/платежей:
   - разбирать `BookingErrorResponse` и отдавать код/сообщение в компонент.
10. В `BookingWizardPage`:
    - отрисовывать понятные сообщения;
    - обеспечить:
      - корректный loading/error state;
      - отсутствие дабл‑сабмита.

### 6.5. Frontend: admin

11. В админских формах Booking/Prepayment/Payments:
    - аналогично PWA:
      - поддержать структурированные ошибки;
      - отобразить alert/tooltip c бизнес‑смыслом.

### 6.6. Наблюдаемость и тесты

12. Добавить:
    - логи по ошибкам цепочки записи/платежей с `trace_id` и `error_code`;
    - базовые метрики:
      - количество ошибок по кодам/клиникам.
13. Тесты:
    - позитивные сценарии:
      - успешное создание записи, успешная оплата;
    - негативные:
      - занятой слот;
      - провал платёжного шлюза;
      - валидационные ошибки;
    - проверка:
      - что фронт получает ожидаемые коды/сообщения;
      - что не происходит «двойной» записи или платежа.

### 6.7. Документация и связь с GAPS

14. Обновить после реализации:
   - `DEV_PROMPTS_NEXT.md` (статус DEV_PROMPT_BKG_ERRORS_005);
   - `BACKEND_GAPS_Booking_NEXT.md` (BKG‑5);
   - `FRONTEND_GAPS_AppPWA_NEXT.md` (FPWA‑4);
   - при необходимости — `NONFUNCTIONAL_AUDIT_NEXT.md` (OBS‑1/2).

---

## 7. Предложения @DEV и «на потом»

### 7.1. Backlog по результатам @QA_ARCH («на потом»)

1. **Admin‑UX по ошибкам Booking/Payments (BKG‑5, FPWA‑4, пункт 4.2, 6.5).**
   - Текущее состояние:
     - PWA (`BookingWizardPage`) уже маппит `BookingErrorResponse.code` в понятные сообщения.
     - Админские страницы (`AdminBookingsPage`, `AdminPrepaymentPage`) показывают `error.message` без разбора `code`/`traceId`.
   - На потом:
     - доработать хуки/клиент админки так, чтобы они принимали `BookingErrorResponse` (code/message/details/trace_id);
     - добавить явные баннеры/алерты с бизнес‑смыслом для кодов (`booking_not_found`, `payment_not_allowed`, `payment_failed`, `service_unavailable` и т.п.);
     - для системных проблем (gateway down, ERP недоступен) — отдельный alert с подсказкой «проверить Attention/Tasks», когда такой сигнал уже создан.

2. **Observability + Attention/Tasks для повторяющихся ошибок записи/платежей (OBS‑1/2, пункт 3.3, 6.3, 6.6).**
   - Текущее состояние:
     - `trace_id` прокинут по цепочке (`main.py`, `RequestContext`, `BookingErrorResponse`).
     - `AttentionFeedService` уже поднимает элементы по ERP‑ошибкам завершения визита (`Booking.erp_error_code`) и loyalty/retention‑кейсам.
   - На потом:
     - ввести прометеус‑метрики по ошибкам записи/платежей (например, `booking_payment_errors_total{clinic_id,error_code,gateway_id}`) в `core/metrics.py` и использовать их в `bookings.py`/`payments.py`;
     - определить и задокументировать пороги: «N ошибок одного типа/клиники/шлюза за T минут»;
     - реализовать генерацию `AttentionItem` для кейсов:
       - `BOOKING_PAYMENT_GATEWAY_FAILURE` — массовые ошибки платёжного шлюза;
       - `BOOKING_CREATION_DEGRADED` — массовые отказы/валидации при создании записи (при исправном шлюзе).

3. **Тестовое покрытие BKG_ERRORS_005 (пункт 6.6).**
   - Текущее состояние:
     - есть тесты фасада завершения визита (`BookingCompletionService`) и сопутствующих сервисов;
     - нет фокусных тестов на коды ошибок для создания записи/платежей.
   - На потом:
     - добавить API‑тесты для:
       - занятого слота (`slot_unavailable` в ответе `create_patient_booking`/`create_admin_booking`);
       - провала платёжного шлюза / недопустимого статуса (`payment_failed`, `payment_not_allowed` в ответе `create_payment`);
       - базовых валидационных ошибок (`validation_error`);
     - отдельно проверить, что фронтовый клиент (`ApiErrorWithCode`) корректно парсит `detail.{code,message,trace_id,details}` и не теряет `code`.

4. **Документация и синхронизация с GAPS (пункт 6.7).**
   - Текущее состояние:
     - код частично реализовал DEV_PROMPT_BKG_ERRORS_005 (DTO, PWA‑UX, часть backend‑логики);
     - артефакты GAPS/DEV_PROMPTS ещё не обновлены под новое состояние.
   - На потом:
     - обновить `DEV_PROMPTS_NEXT.md` по статусу DEV_PROMPT_BKG_ERRORS_005 (что уже закрыто, что в backlog);
     - обновить `BACKEND_GAPS_Booking_NEXT.md` и `FRONTEND_GAPS_AppPWA_NEXT.md` (закрытие части BKG‑5/FPWA‑4);
     - при добавлении метрик/Attention‑логики — откорректировать `NONFUNCTIONAL_AUDIT_NEXT.md` и `ARCH_DEV_OBS_CHAINS_023.md`.

### 7.2. Быстрые доработки, которые можно делать уже сейчас (@DEV)

1. **Выделить централизованный маппинг кодов ошибок во фронте.**
   - Завести модуль `frontend/src/shared/errors.ts` (или аналог) с словарём `bookingErrorMessages[code]`, который выдаёт текст/уровень/возможное действие.
   - Подключить его в `BookingWizardPage` и впоследствии в админские компоненты — без изменения API, только рефакторинг UI‑слоя.

2. **Подготовить единый helper для маппинга исключений → BookingErrorResponse на backend.**
   - Вынести общую логику из `_booking_error_from_value_error` и обработки ошибок в `payments.py` в утилиту (например, `application/errors.py`), которая принимает:
     - исходное исключение/сообщение,
     - `RequestContext` (для `trace_id`),
     - опциональный `default_code`.
   - Использовать helper в `bookings.py`/`payments.py` без изменения публичных контрактов.
