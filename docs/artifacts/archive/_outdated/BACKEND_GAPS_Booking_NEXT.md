### 5. Статус BKG‑1 после DEV_PROMPT_BKG_CORE_001

- **Что реализовано:**  
  - фасад завершения визита `BookingCompletionService.complete_visit`, вызываемый из PUT `/admin/bookings/{booking_id}/complete`;  
  - ERP‑узел вызывается через `ErpVisitNodeService.process_visit_completion` и агрегирует ERP‑состояние визита;  
  - Loyalty подключён в режиме best‑effort (ошибки списания не блокируют завершение, но попадают в метрики и сводку результата);  
  - при ERP‑конфигурационных ошибках фасад не меняет `Booking.status`, проставляет `booking.erp_error_code` и создаёт системный `Task` для владельца/админа;  
  - при несогласованности ERP/Loyalty по обязательствам (например, `attempt_write_off_more_than_remaining` в ERP‑узле) создаётся системный `Task` с кодом `LOYALTY_ERP_INCONSISTENT_OBLIGATION`.  

- **Что остаётся на следующие DEV_PROMPT:**  
  - вынесение CRM/Attribution‑агрегатов вокруг события завершения визита в отдельный сервис (сейчас используется минимальный слой через `make_booking_completed_event`);  
  - дальнейшая детализация ERP‑ноды (Finance/Payroll/Inventory) и отчётных агрегаций — в рамках `DEV_PROMPT_ERP_NODE_010`, `DEV_PROMPT_ERP_REPORTS_012`, `DEV_PROMPT_CRM_MONEY_008`.
## BACKEND_GAPS_Booking_NEXT — домен Booking & Schedule

### 1. Текущее состояние в коде (факты)

- **Сущности:** `Booking`, `Doctor`, `DoctorWorkingHours`, `DoctorAbsence`, `Service`, `ServiceDoctor`, `QueuePolicy`, `WaitlistEntry`, `WaitlistNotification`, `Payment`, `PrepaymentPolicy`, `PrepaymentTransaction`, `ClinicPaymentGateway`, `Notification`.
- **Сервисы и API:**
  - Backend:
    - `schedule.py`, `bookings.py`, `admin_schedule.py`, `admin_doctor_schedule.py`, `admin_waitlist.py`, `admin_prepayment.py`, `payments.py`.
  - Frontend:
    - PWA: `BookingWizardPage.tsx`, `HistoryPage.tsx`.
    - Админка: `SchedulePage.tsx`, `AdminBookingsPage.tsx`, `AdminWaitlistPage.tsx`, `AdminPrepaymentPage.tsx`.
- **Инварианты:**
  - «один слот — одна запись» реализован индексами и логикой сервисов.
  - предоплата опциональна и настраивается на уровне клиники и политик.
  - напоминания и уведомления по записям реализованы через Notification/Celery.

### 2. Сравнение с ARCH_BOOKING_NEXT и ARCH_DECISIONS_NEXT

- ARCH требует:
  - жёсткий узел завершения визита (стык с ERP/CRM/Loyalty);
  - единую модель статусов и централизованные словари;
  - явную multi‑clinic поддержку на уровне UX и логики;
  - формализованную работу листа ожидания;
  - безопасные методы для AI‑tools.
- Код уже содержит большинство сущностей и сервисов, но:
  - завершение визита пока не оформлено как единый фасад с ERP/CRM/Loyalty;
  - статусы в UI выводятся сырыми строками (`HistoryPage` и, вероятно, часть админских экранов);
  - выбор клиники для записи неявен (через `localStorage` + первая клиника);
  - логика waitlist разбросана по нескольким модулям.

### 3. Выявленные GAP’ы

- **BKG-1 — отсутствует единый ERP‑фасад при завершении визита (S1–S2)**  
  - ARCH описывает, что при `Booking.status=completed` должна запускаться связка ERP/CRM/Loyalty в одной точке.  
  - В коде нет явного сервиса «BookingCompletionService», ERP‑логика распределена по нескольким сервисам и attention‑механизмам.

- **BKG-2 — статусы Booking не нормализованы и не централизованы (S2)**  
  - `HistoryPage` и, вероятно, часть админских таблиц выводят `b.status` как сырую строку.  
  - Нет единого словаря статусов (back+front) с человеко‑читаемыми лейблами и строгими enum’ами.

- **BKG-3 — неявная multi‑clinic логика записи (S2)** — **частично снято (2025‑03)**  
  - Backend: публичное расписание с обязательным `clinic_id`, валидация записи/сущностей на клинику, `assert_entity_belongs_to_clinic`, перенос с проверкой врача ∈ клинике; метрика `multitenancy_clinic_mismatch_total`.  
  - **Остаётся:** доработать end‑to‑end тесты waitlist/prepayment и §5.3 Attention при многократных mismatch — см. `ARCH_DEV_BKG_MULTI_003_TASKS.md`.

- **BKG-4 — фрагментированная логика листа ожидания (S2)** — **частично снято (2026‑03)**  
  - Реализован единый **`WaitlistService`**, статусы/переходы, admin‑API через сервис, конвертация в booking с блокировкой и компенсацией, триггер при отмене booking, метрики; детали и хвосты — `ARCH_DEV_BKG_WAITLIST_004.md` §8, **`ARCH_DEV_BKG_WAITLIST_004_TASKS.md`** («Выполнено» / **«На потом»**).

- **BKG-5 — API‑поведение при ошибках не везде доведено до понятного UX (S2)**  
  - хуки `useCreatePatientBooking`/`useCreatePayment` обрабатывают ошибки, но UI‑слой в `BookingWizardPage` не показывает явные сообщения (QA_GAP G4).

- **BKG-6 — AI‑Tools API поверх Booking/Schedule пока отсутствует (S2)**  
  - ARCH требует `get_available_slots`, `create_booking`, `cancel_booking` и др. в `ai_tools`, но сейчас есть только Omnichannel/AI stubs.

### 4. Оценка сложности исправления

- **BKG-1:** средняя/высокая — требует аккуратного выделения фасада и миграции ERP‑логики.
- **BKG-2:** средняя — нуждается в создании словаря статусов и обновлении множества экранов, но без изменения доменной модели.
- **BKG-3:** средняя — влияет на UX и часть API, но опирается на уже существующие сущности клиник.
- **BKG-4:** средняя — нужно аккуратно собрать существующую логику в сервис, не ломая API.
- **BKG-5:** низкая/средняя — в основном фронтовой и UX‑уровень.
- **BKG-6:** средняя — требует проектирования поверх уже существующих сервисов, но без их перелома.

