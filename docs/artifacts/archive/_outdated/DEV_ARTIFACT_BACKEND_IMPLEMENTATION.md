# DEV_ARTIFACT_BACKEND_IMPLEMENTATION — Промпт для @DEV: реализация недостающего бэкенда

> **Назначение:** Пошаговая реализация всех пунктов из `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_GAPS.md` с контрактами API и критериями приёмки. Выполнять по фазам B1 → B2 → B3 → B4 → B5 → B6.  
> **Для кого:** @DEV (бэкенд). Контекст задаёт @ARCH / @LEAD.

**Входы (обязательно открыть перед началом):**
- `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_GAPS.md` — полный список пробелов.
- `docs/ARCH_BACKEND_GAPS_STRUCTURED.md` — приоритеты и зависимости.
- `docs/DEV_MASTER_PROMPT.md` — что ожидает фронт.
- При необходимости: `docs/TPF_MODULE_ENTITIES.md`, `docs/BUSINESS_LOGIC_V2.md`, `TECH_PASSPORT_BACKEND` / `FUNCTIONAL_MAP_CURRENT`.

---

## Как пользоваться

1. Выполняй **фазы по порядку**: B1 → B2 → B3 → B4 → B5 → B6.
2. Внутри фазы — **шаги по порядку**. После каждого шага проверяй критерий.
3. Контракты (путь, метод, body, response) — соблюдать буквально; при расхождении с существующим кодом — согласовать с @ARCH.
4. Не дублировать уже реализованное: перед добавлением эндпойнта проверь `src/api/v1/routers/` и `src/application/services/`.

---

## Обязательные стандарты при реализации

При реализации каждого шага соблюдай **ENTERPRISE QUALITY** из `docs/ROLE_DEV.md` (раздел «ENTERPRISE QUALITY»): Edge Cases, Database Integrity, Validation, Audit & Logging. Архитектурные законы (multi-tenancy, soft delete, N+1, версионирование API) — в `docs/ROLE_ARCH.md`.

---

## Согласование путей и контекста

- В проекте часть роутеров использует **path** `.../clinics/{clinic_id}/...`, часть — только контекст из токена (`context.clinic_id`). При добавлении эндпойнта: если роутер уже под `prefix="/admin/clinics"` — использовать path `{clinic_id}` и проверять `path_clinic_id == context.clinic_id`; иначе брать clinic_id из контекста. При расхождении с артефактом — согласовать с @ARCH.
- Эндпойнты без clinic_id в пути (например `POST /admin/forms/send-link`): clinic_id брать из контекста авторизованного админа.

---

## Интеграции: заглушки и критерий готовности

- **WhatsApp/SMS (form send-link, check_expiring_packages):** если канал не настроен или не реализован — возвращать `sent: false`, URL отдавать; не включать «sent: true по WhatsApp» в критерий приёмки фазы до появления реальной интеграции. Статус зафиксировать в ARCH (например «ЗАГЛУШКА»).
- **AI (ai/agent, marketing/insights, generate-offers):** допускается заглушка (статичный ответ или пустой массив); контракт и путь — соблюдать для последующей подстановки реального вызова.

---

# Фаза B1 — Фундамент для Фазы 1 фронта (Summary, Form send-link)

**Цель:** Zero-Click Context (HoverCard) и отправка формы по ссылке из контекста пациента/записи.

---

## Шаг B1.1. Patient summary (для HoverCard)

**Файлы:** новый или существующий роутер пациентов под admin (например `src/api/v1/routers/patients.py` или `admin_patients` если есть), DTO.

**Действие:**
- Добавить эндпойнт `GET /api/v1/admin/patients/{patient_id}/summary` (или под префиксом admin/clinics/{clinic_id}/patients/{patient_id}/summary — по текущей структуре роутов).
- Ответ: лёгкий DTO, например `{ "id", "full_name", "phone", "ltv" (Decimal), "next_visit_at" (datetime | null), "next_visit_doctor_name" (string | null) }`. Данные брать из существующих репозиториев (Patient, отчёт/запрос по Booking для следующего визита, LTV из отчётов или расчёт на лету).
- ACL: только текущая клиника (clinic_id из контекста админа).

**Контракт (пример):**
```
GET /api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/summary
Response 200: { "id": "uuid", "full_name": "...", "phone": "...", "ltv": "0.00", "next_visit_at": "2025-03-20T14:00:00Z" | null, "next_visit_doctor_name": "..." | null }
Response 404: patient not found or not in clinic
```

**Проверка:** GET по существующему patient_id возвращает 200 и поля; по чужой клинике или несуществующему id — 404.

---

## Шаг B1.2. Doctor summary (для HoverCard)

**Файлы:** роутер врачей (admin), DTO.

**Действие:**
- Добавить `GET /api/v1/admin/clinics/{clinic_id}/doctors/{doctor_id}/summary`.
- Ответ: `{ "id", "full_name", "phone" | null, "specialization" | null }` — минимум для тултипа.

**Контракт (пример):**
```
GET /api/v1/admin/clinics/{clinic_id}/doctors/{doctor_id}/summary
Response 200: { "id": "uuid", "full_name": "...", "phone": null, "specialization": "..." }
Response 404: doctor not found or not in clinic
```

**Проверка:** Аналогично B1.1.

---

## Шаг B1.3. POST form/send-link (отправка формы по ссылке)

**Файлы:** `src/api/v1/routers/admin_forms.py`, сервис форм (например `FormsService` или новый метод), при необходимости интеграция с Omnichannel для отправки в WA/SMS.

