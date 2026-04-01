## 📊 ARCH_CRM_KANBAN — Sales & Kanban Pipeline

> Роли: @ARCH, @BIZ, @LEAD.  
> Цель: спроектировать CRM‑воронку продаж (Sales & Kanban) поверх существующих доменов Omnichannel/Booking/Payments **без реализации кода**.  
> Вход: `BUSINESS_LOGIC_CURRENT.md`, `BUSINESS_LOGIC_V2.md`, `TECH_PASSPORT_BACKEND.md`, `FUNCTIONAL_MAP_CURRENT.md`.

---

## 1. Задача и рамки модуля

- **Задача:** превратить текущий поток «чат ↔ запись ↔ оплата» в **прозрачную воронку продаж**:
  - каждый входящий контакт становится `LeadCard`;
  - каждая запись и оплата меняют состояние лида;
  - владелец видит объём денег на каждом этапе («думают», «записаны», «успешно завершено»).
- **Рамки Phase 1:**
  - один основной pipeline на клинику;
  - только B2C‑лиды (по пациентам/контактам) — без сложных B2B‑сделок;
  - без кастомных пользователем воронок (pipeline настраивает владелец/архитектура, UI может добавить позже).

---

## 2. Новые сущности домена CRM

### 2.1. LeadPipeline

- **Назначение:** описание воронки (набор стадий, порядок).
- **Ключевые поля (проектно):**
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `name: str` (например, «Основная воронка»);
  - `description: str | None`;
  - `is_default: bool` (у клиники может быть 0/1 default).

### 2.2. LeadStage

- **Назначение:** этап воронки.
- **Поля:**
  - `id: UUID`;
  - `pipeline_id: UUID` (FK → `LeadPipeline`);
  - `order: int` (позиция в колонках Kanban);
  - `code: str` (например, `new`, `qualified`, `booked`, `prepaid`, `completed`, `lost`);
  - `name: str` (label для UI);
  - `probability: int` (0–100, вероятность конверсии на этапе);
  - `color: str` (цвет тега/столбца в UI).

### 2.3. LeadCard

- **Назначение:** конкретная сделка/лид.
- **Связи:**
  - `clinic_id: UUID`;
  - `pipeline_id: UUID`;
  - `stage_id: UUID`;
  - `omnichannel_contact_id: UUID | None` — если лид пришёл из чата;
  - `patient_id: UUID | None` — если контакт уже переведён в пациента;
  - `primary_booking_id: UUID | None` — основной визит;
  - `bookings: list[UUID]` (реализуется через отдельную таблицу связей или поле `booking_ids`/`LeadBookingLink`);
  - `payments: list[UUID]` (аналогично, через `LeadPaymentLink`).
- **Бизнес‑поля:**
  - `title: str` (кратко: «Новое обращение: отбеливание»);
  - `source: str` (канал: `whatsapp`, `telegram`, `vk`, `landing`, `utm_xxx`);
  - `estimated_value: Decimal` — потенциальная выручка;
  - `actual_value: Decimal` — фактическая выручка (по успешным визитам/платежам);
  - `status: str` (`open`, `success`, `lost`);
  - `created_at: datetime`;
  - `updated_at: datetime`;
  - `closed_at: datetime | None`;
  - `lost_reason: str | None`.

### 2.4. Связанные сущности (расширения)

- `LeadNote`:
  - заметки менеджеров/админов по лиду;
  - связи: `lead_id`, `author_admin_id`, `created_at`, `text`.
- `LeadActivity` (опционально в Phase 1, можно использовать Omnichannel/Tasks):
  - лог активности: изменение стадий, привязка визитов, автоматические события.

---

## 3. Триггеры создания и движения лида

### 3.1. Создание LeadCard

**Триггер 1: новый OmnichannelContact**

- Условие:
  - создаётся новый `OmnichannelContact` (новый номер/аккаунт), ещё **не связанный** с `Patient`;
  - контакт принадлежит `clinic_id`.
