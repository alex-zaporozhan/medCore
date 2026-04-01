## ARCH_BOOKING_NEXT — домен Booking & Schedule

### 1. Краткое описание домена

Домен **Booking & Schedule** отвечает за полный жизненный цикл визита:

- открытые слоты расписания врачей по клинике;
- создание, изменение, перенос и отмену записей;
- лист ожидания и политики очереди;
- связь с предоплатой/платежами, уведомлениями и ERP.

Это «сердце» операционной части Business OS: всё, что связано с визитами пациентов.

### 2. Актуальная модель сущностей (по коду / BUSINESS_LOGIC_CURRENT)

Основные сущности (по `BUSINESS_LOGIC_CURRENT.md` и коду):

- **Расписание:**
  - `Doctor`, `DoctorWorkingHours`, `DoctorAbsence`
  - `Service`, `ServiceDoctor`
- **Записи:**
  - `Booking` — сама запись;
  - `QueuePolicy` — политика очереди/лист ожидания;
  - `WaitlistEntry`, `WaitlistNotification` — лист ожидания и уведомления по нему.
- **Предоплата/платежи:**
  - `Payment`, `PrepaymentPolicy`, `PrepaymentTransaction`, `ClinicPaymentGateway`.
- **Уведомления по записям:**
  - `Notification`, `WaitlistNotification` (частично пересекается с Notification‑доменом).

API и сервисы:

- Backend:
  - `src/api/v1/routers/schedule.py`, `bookings.py`, `admin_schedule.py`, `admin_doctor_schedule.py`, `admin_waitlist.py`, `admin_prepayment.py`, `payments.py`.
  - Сервисы `BookingService`, `ScheduleService`, `PaymentService` (по коду).
- Frontend:
  - PWA: `BookingWizardPage.tsx`, `HistoryPage.tsx`.
  - Админка: `SchedulePage.tsx`, `AdminBookingsPage.tsx`, `AdminWaitlistPage.tsx`, `AdminPrepaymentPage.tsx`.

Ключевые инварианты, уже реализованные:

- **Один слот — одна запись** (`doctor + date + time`).
- Предоплата опциональна и управляется политиками и настройками клиники.
- Автоматические напоминания и уведомления по предстоящим/отменённым записям.

### 3. Целевая модель vNext (что нужно добавить/упростить)

1. **Чёткий «узел завершения визита» (стык с ERP/CRM/Loyalty):**
   - При `Booking.status → completed` внутри одной транзакции:
     - вызвать ERP‑сервис для создания `FinancialTransaction`, `SalaryTransaction`, `InventoryTransaction`;
     - оповестить CRM (перевод `LeadCard` в «Success», пересчёт LTV пациента);
     - опционально уменьшить абонемент/депозит в Loyalty.

2. **Единая модель статусов и их отображения:**
   - Ввести централизованный enum/словарь статусов `Booking` (back+front):
     - `new`, `pending_payment`, `confirmed`, `completed`, `cancelled`, `no_show`, и т.п.;
   - На фронте везде использовать человеко‑читаемые лейблы и цвета (в т.ч. в `HistoryPage`).

3. **Multi‑clinic‑поддержка UX‑уровня:**
   - Явный выбор клиники при записи (а не только через `localStorage`/первую клинику);
   - возможность работать с расписанием в нескольких клиниках (при нужных ролях).

4. **Унификация работы с листом ожидания:**
   - единый сервис/правила перехода из waitlist в `Booking`;
   - понятные триггеры (освободился слот → что именно происходит).

5. **Injectability для AI‑Agent:**
   - `BookingService` и `ScheduleService` должны иметь чёткие, безопасные методы, которые AI‑tools смогут вызывать (`get_available_slots`, `create_booking`, `cancel_booking`).

### 4. Связи с другими доменами

- **ERP:** завершение визита, расчёт денег/ЗП/склада.
- **CRM:** автодвижение лидов по стадиям (создана запись / завершена / отменена).
- **Loyalty:** списание посещений/баланса по пакетам при завершённой записи.
- **Tasks & AttentionFeed:** создание задач/attention‑элементов при проблемах (ошибка ERP, неявка, сбой оплаты).
- **Omnichannel & AI:** создание/управление записями и waitlist’ом по командам из чатов через AI‑tools.

