## DEV_PROMPTS_CRM_KANBAN — Реализация Sales & Kanban Pipeline

> Роли: @DEV, @ARCH, @QA.  
> Читается после: `BUSINESS_LOGIC_V2.md`, `ARCH_CRM_KANBAN.md`, `TECH_PASSPORT_BACKEND.md`, `TECH_PASSPORT_FRONTEND.md`, `ARCH_CROSSCUT_EVENT_CONTEXT_AI.md`.

---

## 1. Цели реализации

- Добавить CRM‑воронку продаж поверх существующих Omnichannel/Booking/Payments:
  - фиксировать каждый новый контакт/лид;
  - отслеживать движение «Новое обращение → Записан → Предоплата → Успех/Потеряно»;
  - считать суммы по этапам и давать удобный Kanban‑интерфейс в админке.
- Интегрировать CRM с:
  - доменными событиями (`BookingCreated`, `BookingCompleted`, `PaymentSuccess`, `ContactCreated`);
  - AI‑агентом (видимость стадии лида и суммы в боковой панели чата).

---

## 2. Backend — модель данных и миграции

### 2.1. Создать сущности в домене

- Добавить файлы в `src/domain/entities/`:
  - `lead_pipeline.py`
  - `lead_stage.py`
  - `lead_card.py`
  - (опционально) `lead_note.py`

**LeadPipeline** (см. ARCH_CRM_KANBAN.md):

- Поля:
  - `id`, `clinic_id`, `name`, `description`, `is_default`, timestamps.

**LeadStage**:

- Поля:
  - `id`, `pipeline_id`, `order`, `code`, `name`, `probability`, `color`.

**LeadCard**:

- Поля:
  - `id`, `clinic_id`, `pipeline_id`, `stage_id`,
  - `omnichannel_contact_id`, `patient_id`,
  - `primary_booking_id`, (при необходимости связь N:M с бронированиями/платежами через отдельную таблицу),
  - `title`, `source`, `estimated_value`, `actual_value`,
  - `status` (`open/success/lost`), `created_at`, `updated_at`, `closed_at`, `lost_reason`.

**LeadNote** (если делаем сразу):

- Поля:
  - `id`, `lead_id`, `author_admin_id`, `created_at`, `text`.

### 2.2. Миграции Alembic

- Создать новую версию Alembic:
  - таблицы `lead_pipelines`, `lead_stages`, `lead_cards`, `lead_notes`.
  - индексы:
    - по `clinic_id` на всех таблицах;
    - на `lead_cards` по `clinic_id + stage_id`, `clinic_id + status`, `clinic_id + created_at`.

---

## 3. Backend — сервисы и события

### 3.1. Репозитории и сервисы

- В `src/domain/interfaces/repositories/` добавить:
  - `lead_repository.py` (контракты для работы с воронкой/лидами).
- В `src/infrastructure/database/`:
  - реализовать `LeadRepositoryImpl`.
- В `src/application/services/`:
  - `lead_service.py`:
    - CRUD по `LeadPipeline`/`LeadStage` (на Phase 1 можно сделать только чтение/дефолтные значения);
    - операции с `LeadCard`:
      - `create_lead_from_contact`;
      - `update_stage`;
      - `attach_booking`;
      - `attach_payment`;
      - вычисление/обновление `estimated_value` и `actual_value`.

### 3.2. Обработка доменных событий

Использовать EventBus/хуки из `ARCH_CROSSCUT_EVENT_CONTEXT_AI.md`.

- Подписчики (примерно в `lead_event_handlers.py`):

1. `on_contact_created`:
   - если у контакта ещё нет лида:
     - создать `LeadCard` в default‑pipeline клиники с начальными полями (stage = `new`).

2. `on_booking_created`:
   - найти открытый `LeadCard` по `patient_id` или `omnichannel_contact_id`;
   - если найден:
     - обновить `stage` (например, `booked`);
     - проставить `primary_booking_id` (если пусто);
     - обновить `estimated_value` на основе стоимости услуг.

3. `on_payment_success`:
   - найти `LeadCard` по `booking_id`/`patient_id`;
   - обновить стадию (опционально `prepaid`) и `actual_value` (+сумма платежа).

4. `on_booking_completed`:
   - найти `LeadCard` по `booking_id`/`patient_id`;
   - перевести стадию в `success`, `status="success"`, `closed_at=now`;
   - при необходимости обновить `actual_value` по ERP.

### 3.3. Публичные методы сервиса

- `list_leads(filters, pagination)` — список лидов для API.
- `get_lead_details(lead_id)` — детали.
- `change_lead_stage(lead_id, new_stage_id)` — ручное перетаскивание карточки.
- `add_lead_note(lead_id, admin_id, text)`.

---

## 4. Backend — API для админки

### 4.1. Новый роутер

- Создать `src/api/v1/routers/admin_crm.py`.
- Эндпоинты:
  - `GET /api/v1/admin/crm/pipelines` — список pipeline/stage по клинике.
  - `GET /api/v1/admin/crm/leads` — список с фильтрами:
    - `stage_id`, `status`, `date_from/to`, `source`, `search`, `page`, `page_size`.
  - `GET /api/v1/admin/crm/leads/{id}` — детали (включая заметки и связанные booking/payment).
  - `PATCH /api/v1/admin/crm/leads/{id}/stage` — изменение стадии (Kanban‑перетаскивание).
  - `POST /api/v1/admin/crm/leads/{id}/notes` — добавление заметки.