**Действие:**
- Добавить эндпойнт `POST /api/v1/admin/forms/send-link` (или `POST /api/v1/admin/forms/send-link` под текущим префиксом admin/forms).
- Body: `{ "patient_id": "uuid" | null, "booking_id": "uuid" | null, "template_id": "uuid", "send_via": "whatsapp" | "sms" | "copy_only" }`. Хотя бы один из patient_id или booking_id обязателен.
- Логика: сгенерировать уникальный одноразовый (или с TTL) URL для заполнения формы (привязать к template_id + patient_id/booking_id); при send_via = whatsapp/sms — вызвать существующий канал отправки (если есть) или вернуть URL для ручной отправки; при copy_only — только вернуть URL.
- Response: `{ "url": "https://...", "sent": true | false, "channel": "whatsapp" | "sms" | null }`.

**Контракт (пример):**
```
POST /api/v1/admin/forms/send-link
Body: { "patient_id": "uuid"?, "booking_id": "uuid"?, "template_id": "uuid", "send_via": "whatsapp"|"sms"|"copy_only" }
Response 200: { "url": "https://...", "sent": true, "channel": "whatsapp" }
Response 422: validation error (missing patient_id/booking_id, invalid template)
```

**Проверка:** Запрос с template_id и patient_id возвращает url; при send_via=whatsapp и настроенном канале — sent: true (или заглушка sent: false с url).

---

## To-do B1

- [ ] GET patient summary для HoverCard.
- [ ] GET doctor summary для HoverCard.
- [ ] POST form/send-link с генерацией URL и опциональной отправкой.

**Критерий приёмки B1:** Фронт может запрашивать summary по patient/doctor и вызывать send-link для формы; контракты задокументированы.

---

# Фаза B2 — Фундамент для Фазы 2 фронта (Dashboard, Feed claim, Schedule, Waitlist)

**Цель:** Метрики дашборда (4 виджета), claim по Attention Feed, suggest-slots, создание брони из листа ожидания.

---

## Шаг B2.1. Dashboard: 4 метрики (записи сегодня, выручка, новые лиды, NPS/отмены)

**Файлы:** `src/application/dto/reports_dto.py`, `src/application/services/report_service.py`, роутер dashboard/reports.

**Действие:**
- Расширить DTO дашборда (или ответ dashboard-aggregate): добавить поля `new_leads_count` (int), `cancellations_count` (int), при возможности `nps_avg` (float | null) или отдельный виджет.
- В ReportService (или аналог) реализовать подсчёт: новые лиды за период (LeadCard по created_at), отмены (Booking status=cancelled за период). NPS — при наличии сущности отзывов.
- Убедиться, что эндпойнт `GET /admin/reports/dashboard-aggregate` (или по клинике) возвращает эти поля.

**Контракт (пример):**
```
GET /admin/reports/dashboard-aggregate?date=...&period=day&clinic_ids=...
Response: { ..., "new_leads_count": 3, "cancellations_count": 2, "nps_avg": 4.5 | null }
```

**Примечание:** Поле `nps_avg` опционально: до появления модуля отзывов/NPS допустимо всегда возвращать `null`. Фронт не должен показывать виджет NPS при `nps_avg === null`.

**Проверка:** Ответ содержит новые поля; значения соответствуют данным в БД.

---

## Шаг B2.2. Attention Feed: claim («Взять в работу»)

**Файлы:** `src/api/v1/routers/admin_attention_feed.py`, `src/application/services/attention_feed_service.py`.

**Фактический контракт (зафиксирован по коду):**
```
PATCH /api/v1/admin/clinics/{clinic_id}/attention-feed/items/claim
Body: { "item_type": "task" | "follow_up", "item_id": "uuid" }
Response 200: { "ok": true } (или пустой 200)
Response 404: item not found
Response 422: item_type must be task or follow_up
```

**Действие:** Реализация уже есть. Логика: при item_type=task — назначить задачу на текущего админа (assignee_id = current_admin.id); при follow_up — закрыть или назначить задачу. Фронт вызывает этот эндпойнт с body.

**Проверка:** Вызов claim по задаче из Feed назначает её на текущего пользователя.

---

## Шаг B2.3. Schedule: suggest-slots (идеальные окна)

**Файлы:** новый метод в `ScheduleService` или роутер `admin_schedule.py`.

**Действие:**
- Добавить `GET /api/v1/admin/clinics/{clinic_id}/schedule/suggest-slots?doctor_id=...&date=...&service_id=...` (service_id опционально).
- Возврат: список слотов (время начала/конца или slot_id), где есть «дыры» в расписании (алгоритм на основе уже занятых слотов). Можно вызывать существующий get_aggregated_schedule и на фронте фильтровать свободные; если нужна логика «идеальных» окон (минимальные дыры) — реализовать в сервисе.

**Контракт (пример):**
```
GET /api/v1/admin/clinics/{clinic_id}/schedule/suggest-slots?doctor_id=uuid&date=2025-03-20&service_id=uuid
Response 200: { "slots": [ { "start": "09:00", "end": "09:30" }, ... ] }
```

**Проверка:** Для врача с занятым расписанием возвращаются свободные слоты на дату.

---

## Шаг B2.4. Создание брони из листа ожидания (Waitlist → Booking)

**Файлы:** `src/api/v1/routers/bookings.py` или admin bookings, `src/application/services/booking_service.py`, при необходимости `admin_waitlist.py`.