- Действие:
  - создаётся `LeadCard`:
    - `pipeline_id` — default‑воронка клиники;
    - `stage` — первая стадия (`code="new"`);
    - `omnichannel_contact_id` — ссылка на контакт;
    - `title` — на основе имени/канала (если есть);
    - `source` — по каналу (`telegram`, `whatsapp`, и т.п.);
    - `estimated_value` = 0 (или базовый чек клиники, если настроен);
  - в Omnichannel‑UI:
    - для чата отображается бейдж стадии/суммы.

**Триггер 2: лид с лендинга**

- Источник: текущий лендинг `LANDING_WEB_FRONTEND` и форма `GetStarted`:
  - backend‑эндпоинт `/api/leads` уже существует (по техпаспорту лендинга).
- Действие:
  - создаётся отдельный `LeadCard` от лендинга:
    - `omnichannel_contact_id` может быть пустым;
    - `source` — на основе `meta`/utm.
  - дальнейшая конверсия:
    - при первом привязании контакта к Omnichannel/Patient — карта связывается с `omnichannel_contact_id`/`patient_id`.

### 3.2. Переходы стадий по событиям

**Событие: создан Booking для пациента/контакта**

- Условие:
  - создаётся `Booking` для `patient_id`;
  - существует открытый `LeadCard` с этим `patient_id` или `omnichannel_contact_id`.
- Действие:
  - если `LeadCard.stage.code` в одной из ранних стадий (`new`, `qualified`):
    - перенести на стадию `booked`;
    - `primary_booking_id` установить, если не было;
    - `estimated_value` обновить по стоимости услуги/услуг.

**Событие: внесена предоплата / оплата**

- Условие:
  - у `Booking` появляется успешный `Payment` (или статус `prepaid`);
  - связанный `LeadCard` существует.
- Действие:
  - при первом успешном платеже:
    - stage → `prepaid` (если выделяем такую стадию);
    - `actual_value` увеличить на сумму оплаты.

**Событие: завершение визита**

- Условие:
  - `Booking.status` → `completed`.
- Действие:
  - stage → `success`;
  - `actual_value` подтянуть из ERP‑блока (или стоимости услуги на первом этапе);
  - `status` → `success`, `closed_at=now`.
  - LTV пациента:
    - суммировать `actual_value` всех успешных LeadCard пациента в отдельном поле `patient.ltv` (или агрегировать в отчётах).

**Стратегия кодов стадий (Phase 1):**

- Рекомендуемые коды стадий воронки: `new` → `qualified` (опционально) → `booked` → `prepaid` → `success` или `lost`.
- Обработчики событий (`lead_event_handlers`) переводят лид по стадиям:
  - `ContactCreated` → лид в стадии `new`;
  - `BookingCreated` → при наличии открытого лида по patient/contact: стадия `booked`, проставление `primary_booking_id` и `estimated_value`;
  - `PaymentSuccess` → стадия `prepaid` (если есть такая в pipeline), обновление `actual_value`;
  - `BookingCompleted` → стадия `success`, `status="success"`, `closed_at`.
- Поиск лида по бронированию: репозиторий `get_lead_by_primary_booking_id(clinic_id, booking_id)` — прямой поиск без перебора списка.

**Событие: потерянный лид**

- Условие:
  - явная пометка админом («потерян»);
  - либо автоматический таймаут:
    - нет записей/ответов в течение N дней;
    - запись отменена без новой записи.
- Действие:
  - stage → `lost`;
  - `status` → `lost`, `closed_at=now`, `lost_reason` заполнен.

---

## 4. API и UI‑слой CRM Kanban

### 4.1. Backend API (проектно)

Новый роутер `src/api/v1/routers/admin_crm.py` (название уточнить при реализации):

- `GET /api/v1/admin/crm/pipelines`:
  - список воронок клиники.
