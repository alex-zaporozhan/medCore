## ARCH_DEV_BKG_WAITLIST_004 — унификация листа ожидания

> DEV_PROMPT_BKG_WAITLIST_004 — «унификация листа ожидания (BKG‑4, FADM‑2)»

---

## 1. Контекст и существующее состояние

### 1.1. Роль waitlist в продукте

- Лист ожидания (waitlist) решает задачи:
  - удерживать пациентов, не нашедших удобного слота прямо сейчас;
  - заполнять «дыры» в расписании при отменах/освободившихся окнах;
  - помогать администраторам прозрачно управлять очередью.
- Связан с доменами:
  - **Booking / Schedule** — слоты расписания, реальные записи;
  - **Omnichannel/CRM** — коммуникации по переводу из waitlist в Booking;
  - **Tasks/Attention** — сигналы о «зависших» или критичных ожиданиях.

### 1.2. Проблема (GAPS BKG‑4, FADM‑2 и UX)

По `BACKEND_GAPS_Booking_NEXT.md`, `UX_FLOWS_AND_GAPS_NEXT.md`:

- Логика waitlist:
  - частично размазана по разным сервисам и роутерам (`admin_waitlist.py`, расписание);
  - нет единого доменного сервиса/модели с чёткими статусами и триггерами;
  - поведение при освободившихся слотах/отменах не всегда предсказуемо.
- Риски:
  - потеря/забывание пациентов из листа ожидания;
  - неочевидные правила приоритезации;
  - расхождения между тем, что видит админ, и тем, что реально происходит в коде.

### 1.3. Связанные ARCH/DEV артефакты

- `ARCH_BOOKING_NEXT.md` — модель расписания и записей.
- `ARCH_OMNICHANNEL_NEXT.md` — коммуникации с пациентами.
- `ARCH_TASKS_NEXT.md`, `ARCH_DEV_TASKS_MODEL_020.md` — Tasks/Attention.
- `ARCH_DEV_BKG_CORE_001.md`, `ARCH_DEV_BKG_STATE_002.md`, `ARCH_DEV_BKG_MULTI_003.md`, `ARCH_DEV_BKG_ERRORS_005.md` — основа Booking/ERP/статусов/ошибок.
- `ARCH_DEV_OBS_CHAINS_023.md` — наблюдаемость ключевых цепочек.

---

## 2. Целевое состояние waitlist

### 2.1. Жёсткие инварианты

1. **Waitlist — отдельная доменная сущность с понятным жизненным циклом.**
   - Есть явная сущность `WaitlistEntry` (см. ниже) со статусами.

2. **Каждый элемент waitlist привязан к клинике, пациенту и желаемому окну.**
   - `clinic_id`, `patient_id`, предпочтения по времени/врачу/услуге.

3. **Переход из waitlist в Booking — управляемый и трассируемый.**
   - Любой перевод «ожидание → реальная запись»:
     - создаёт/обновляет `Booking`;
     - меняет статус `WaitlistEntry`;
     - оставляет след в логах/Attention/Tasks при ошибках.

4. **Автоматические и ручные действия не конфликтуют.**
   - Автоматические триггеры (по отменам/освободившимся слотам):
     - учитывают текущее состояние элемента;
     - не создают дубликатных записей;
   - Ручные действия администратора:
     - видны системе;
     - не ломают автоматические сценарии.

5. **Waitlist уважает multi‑clinic и RBAC.**

---

## 3. Архитектурный дизайн моделей

### 3.1. Сущности

- `WaitlistEntry` (рабочее имя):
  - `id: UUID`
  - `clinic_id: UUID`
  - `patient_id: UUID`
  - предпочтения:
    - `preferred_doctor_id: UUID | None`
    - `preferred_service_id: UUID | None`
    - `preferred_time_from: datetime | None`
    - `preferred_time_to: datetime | None`
  - контекст:
    - `source: Enum("admin", "pwa", "omni", "crm")`
    - `notes: str | None`
  - статус:
    - `status: Enum("waiting", "notified", "booked", "cancelled", "expired")`
  - связи:
    - `booking_id: UUID | None` (если был создан/закреплён Booking)
  - служебные поля:
    - `created_at`, `updated_at`, `created_by`, `updated_by`