**Действие:**
- В тело `POST /api/v1/admin/bookings` (или эквивалент создания брони админом) добавить опциональное поле `waitlist_entry_id: uuid`.
- При наличии waitlist_entry_id: загрузить WaitlistEntry, взять patient_id, при необходимости doctor_id, preferred_date/time; создать бронь с этими данными; обновить или удалить запись листа (например status=converted или удалить из листа).
- ACL: клиника записи листа = клиника брони = clinic_id админа.

**Контракт (пример):**
```
POST /api/v1/admin/bookings (или /admin/clinics/{clinic_id}/bookings)
Body: { "patient_id": "uuid", "doctor_id": "uuid", "service_id": "uuid", "date": "...", "time": "...", "waitlist_entry_id": "uuid"? }
При waitlist_entry_id: patient_id/doctor_id могут быть подставлены из листа; после создания брони waitlist entry помечается использованным.
Response 201: booking DTO
Response 404: waitlist entry not found
```

**Проверка:** Создание брони с waitlist_entry_id создаёт бронь и обновляет лист.

---

## To-do B2

- [ ] Dashboard: new_leads_count, cancellations_count, nps_avg (если есть данные).
- [ ] PATCH/POST attention-feed claim.
- [ ] GET schedule/suggest-slots.
- [ ] POST bookings с waitlist_entry_id.

**Критерий приёмки B2:** Фронт получает 4 метрики, может вызвать claim, запросить suggest-slots и создать бронь из листа.

---

# Фаза B3 — Богатые карточки сущностей (Фаза 3 фронта)

**Цель:** Один или минимальное число запросов для отрисовки карточек Patient, Booking, Doctor, Service по вкладкам (TPF_MODULE_ENTITIES).

---

## Шаг B3.1. Rich Patient (вкладки: Основное, Визиты, Финансы, Медкарта, Коммуникации)

**Файлы:** роутер пациентов (admin), сервис/репозиторий, DTO.

**Действие:**
- Добавить эндпойнт `GET /api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/card` (или расширить существующий GET patient/{id}) с опциональным query `?include=visits,finances,notes,comms` или отдавать всё одним ответом.
- Response: Patient + вложенные или отдельные списки: visits (bookings с датой, врач, услуга, статус, сумма, NPS), finances (платежи, возвраты, абонементы), notes/медкарта, коммуникации (история уведомлений). Формат по TPF_MODULE_ENTITIES.

**Контракт (пример):**
```
GET /api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/card
Response 200: {
  "patient": { "id", "full_name", "phone", "email", "ltv", "bonus_balance", "tags": [], ... },
  "visits": [ { "id", "date", "doctor_name", "service_name", "status", "amount", "nps" }, ... ],
  "finances": [ { "type": "payment"|"refund", "amount", "date", ... }, ... ],
  "notes": [ ... ],
  "comms": [ ... ]
}
```

**Проверка:** Один запрос возвращает данные для всех вкладок карточки пациента.

---

## Шаг B3.1.1. Мини-лента сообщений по пациенту (вкладка Коммуникации)

**Файлы:** `src/api/v1/routers/admin_clinics_summary.py` или `admin_chat.py`, ChatService / привязка patient → contact → conversation.

**Действие:**
- Добавить эндпойнт `GET /api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/messages?limit=20&cursor=...` (cursor опционально).
- Логика: по patient_id найти contact (или conversation), связанный с пациентом; вернуть последние сообщения этого диалога (тот же формат, что у `GET .../conversations/{conversation_id}/messages`). ACL: только клиника админа.
- Response: список сообщений (id, role, content, created_at и т.д.) для мини-ленты во вкладке «Коммуникации» карточки пациента.

**Контракт (пример):**
```
GET /api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/messages?limit=20&cursor=
Response 200: { "items": [ MessageDto, ... ], "next_cursor": "..." | null }
Response 404: patient not found or not in clinic
```

**Проверка:** Для пациента с диалогом возвращаются последние сообщения; при отсутствии диалога — пустой items.

---

## Шаг B3.2. Rich Booking (вкладки: Детали, Услуги и чек, Расходники, Задачи)

**Файлы:** роутер бронирований, сервис, DTO.

**Действие:**
- `GET /api/v1/admin/bookings/{booking_id}/card` (с проверкой clinic_id) или расширить GET booking/{id}: детали (пациент, врач, кабинет, время, статус), услуги и чек, расходники по техкарте, задачи привязанные к визиту.

**Контракт (пример):**
```
GET /api/v1/admin/bookings/{booking_id}/card
Response 200: { "booking": {...}, "services": [...], "consumables": [...], "tasks": [...] }
```

**Проверка:** Данные для вкладок возвращаются одним запросом.

---

## Шаг B3.3. Rich Doctor и Rich Service

**Действие:** Аналогично B3.1–B3.2:
- **Doctor:** GET .../doctors/{id}/card: профиль, расписание (working_hours), зарплата (payroll_policy), услуги (service_doctor).
- **Service:** GET .../services/{id}/card: описание, исполнители (service_doctor), техкарта (consumables), флаги онлайн-записи.

**Проверка:** Один запрос на сущность даёт данные для всех вкладок Drawer.

---

## To-do B3

- [ ] GET patient card (rich).
- [ ] GET booking card (rich).
- [ ] GET doctor card (rich).
- [ ] GET service card (rich).

**Критерий приёмки B3:** Фронт может строить карточки Patient, Booking, Doctor, Service без лишних запросов.

---

# Фаза B4 — CRM, задачи, финансы, Checkout (Фаза 4 фронта)