- `GET /api/v1/admin/crm/stages`:
  - список стадий по pipeline.
- `GET /api/v1/admin/crm/leads`:
  - список `LeadCard`:
    - фильтры: `stage_id`, `date_range`, `source`, `assigned_admin_id?`, `search`.
- `GET /api/v1/admin/crm/leads/{id}`:
  - детали лида:
    - основной блок;
    - связанные записи/платежи;
    - заметки.
- `PATCH /api/v1/admin/crm/leads/{id}/stage`:
  - ручное перетаскивание карточки в другую стадию (Kanban drag&drop).
- `POST /api/v1/admin/crm/leads/{id}/notes`:
  - добавление заметки.

С привязкой к существующим доменам:

- READ‑часть использует join‑ы к `OmnichannelContact`, `Patient`, `Booking`, `Payment`.
- CREATE/UPDATE/DELETE ‑‑ стандартные CRUD‑операции по сущностям CRM.

### 4.2. Frontend (проектно)

Новая страница админки: `AdminSalesPipelinePage` (например, маршрут `/admin/sales`):

- **Левая панель:** фильтры:
  - период;
  - источник;
  - ответственный;
  - чекбоксы стадий.
- **Основная область:** Kanban‑доска:
  - колонки = `LeadStage` (отсортированы по `order`);
  - карточки = `LeadCard`:
    - отображают имя/контакт, стадию, оценку/факт, канал (иконка), теги;
    - drag&drop между колонками → PATCH stage.
- **Правая панель (drawer):** подробности лида:
  - контактная информация;
  - связанные записи/платежи;
  - заметки и история;
  - кнопки:
    - создать запись;
    - открыть чат;
    - изменить стадию/статус.

UX‑принципы:

- Использовать **плотный layout** и трёхколоночную структуру по аналогии с OmniChat (см. `Gemini_UX_frontend.md`).
- Карточки в колонках — стеклянные короткие блоки с ключевой информацией (имя, сумма, стадия).

---

## 5. Взаимодействие с AI Agent

- AI‑агент должен:
  - уметь читать ключевые поля текущего лида (стадия, ожидаемая сумма, была ли запись);
  - **не** менять стадии напрямую в Phase 1 — только предлагать админу действия (в сообщении/Task).
- В Phase 2+:
  - возможно добавить инструменты:
    - `update_lead_stage`;
    - `create_task_for_lead`.

---

## 6. Инварианты и ограничения

1. **Multi‑tenancy:** все сущности CRM (`LeadPipeline`, `LeadStage`, `LeadCard`, `LeadNote`) имеют `clinic_id`. Все запросы ограничены по текущей клинике.
2. **Согласованность с Booking/Payments:**
   - LeadCard не хранит дублирующие суммы — только кэш (`estimated_value`, `actual_value`), который можно пересчитать по данным ERP/Payments при необходимости.
3. **Слабая связность:**
   - Omnichannel, Booking, Payments **не импортируют** CRM‑модели напрямую;
   - связь идёт через сервисный слой и/или события (Domain Events / сервис‑вызовы).
4. **Безопасность данных:**
   - доступ к CRM‑API только у ролей `Owner`/`Manager`/`Admin` (точная матрица ⟶ `ARCH_RBAC_AND_TASKS.md`).

---

## 7. Следующие шаги для @ARCH/@BIZ

1. Уточнить минимальный набор стадий для default‑воронки (5–7 штук) и их вероятности.
2. Зафиксировать формат отчётов по CRM (что хочет видеть владелец: «деньги на этапе», конверсию, LTV).
3. Синхронизировать названия сущностей и полей с будущими ERP и Marketing Attribution:
   - чтобы UTM‑источники и финансовые транзакции можно было легко связать с `LeadCard`.
4. После согласования — подготовить `DEV_PROMPTS_CRM_KANBAN.md` с конкретными шагами реализации (схема БД, сервисы, роутеры, страницы).