- Доступ:
  - ограничить через RBAC:
    - `view_crm` для чтения;
    - `manage_crm` для изменения стадий/заметок.

---

## 5. Frontend — Kanban‑страница

### 5.1. Страница `AdminSalesPipelinePage`

- Добавить маршрут, например `/admin/sales` (см. ARCH_FRONTEND_BUSINESS_OS_UX).
- Структура:
  - использует общий layout админки.
  - левая панель:
    - фильтры (стадия, период, источник, ответственный);
    - краткие показатели (кол‑во лидов, сумма по этапам).
  - центральная область:
    - Kanban‑доска:
      - столбцы = `LeadStage` (в порядке `order`);
      - карточки = `LeadCard`:
        - имя/контакт, канал, стадия, оценка/факт, метки (например, «Новый», «С предоплатой»);
        - drag&drop между столбцами вызывает `PATCH /leads/{id}/stage`.
  - правая панель (drawer/side panel):
    - подробности выбранного лида:
      - контактные данные;
      - связанные записи/платежи;
      - задачи (если модуль Tasks включён);
      - заметки (список + форма добавления).

### 5.2. Хуки и типы

- В `frontend/src/api/types.ts` добавить типы DTO:
  - `LeadPipeline`, `LeadStage`, `LeadCard`, `LeadNote`, фильтры и ответы листинга.
- В `frontend/src/hooks/`:
  - `useCrmPipelines` — загрузка стадий.
  - `useLeads` — список лидов по фильтрам (React Query).
  - `useLeadDetails` — детали лида.
  - `useUpdateLeadStage`, `useCreateLeadNote` — мутации.

---

## 6. Интеграция с OmniChat и AI

### 6.1. Отображение стадии лида в OmniChat

- В `AdminOmniChatPage`:
  - для выбранного контакта:
    - показывать текущую стадию и сумму `estimated_value`/`actual_value` в правой панели (секция CRM).
  - добавить кнопку перехода:
    - «Открыть лид» → `AdminSalesPipelinePage` с выбранным `lead_id`.

### 6.2. AI‑подсказки

- На уровне AI‑агента (не Phase 1, но предусмотреть поля):
  - в будущем можно добавить инструменты `update_lead_stage`/`create_task_for_lead`, поэтому DTO и API должны быть к этому готовы (явные ID стадий/лидов, а не строки).

---

## 7. LTV пациента и отчёты владельца

- **TODO:**
  1. На уровне сервиса/отчётного слоя реализовать расчёт LTV пациента:
     - агрегировать `actual_value` всех успешных `LeadCard` пациента;
     - либо использовать ERP‑данные как источник правды по выручке и кэшировать результат в поле пациента.
  2. Добавить в CRM‑API/отчёты:
     - эндпоинт/метод для получения:
       - суммы по этапам воронки (как в `BUSINESS_LOGIC_V2` — «думают / записаны / успешно завершено»);
       - LTV по пациентам/сегментам.
  3. Убедиться, что DTO для OmniChat и дашбордов включает:
     - текущую стадию лида;
     - `estimated_value`/`actual_value`;
     - LTV пациента (если доступен).

---

## 8. Связь с маркетинговой атрибуцией

- **TODO:**
  1. В `LeadService` и DTO для `LeadCard` явно предусмотреть поля:
     - `visit_attribution_id: UUID | None`;
     - utm‑поля (или ссылку на `VisitAttribution`) в ответах API по лидам.
  2. При обработке доменных событий и создании `LeadCard`:
     - если для контакта/пациента уже существует `VisitAttribution`, связывать лид с атрибуцией;
  3. Обеспечить, чтобы CRM‑отчёты могли фильтроваться/группироваться по источнику/кампании, используя связку с модулем Marketing Attribution.

---

## 9. Тестирование

### 9.1. Unit‑ и интеграционные тесты backend

- Тесты для `LeadService`:
  - создание лида по `ContactCreated`;
  - обновление стадии по `BookingCreated`, `PaymentSuccess`, `BookingCompleted`;
  - корректный пересчёт `estimated_value`/`actual_value`.
- Тесты для API:
  - фильтрация и пагинация `GET /leads`;
  - смена стадии через `PATCH /leads/{id}/stage` с проверкой RBAC;
  - создание заметок.

### 9.2. Frontend‑тесты

- Снэпшоты/interaction‑тесты Kanban‑доски:
  - корректное отображение колонок и карточек;
  - drag&drop вызывает нужные запросы и обновляет UI.

---

## 10. Порядок выполнения для @DEV

1. Реализовать доменные сущности и миграции (LeadPipeline/LeadStage/LeadCard/LeadNote).
2. Реализовать репозитории и `LeadService`.
3. Подписать `LeadService` на доменные события через EventBus.
4. Добавить `admin_crm` роутер с API для листинга/деталей/смены стадий/заметок.
5. Добавить DTO/хуки/страницу `AdminSalesPipelinePage` во frontend.
6. Интегрировать CRM‑данные в OmniChat (отображение стадии и суммы, LTV пациента).
7. Реализовать расчёт LTV пациента и базовые отчёты владельца по воронке.
8. Обеспечить связь CRM с Marketing Attribution (visit_attribution/utm в лидах и отчётах).
9. Написать и прогнать тесты backend и frontend.