**Цель:** Агрегаты по этапам CRM, фильтр и claim задач, POST финансовых транзакций, контракт Checkout Hub (подходящие абонементы + опционально use_subscription_id при complete).

---

## Шаг B4.1. CRM: суммы по этапам (для шапки Kanban)

**Файлы:** `src/api/v1/routers/admin_crm.py`, LeadService или отчёт.

**Действие:**
- Добавить в ответ `GET /admin/crm/stages` (или отдельный `GET /admin/crm/stages/aggregates?pipeline_id=...`) агрегаты по каждому stage_id: `count` (число лидов), `sum_estimated_value` (сумма estimated_value). Либо расширить LeadListResponse при запросе по stage — отдавать агрегат в заголовке.

**Контракт (пример):**
```
GET /api/v1/admin/crm/stages?pipeline_id=uuid
Response 200: [
  { "id": "uuid", "name": "Думают", "order": 1, "leads_count": 5, "sum_estimated_value": "150000.00" },
  ...
]
```

**Проверка:** В ответе stages есть leads_count и sum_estimated_value по каждому этапу.

---

## Шаг B4.2. Задачи: фильтр source=ai и POST claim

**Файлы:** `src/api/v1/routers/admin_tasks.py`, TaskService.

**Действие:**
- В `GET /admin/tasks` добавить query-параметр `source=ai` (или source=ai_suggested — по полю в Task). Фильтровать задачи по task.source.
- Добавить `POST /admin/tasks/{task_id}/claim`: назначить задачу на текущего пользователя (assignee_id = current_admin.id). Только для задач с source=ai (или без ограничения — уточнить у @ARCH).

**Контракт (пример):**
```
GET /api/v1/admin/tasks?source=ai
Response 200: [ TaskResponse, ... ]

POST /api/v1/admin/tasks/{task_id}/claim
Response 200: TaskResponse (updated)
Response 404: task not found
```

**Проверка:** Список с source=ai возвращает только AI-задачи; claim назначает задачу на себя.

---

## Шаг B4.3. POST finance/transactions (Внести, Изъять, Перевод)

**Файлы:** `src/api/v1/routers/admin_finance.py`, `src/application/services/finance_service.py`, DTO (FinancialTransactionCreate).

**Действие:**
- Добавить DTO `FinancialTransactionCreate`: cashbox_id, amount, type (income|expense|transfer), category (string); для type=transfer — from_cashbox_id, to_cashbox_id (и amount).
- Добавить `POST /api/v1/admin/clinics/{clinic_id}/finance/transactions`. Валидация: обязательные поля (Relational Integrity); при transfer — два cashbox в одной клинике. Вызов существующего FinanceService.create_transaction (или расширить сервис).

**Контракт (пример):**
```
POST /api/v1/admin/clinics/{clinic_id}/finance/transactions
Body (income/expense): { "cashbox_id": "uuid", "amount": "1000.00", "type": "income", "category": "Оплата услуги" }
Body (transfer): { "from_cashbox_id": "uuid", "to_cashbox_id": "uuid", "amount": "5000.00", "type": "transfer", "category": "Перевод" }
Response 201: FinancialTransactionRead
Response 422: validation error
```

**Проверка:** Создание транзакции income/expense/transfer обновляет баланс (или учёт); 422 при пустых обязательных полях.

---

## Шаг B4.4. Checkout Hub: подходящие абонементы и use_subscription_id при complete

**Файлы:** `src/application/services/booking_service.py`, `src/application/services/loyalty_service.py`, роутер бронирований (complete).

**Действие:**
- Добавить эндпойнт `GET /api/v1/admin/bookings/{booking_id}/checkout-info` (или включить в GET booking/{id}/card): возвращать список «подходящих» активных пакетов пациента для этого визита (услуги брони входят в пакет, остаток > 0). DTO: subscription_id, package_name, remaining_visits | remaining_amount.
- В вызов `complete_booking` (или PATCH/POST booking complete) добавить опциональный параметр `use_subscription_id: uuid`. При передаче — вызывать `loyalty_service.use_subscription_for_booking(booking_id, subscription_id, ...)` и не создавать платёж наличными/картой за эту сумму (или создавать с пометкой paid_by_subscription).

**Контракт (пример):**
```
GET /api/v1/admin/bookings/{booking_id}/checkout-info
Response 200: { "eligible_subscriptions": [ { "customer_subscription_id": "uuid", "package_name": "...", "remaining_visits": 5, "remaining_amount": null }, ... ] }

POST/PATCH .../bookings/{booking_id}/complete
Body: { "use_subscription_id": "uuid"? }  // опционально
Response 200: BookingRead
```

**Проверка:** checkout-info возвращает список пакетов; complete с use_subscription_id списывает визит с пакета (SubscriptionUsage создаётся).

---

## Шаг B4.5. AI Marketing Advisor (заглушка или контракт)

**Файлы:** новый роутер или в admin_marketing_attribution, сервис (заглушка или вызов AI).

**Действие:**
- Добавить `GET /api/v1/admin/clinics/{clinic_id}/marketing/insights` или `POST /api/v1/ai/marketing-insights` (clinic_id в контексте). Пока заглушка: возврат статичного списка строк-рекомендаций или пустой массив. В перспективе — вызов AI по данным UTM/воронки.

**Контракт (пример):**
```
GET /api/v1/admin/clinics/{clinic_id}/marketing/insights
Response 200: { "insights": [ "Акция X принесла 12 записей.", "VK конвертирует хуже, чем Telegram." ] }
```