- (опционально) `QueuePolicy` / `WaitlistPolicy`:
  - правила приоритезации и уведомлений:
    - по типу услуги, срочности, источнику.

### 3.2. Статусы и переходы

Примерный жизненный цикл:

- `waiting`:
  - заявка создана, ожидает подходящего слота или решения админа;
- `notified`:
  - пациенту отправлено предложение слота;
- `booked`:
  - по этому элементу создана и подтверждена запись (`Booking`);
- `cancelled`:
  - заявка отменена пациентом/клиникой;
- `expired`:
  - условия ожидания устарели (например, прошла дата/период, пациент не ответил).

Переходы и их триггеры фиксируются в коде `WaitlistService` и UI (admin/PWA).

---

## 4. Интеграция с расписанием и Booking

### 4.1. Создание/управление waitlist

- Источники создания:
  - админка:
    - оператор добавляет пациента в лист ожидания (при отсутствии подходящего слота);
  - PWA:
    - пациент сам оставляет запрос с параметрами;
  - Omnichannel/CRM:
    - оператор/AI‑агент переводит диалог в waitlist.

- Все создающие операции:
  - проходят через `WaitlistService`/роутер `admin_waitlist.py` (и/или PWA‑роутеры);
  - устанавливают:
    - `clinic_id`, `patient_id`, предпочтения, `source`.

### 4.2. Триггеры по расписанию

- При событиях:
  - отмена `Booking`/освобождение слота;
  - создание «дыр» в расписании (по правилам);
  - `ScheduleService`/соответствующие Celery‑таски:
    - ищут подходящие `WaitlistEntry`:
      - по клинике, врачу/услуге/времени;
      - по приоритету/дате создания;
    - инициируют:
      - уведомление пациента;
      - или сразу создание черновой/подтверждаемой `Booking` (по выбранной политике).

### 4.3. Перевод в Booking

- Любой успешный сценарий:
  - создаёт/обновляет `Booking`:
    - ссылаясь на `WaitlistEntry` (через `waitlist_entry_id`/`booking_id`);
  - переводит `WaitlistEntry.status`:
    - в `booked` (или `cancelled`/`expired` в других сценариях).

---

## 5. Наблюдаемость, Tasks & Attention

### 5.1. Логирование и метрики

- Логировать:
  - создание/изменение/закрытие `WaitlistEntry`;
  - связи с Booking/расписанием;
  - неудачные попытки автоматического подбора слота.
- Метрики:
  - количество активных `waiting`/`notified` по клинике/врачу/услуге;
  - среднее время ожидания до `booked`/`cancelled`/`expired`;
  - конверсия waitlist → Booking.

### 5.2. Tasks & Attention

- Критичные ситуации:
  - долго ожидающие high‑priority записи;
  - большое число `waiting` по конкретному врачу/сервису;
  - системные сбои триггеров.
- По ним:
  - создаются Attention/Tasks по шаблонам из `ARCH_TASKS_NEXT` и `ARCH_DEV_TASKS_MODEL_020.md`.

---

## 6. SEC/RBAC и multi‑clinic

- Операции с waitlist:
  - относятся к чувствительным (содержат ПД, влияют на расписание);
  - защищаются через:
    - `require_permissions` (см. `ARCH_DEV_SEC_RBAC_022.md`);
    - жёсткий контроль по `clinic_id`.
- PWA:
  - пациент может управлять **своими** элементами waitlist;
  - доступ к чужим заявкам исключён.

---

## 7. Dev‑чек‑лист для DEV_PROMPT_BKG_WAITLIST_004

### 7.1. Аналитика

1. Проанализировать текущие:
   - модели/таблицы waitlist (если есть);
   - сервисы/роутеры (`admin_waitlist.py`, расписание);
   - UX‑потоки в админке и PWA.
2. Сопоставить с GAPS BKG‑4/FADM‑2 и UX‑заметками.

### 7.2. Проектирование и модели

3. Спроектировать и добавить/привести к виду:
   - `WaitlistEntry` (и при необходимости `QueuePolicy`);
   - статусы и поля, описанные выше.
4. Спланировать миграцию данных, если есть легаси‑структуры.

### 7.3. Обновление сервисов и триггеров

5. Ввести/обновить `WaitlistService`:
   - создание/обновление/закрытие записей;
   - поиск подходящих записей при событиях в расписании.