**Проверка:** Эндпойнт возвращает 200 и массив (пустой или заглушка).

---

## To-do B4

- [ ] CRM stages с агрегатами count и sum_estimated_value.
- [ ] GET tasks?source=ai и POST tasks/{id}/claim.
- [ ] POST finance/transactions (income, expense, transfer).
- [ ] GET bookings/{id}/checkout-info (eligible_subscriptions); complete_booking(use_subscription_id).
- [ ] GET marketing/insights (заглушка или контракт).

**Критерий приёмки B4:** Фронт может отображать суммы в Kanban, работать с AI-задачами и claim, создавать ручные транзакции, показывать в Checkout подходящие абонементы и завершать визит с списанием с пакета.

---

# Фаза B5 — Дифференциаторы (Фаза 5 фронта)

**Цель:** Глобальный поиск (Spotlight), AI Command Line, виджет спасённой выручки, Retention AI, Omni-Vault (медиа, экспорт, бэкап).

---

## Шаг B5.1. GET admin/search (глобальный поиск)

**Файлы:** новый роутер `admin_search.py` или в существующем admin, сервис поиска.

**Действие:**
- `GET /api/v1/admin/search?q=...&limit=10` (или под префиксом admin/clinics/{clinic_id}/search). Контекст: clinic_id из токена/сессии.
- Возврат: секции (навигация по разделам — статичный список роутов) + пациенты (id, full_name, phone — по LIKE по имени/телефону) + записи (id, patient_name, date — по фильтру). Ограничить limit, права только своей клиники.

**Контракт (пример):**
```
GET /api/v1/admin/search?q=Иван&limit=10
Response 200: {
  "sections": [ { "label": "Дашборд", "path": "/admin" }, ... ],
  "patients": [ { "id": "uuid", "full_name": "...", "phone": "..." }, ... ],
  "bookings": [ { "id": "uuid", "patient_name": "...", "date": "..." }, ... ]
}
```

**Проверка:** Поиск по подстроке возвращает пациентов и записи своей клиники.

---

## Шаг B5.2. POST ai/agent (AI Command Line для Spotlight)

**Файлы:** новый роутер (например `ai_agent.py` или в admin_ai_*), вызов существующего AI/orchestrator с function-calling.

**Действие:**
- `POST /api/v1/ai/agent` (или `/api/v1/admin/ai/command`). Body: `{ "text": "записать Иванова на завтра к терапевту" }`. Контекст: clinic_id, admin_id из токена.
- Вызвать AI-агента с function-calling (как в omnichannel), передать text; вернуть ответ агента (текст + опционально список выполненных действий). Rate limit (например по clinic_id).

**Контракт (пример):**
```
POST /api/v1/ai/agent
Body: { "text": "..." }
Response 200: { "reply": "Записал Иванова на 10:00 завтра к терапевту.", "actions": [ { "tool": "create_booking", "result": "ok" } ] }
Response 429: rate limit
```

**Проверка:** Запрос с текстом возвращает ответ агента; при перегрузке — 429.

---

## Шаг B5.3. Виджет «Спасённая выручка (AI)»

**Файлы:** отчёт/агрегат дашборда или отдельный эндпойнт, Celery/фоновый процесс Revenue Hunter (если ещё нет — заглушка).

**Действие:**
- Добавить поле в ответ dashboard-aggregate или `GET /api/v1/admin/clinics/{clinic_id}/reports/revenue-saved-by-ai`: значение «выручка, спасённая ИИ за ночь» (из расчёта или из таблицы/кеша, заполняемой Celery). При отключённом Revenue Hunter возвращать null или не отдавать эндпойнт.

**Контракт (пример):**
```
GET /api/v1/admin/clinics/{clinic_id}/reports/revenue-saved-by-ai
Response 200: { "amount": "5000.00", "period": "night" } | { "amount": null, "period": "night" }
```

**Примечание:** При отключённом Revenue Hunter или отсутствии расчёта возвращать `amount: null`. Фронт отображает виджет только при `amount !== null`.

**Проверка:** При наличии данных возвращается сумма; иначе null.

---

## Шаг B5.4. Retention: AI-сегменты, generate-offers, ROI кампании

**Файлы:** расширение admin_recall или новый модуль retention, сервисы.

**Действие:**
- API сегментов (в т.ч. предопределённые «На грани ухода», «Охотники за скидками» и т.д.): `GET /api/v1/admin/clinics/{clinic_id}/retention/segments` — список сегментов с count пациентов.
- `POST /api/v1/ai/generate-offers` (или под admin): body segment_id / cohort; возврат списка персональных офферов (заглушка или вызов AI).
- Статистика кампании с воронкой до «Оплатили в кассу»: расширить существующий отчёт recall/кампаний или добавить `GET .../retention/campaigns/{id}/roi` с этапами и конверсиями.

**Контракт:** Зафиксировать в TECH_PASSPORT_BACKEND; минимально — эндпойнты возвращают 200 и структуру (пустую или заглушку).

**Проверка:** Эндпойнты доступны и возвращают данные по контракту.

---

## Шаг B5.5. Omni-Vault: медиа, Export Builder, Full Backup

**Файлы:** новые роутеры/сервисы.