6. Обновить взаимодействие с `ScheduleService` и Booking:
   - по триггерам свободных слотов/отмен.

### 7.4. Наблюдаемость и Tasks

7. Добавить логи/метрики по waitlist (см. раздел 5).
8. Настроить генерацию Attention/Tasks по аномалиям.

### 7.5. Тесты и документация

9. Написать/обновить тесты:
   - создание/закрытие заявок;
   - автоматический/ручной перевод в Booking;
   - сценарии с конфликтами слотов.
10. Обновить:
    - `DEV_PROMPTS_NEXT.md` (статус DEV_PROMPT_BKG_WAITLIST_004);
    - `BACKEND_GAPS_Booking_NEXT.md` и `UX_FLOWS_AND_GAPS_NEXT.md` — отметить закрытые/уточнённые пункты.

---

## 8. Статус реализации (v1 core, 2026‑03)

> Зафиксировано **@QA_ARCH** по факту кода в репозитории (ветка main). Детальный перечень и **«На потом»** — в `ARCH_DEV_BKG_WAITLIST_004_TASKS.md` (конец файла).

### 8.1. Сделано (backend)

- **Единый фасад `WaitlistService`:** `create_entry`, `update_entry`, `cancel_entry` (soft‑cancel), `list_entries` с фильтрами `include_inactive` / `include_booked`, `lock_entry_for_admin_booking` (`SELECT … FOR UPDATE`), `mark_booked_after_booking_created`, `notify_slot_freed`.
- **Домен:** `WaitlistStatus` + матрица переходов (`waitlist_status.py`); нормализация статусов, legacy `converted` → `booked`, предупреждение в лог при неизвестном статусе в БД.
- **ORM/миграция:** расширение `WaitlistEntry` (`preferred_service_id`, `booking_id`, `source`, `notes`, `created_by_id`/`updated_by_id`), миграция `i5j6k7l8m9n0_waitlist_entry_bkg4`.
- **Мультиклиника:** проверки `patient`/`doctor`/`service` ∈ `clinic_id` при создании/обновлении.
- **Инварианты:** терминальные записи (`booked`/`cancelled`/`expired`) не редактируются через `update_entry`; статус `booked` только через конвертацию в `BookingService`, не через PATCH.
- **`BookingService.create_admin_booking`:** блокировка строки waitlist до создания записи; при ошибке `mark_booked` — soft‑delete созданной записи и `ValueError` с `BOOKING_WAITLIST_CONVERSION_FAILED`; инвалидация кеша расписания по **фактическим** `doctor_id` / `appointment_date` после слияния с waitlist.
- **Отмена booking:** `notify_slot_freed` с `service_id` слота; учёт `QueuePolicy`: режим `sequential` → один кандидат, `broadcast` → `broadcast_size`; лимит `max_notifications_per_entry`; `FOR UPDATE SKIP LOCKED`; перевод в `notified` + `WaitlistNotification`.
- **Admin API:** `admin_waitlist.py` только через `WaitlistService`; query `include_booked`, `include_inactive`.
- **Метрики:** `waitlist_entries_total`, `waitlist_status_transitions_total`, `waitlist_slot_notify_total`, `waitlist_booking_conversion_total` (`src/core/metrics.py`).
- **Отчёт владельца:** в счётчик «в очереди» входят только `waiting` + `notified`.

### 8.2. Сделано (frontend)

- Хук `useAdminWaitlistEntries` с query‑параметрами списка; для панели расписания — выборка без `booked` (`includeBooked: false`).

### 8.3. Частично / вне v1

- Omnichannel/CRM, PWA‑API waitlist, Attention/Tasks по аномалиям, авто‑`expired`, «дыры» расписания без отмены booking, гистограммы времени ожидания — см. **«На потом»** в TASKS.

---

## 9. Связь с другими DEV_PROMPTS

- После реализации этого ARCH_DEV/DEV_PROMPT:
  - Booking/расписание получают предсказуемый слой waitlist;
  - Omnichannel/CRM могут работать с waitlist как с явным доменом (напоминания, предложения слотов);
  - DEV_PROMPT_OBS_CHAINS_023 и DEV_PROMPT_PERF_SPOTS_024 могут измерять влияние waitlist на заполнение расписания и перф.