**Действие:**
- **Медиа:** `GET /api/v1/admin/media` (или под clinics/{id}/media): полиморфная привязка к patient_id, booking_id, message_id; фильтры type, date_from, date_to. Возврат списка медиа-ресурсов с URL (или подписанным URL).
- **Export Builder:** `POST /api/v1/admin/export`: body columns[], format=excel|csv, entity_type=patients|bookings|...; генерация файла (фоново или синхронно с лимитом); возврат ссылки на скачивание или поток.
- **Full Backup:** `POST /api/v1/admin/backup/request` — постановка задачи Celery на создание бэкапа; `GET /api/v1/admin/backup/status` — статус и ссылка на скачивание (например в Telegram). Контракт: task_id, status, download_url при готовности.

**Контракт:** Описать пути и форматы в отдельном параграфе TECH_PASSPORT_BACKEND или в этом артефакте.

**Проверка:** Медиа возвращает список; Export возвращает файл/ссылку; Backup ставит задачу и возвращает статус.

---

## To-do B5

- [ ] GET admin/search (sections + patients + bookings).
- [ ] POST ai/agent (AI Command Line).
- [ ] Виджет revenue-saved-by-ai.
- [ ] Retention: segments, generate-offers, ROI.
- [ ] Медиа, Export Builder, Full Backup.

**Критерий приёмки B5:** Spotlight и дифференциаторы фронта получают данные по контрактам.

---

## Шаг B5.6. Owner Morning Brief и AI Supervisor Summary (интеграции для владельца)

**Источник:** `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md` (разделы Owner's Morning Brief и AI Supervisor). Фаза 5 фронта (DEV_MASTER_PROMPT шаг 5.6).

**Файлы:** Celery Beat (расписание), задачи в `src/infrastructure/messaging/tasks/` или аналог, интеграция с Telegram Bot API.

### Owner Morning Brief

- **Расписание:** 09:00 (по техпаспорту), ежедневно по времени клиники/владельца.
- **Содержание:** касса за вчера, динамика к предыдущему периоду, записи на сегодня, алерты (заканчивается расходник и т.п.).
- **Реализация:** Celery Beat — задача `send_owner_morning_brief`; для каждой клиники (или владельца) с включённой настройкой: агрегация данных (отчёты, касса, остатки), формирование сообщения (текст/Markdown), отправка в Telegram (Bot API `sendMessage` по `chat_id` владельца).
- **Контракт настроек (при необходимости в админке):** время рассылки (cron expression или время), вкл/выкл, `telegram_chat_id` владельца. Хранить в настройках клиники или отдельной таблице `owner_integration_settings`.

### AI Supervisor Summary

- **Расписание:** вечер (по техпаспорту — после окончания рабочего дня).
- **Содержание:** «админ проигнорировал N алертов», потерянная выручка, время реакции на сообщения (среднее/по операторам).
- **Реализация:** Celery Beat — задача `send_ai_supervisor_summary`; агрегация данных из Attention Feed, логов назначений, отмен, выручки за день; формирование отчёта; отправка в Telegram получателям (настройка: вкл/выкл, список `telegram_chat_id`).

### Контракты (фиксация для реализации)

| Интеграция              | Триггер     | Входные данные                         | Выход                    |
|-------------------------|------------|----------------------------------------|--------------------------|
| Owner Morning Brief     | Celery 09:00 | clinic_id, date_yesterday, date_today | Telegram sendMessage     |
| AI Supervisor Summary   | Celery вечер | clinic_id, date_today, attention/omni stats | Telegram sendMessage     |

**Проверка:** При реализации — утренняя/вечерняя отправка срабатывает по расписанию; настройки (если вынесены в админку) сохраняются. Контракты не требуют REST API для фронта; при необходимости UI настроек — эндпойнты вида `GET/PATCH /api/v1/admin/clinics/{id}/integration-settings` (owner_morning_brief_enabled, owner_telegram_chat_id, ai_supervisor_enabled, ai_supervisor_telegram_chat_ids).

---

# Фаза B6 — Loyalty & Wealth Engine (детали Gemini)

**Цель:** FamilyLink, Liability Dashboard, Celery check_expiring_packages, типы COUNT-BASED/BALANCE-BASED, Digital Pass (PWA) — по сценарию из DEV_ARTIFACT_BACKEND_GAPS Part 2.

---

## Шаг B6.1. FamilyLink (семейный шеринг пакетов)

**Файлы:** миграция (новая таблица), сущность, репозиторий, LoyaltyService, роутеры admin_loyalty и patient_loyalty.

**Действие:**
- Таблица `package_family_links`: id, customer_subscription_id (FK), patient_id (FK) — «кому разрешено тратить с этого пакета». Владелец пакета (CustomerSubscription.patient_id) по умолчанию имеет доступ; дополнительные patient_id — члены семьи.
- API: `POST /api/v1/admin/loyalty/subscriptions/{subscription_id}/family-members` body { "patient_id": "uuid" }; `DELETE .../family-members/{patient_id}`. Список: в GET customer-subscriptions/{id} включить shared_with: [ { patient_id, patient_name } ].
- При списании с пакета проверять: текущий patient визита = владелец пакета ИЛИ в family_links. В LoyaltyService.select_subscription_for_booking / use_subscription_for_booking учитывать shared_with.

**Контракт (пример):**
```
POST /api/v1/admin/loyalty/subscriptions/{subscription_id}/family-members
Body: { "patient_id": "uuid" }
Response 201: { "ok": true }
GET .../customer-subscriptions/{id} → включить "shared_with": [ { "patient_id": "uuid", "patient_name": "..." } ]
```

**Проверка:** Добавление члена семьи сохраняется; при визите «члена семьи» пакет доступен для списания.

---

## Шаг B6.2. Liability Dashboard (Unearned Revenue)

**Файлы:** отчёт/финансы, роутер admin_finance или reports.

**Действие:**
- `GET /api/v1/admin/clinics/{clinic_id}/finance/liability`: агрегат «деньги в воздухе» — сумма остатков по активным CustomerSubscription. Для COUNT-BASED: remaining_visits * (price / total_visits) пакета; для BALANCE-BASED: remaining_amount. Суммировать по клинике.

**Контракт (пример):**
```
GET /api/v1/admin/clinics/{clinic_id}/finance/liability
Response 200: { "unearned_revenue": "150000.00", "active_subscriptions_count": 12 }
```

**Проверка:** Сумма соответствует сумме остатков активных пакетов.

---

## Шаг B6.3. Celery check_expiring_packages (AI-угроза сгорания)

**Файлы:** Celery-задача (например в `src/infrastructure/messaging/tasks/` или loyalty_tasks.py), интеграция с Omnichannel/WhatsApp.

**Действие:**
- Задача `check_expiring_packages`: раз в день (cron) выбирать CustomerSubscription с expires_at через N дней (например 14), по клинике; для каждого пациента сформировать персонализированное сообщение (шаблон + данные пакета) и отправить через существующий канал (WhatsApp и т.д.) или поставить в очередь сообщений. Параметр N — из настроек клиники или константа.

**Контракт:** Задача не возвращает HTTP; логирование и метрики. Текст сообщения: по шаблону из DEV_ARTIFACT_BACKEND_GAPS («У вас сгорят 2 массажа через 2 недели! Давайте найдём окно?»).

**Проверка:** Запуск задачи вручную или по расписанию создаёт отправки/записи в очереди для пакетов с expires_at в заданном окне.

---

## Шаг B6.4. Типы пакетов COUNT-BASED / BALANCE-BASED

**Файлы:** SubscriptionPackage, `src/application/dto/loyalty_dto.py` (SubscriptionPackageCreate/Update), `src/api/v1/routers/admin_loyalty.py`, LoyaltyService.

**Действие:**
- Допустимые значения `kind`: `COUNT_BASED`, `BALANCE_BASED`. В API создания/обновления пакета валидировать: при kind=COUNT_BASED поле total_visits обязательно (и > 0); при kind=BALANCE_BASED поле total_amount обязательно (и > 0). При нарушении возвращать 422 с деталью по полю.
- В контрактах и документации использовать COUNT_BASED / BALANCE_BASED.

**Проверка:** Создание пакета с kind=COUNT_BASED без total_visits — 422; kind=BALANCE_BASED без total_amount — 422.

---

## Шаг B6.5. PWA Digital Pass (карточка абонемента)

**Файлы:** patient_loyalty API (уже есть), проверить DTO.

**Действие:**
- Убедиться, что ответ `GET /api/v1/patient/loyalty/subscriptions` (или аналог) содержит для каждого абонемента: name, remaining_visits/total_visits или remaining_amount/total_amount, expires_at, services_included (или service_ids) — для кнопки «Записаться по абонементу» и фильтра услуг в мастере записи. При необходимости расширить DTO.

**Проверка:** PWA получает достаточно данных для отображения карточки и фильтра услуг.

---

## To-do B6

- [ ] FamilyLink: таблица, API, учёт при списании.
- [ ] GET finance/liability (Unearned Revenue).
- [ ] Celery check_expiring_packages + отправка напоминаний.
- [ ] COUNT-BASED / BALANCE-BASED в пакетах.
- [ ] Patient loyalty API: данные для Digital Pass.

**Критерий приёмки B6:** Loyalty Engine по сценарию Gemini: семейный шеринг, дашборд обязательств, AI-напоминания о сгорании, типы пакетов, PWA-карточка.

---

# Интеграции для владельца (Фаза 5.6 фронта: Owner Morning Brief, AI Supervisor)

**Источник:** `docs/DEV_MASTER_PROMPT.md` (шаг 5.6), `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md` (Owner's Morning Brief, AI Supervisor).

При реализации — контракты и расписание ниже; при отсутствии бэкенда — добавить по шагам.

---

## Owner Morning Brief (утренняя сводка в Telegram)

**Содержание:** Касса за вчера, динамика, записи на сегодня, алерты (например заканчивается расходник). Время по техпаспорту — 09:00.

**Реализация:**
- Celery Beat: задача по расписанию (cron 0 9 * * * или настраиваемое время).
- Формирование сообщения: агрегаты по клинике (выручка вчера, сравнение с позавчера; количество записей на сегодня; список алертов из склада/расходников).
- Отправка в Telegram: Bot API `sendMessage(chat_id, text)` или webhook. `chat_id` владельца — из настроек клиники или отдельной таблицы `owner_telegram_settings` (clinic_id, chat_id, morning_brief_enabled, morning_brief_time_utc).

**Контракт (внутренний):**
- Задача: `tasks.send_owner_morning_brief(clinic_id)`.
- Настройки (опционально в админке): GET/PATCH `admin/clinics/{id}/settings/owner-brief` → `{ "enabled": true, "send_at_utc": "06:00", "telegram_chat_id": "..." }`. При отсутствии настроек — не отправлять или использовать дефолтный chat_id из конфига.

**Проверка:** По расписанию или ручной запуск задачи отправляет сообщение в Telegram.

---

## AI Supervisor Summary (вечерний отчёт владельцу)

**Содержание:** «Админ проигнорировал 3 алерта», потерянная выручка, время реакции на сообщения. По техпаспорту — вечерняя отправка.

**Реализация:**
- Celery Beat: задача по расписанию (например 20:00).
- Агрегация за день: количество необработанных алертов из Attention Feed; метрики по ответам в чате (среднее время ответа, пропущенные диалоги); выручка потерянная (отмены, no-show с оценкой).
- Отправка в Telegram (тот же или отдельный chat_id).

**Контракт (внутренний):**
- Задача: `tasks.send_ai_supervisor_summary(clinic_id)`.
- Настройки (опционально): GET/PATCH `admin/clinics/{id}/settings/ai-supervisor` → `{ "enabled": true, "send_at_utc": "17:00", "recipient_chat_ids": ["..."] }`.

**Проверка:** По расписанию или ручной запуск формирует и отправляет отчёт.

---

## To-do интеграций владельца

- [ ] Celery задача Owner Morning Brief (расписание, формирование текста, отправка в Telegram).
- [ ] Celery задача AI Supervisor Summary (агрегаты, отправка в Telegram).
- [ ] (Опционально) Настройки в админке: время рассылки, вкл/выкл, chat_id; при наличии — эндпойнты GET/PATCH для owner-brief и ai-supervisor.

**Критерий приёмки:** При реализации — утренняя и вечерняя отправка работают по расписанию; настройки (если реализованы) сохраняются.

---

# Сводка и порядок выполнения

| Фаза | Содержание | Критерий приёмки |
|------|------------|------------------|
| **B1** | Patient/Doctor summary, POST form/send-link | Фронт Zero-Click и отправка формы по ссылке |
| **B2** | Dashboard 4 метрики, Feed claim, suggest-slots, booking from waitlist | Фронт дашборд, Feed, расписание, лист ожидания |
| **B3** | Rich Patient/Booking/Doctor/Service card | Фронт карточки без лишних запросов |
| **B4** | CRM aggregates, Tasks source+claim, POST transactions, Checkout eligible + use_subscription_id, Marketing insights | Фронт CRM, задачи, финансы, Checkout Hub |
| **B5** | search, ai/agent, saved revenue, Retention, Media, Export, Backup | Фронт Spotlight и дифференциаторы |
| **B6** | FamilyLink, Liability, check_expiring_packages, COUNT/BALANCE, Digital Pass | Loyalty Engine по Gemini |

---

# Ревью: соответствие ENTERPRISE QUALITY и полнота

**Проверено @ARCH.** Ниже — что учтено в артефакте и что доработано для гладкой реализации.

| Аспект | Статус | Комментарий |
|--------|--------|-------------|
| **ENTERPRISE QUALITY GATE** | ✅ В ROLE_DEV | Требования Edge Cases, Database Integrity, Validation, Audit & Logging вынесены в `docs/ROLE_DEV.md` (раздел «ENTERPRISE QUALITY»); в артефакте — ссылка на ROLE_DEV. |
| **Архитектурные законы** | ✅ В ROLE_ARCH | Multi-tenancy, soft delete, N+1, версионирование API — в `docs/ROLE_ARCH.md`; в артефакте — ссылка. |
| **Контракты API** | ✅ Учтено | Путь, метод, body, response, 404/422 — заданы по фазам B1–B6; при расхождении с кодом — согласование с @ARCH. |
| **Пути и clinic_id** | ✅ Учтено | Добавлено согласование: path vs context.clinic_id в зависимости от префикса роутера; проверка path_clinic_id == context.clinic_id. |
| **Интеграции (WA/SMS, AI)** | ✅ Учтено | Явно разрешены заглушки; критерий приёмки фазы не требует «sent: true» до появления реального канала; AI — заглушка по контракту. |
| **Финансы и гонки** | ✅ Учтено | Для POST transactions и complete_booking с use_subscription_id указано использование with_for_update и rollback при ошибках. |
| **Покрытие пробелов** | ✅ Полное | Все пункты из DEV_ARTIFACT_BACKEND_GAPS и ARCH_BACKEND_GAPS_STRUCTURED отражены в шагах B1–B6; сводная таблица фаз приведена выше. |
| **Тесты** | ⚠️ Отдельно | Проектирование тестов — по документу ARCH_TESTS.md (создаётся @ARCH после стабилизации API). В артефакте критерии «Проверка» дают ориентир для ручной проверки и будущих автотестов. |
| **Пагинация и лимиты** | ⚠️ По контракту | Где в контракте указан limit (например search?limit=10) — соблюдать; для списков без явного limit ориентироваться на существующие эндпойнты проекта (page_size и т.д.). |

**Итог:** Артефакт приведён в соответствие с ENTERPRISE QUALITY; детальные требования — в `docs/ROLE_DEV.md` и `docs/ROLE_ARCH.md`. При реализации @DEV обязан следовать им в дополнение к шагам фаз.

---

# Ссылки

- **Источник пробелов:** `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_GAPS.md`
- **Приоритеты и зависимости:** `docs/ARCH_BACKEND_GAPS_STRUCTURED.md`
- **Ожидания фронта:** `docs/DEV_MASTER_PROMPT.md`
- **ENTERPRISE QUALITY и законы:** `docs/ROLE_DEV.md` (раздел «ENTERPRISE QUALITY»), `docs/ROLE_ARCH.md` (архитектурные законы)

---

*Выполняй фазы по порядку, шаги внутри фазы — по порядку. Контракты соблюдать; при отсутствии указания — спрашивать @ARCH/@LEAD.*
