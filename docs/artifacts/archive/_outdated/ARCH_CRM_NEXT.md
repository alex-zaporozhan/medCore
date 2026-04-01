## ARCH_CRM_NEXT — домен CRM (Sales & Kanban)

### 1. Краткое описание домена

CRM‑домен отвечает за **воронку продаж**:

- лиды, стадии, воронки (pipelines);
- оценка/факт стоимости сделок;
- связка Omnichannel → Booking → Payments → деньги и LTV.

Он превращает «поток контактов» в управляемые сделки с понятным статусом и прогнозом выручки.

### 2. Актуальная модель сущностей (по коду / BUSINESS_LOGIC_CURRENT/V2)

Сущности (по `BUSINESS_LOGIC_V2` и коду `admin_crm.py`, `LeadService`):

- `LeadPipeline` — воронка (набор стадий).
- `LeadStage` — стадия воронки, с вероятностью конверсии.
- `LeadCard` — конкретный лид/сделка:
  - `clinic_id`, `pipeline_id`, `stage_id`;
  - связь с `omnichannel_contact_id`, `patient_id`, `booking_id`, `payment_id`;
  - `title`, `estimated_value`, `actual_value`, `status`, `source`, `created_at`, `closed_at`.
- `LeadNote` — заметки по лидам (по коду).

API и сервисы:

- Backend:
  - `src/api/v1/routers/admin_crm.py` (pipelines, stages, leads, смена стадии, заметки);
  - `LeadService` в `src/application/services` (логика работы с лидами).
- Frontend:
  - `AdminSalesPipelinePage.tsx`:
    - Kanban‑доска со стадиями/лидами;
    - drag‑and‑drop для смены стадий;
    - агрегаты по сумме и количеству.

### 2.1. Событийная воронка (CRM_EVENTS_007, v1 в коде)

- `LeadLifecycleService` + DTO в `src/application/dto/lead_lifecycle_dto.py`; переходы стадий через `LeadService.update_stage_from_ai` (и ручной Kanban на том же пути).
- События шины: `ContactCreated`, `BookingCreated` / `Completed` / `Cancelled` / `NoShow` → lifecycle; при первой записи без открытого лида создаётся `LeadCard`; в payload `BookingCreated` добавляются `contact_id` (если известен по открытому лиду) и стабильный `dedup_id`. В `BookingCompleted` поле `visit_revenue` **не используется CRM для факта** (legacy/deprecated; фасад завершения визита коммитит БД до публикации события).
- Закрытие лида в `success` после визита — если audited‑переход в стадию «won» прошёл успешно; **`actual_value` пересчитывается из ERP** (`financial_transactions`, income), см. `ARCH_DEV_CRM_MONEY_008.md` §6 и `DEV_PROMPT_CRM_MONEY_008`.
- **Деньги в CRM (CRM_MONEY_008, v1):** `estimated_value` — прогноз (ручной PATCH или авто с прайса услуги по primary booking); `actual_value` — только зеркало ERP income, не локальные суммы по платежам/событиям.
- Системные задачи по отмене/no‑show: `lead_id`, идемпотентность по `dedup_id` / `source_event_id`, `trace_id` в описании. См. `ARCH_DEV_CRM_EVENTS_007_TASKS.md`.

### 3. Целевая модель vNext (что нужно добавить/упростить)

1. **Полное автодвижение лидов по событиям:**
   - Автоматическое создание `LeadCard` при новом `OmnichannelContact` (если контакта ещё нет в CRM).
   - Автопереход в стадию «Записан» при создании `Booking`, связанного с пациентом/контактом.
   - Автопереход в «Успешно завершено» при `Booking.status=completed` + обновление `actual_value`.
   - Автопереход в «Потеряно» при отменах/длительном отсутствии движения.

2. **Единый источник истины по деньгам:**
   - `estimated_value` и `actual_value` берутся из ERP/Booking/Payments, а не считаются вручную;
   - CRM не должна хранить собственные дублирующие суммы, кроме кэширующих агрегатов.

3. **Интеграция с Omnichannel и AI:**
   - в Omnichannel‑чате оператор и AI видят:
     - текущий stage/ожидаемую сумму по лиду;
     - быстрые действия (перевести в другую стадию, создать запись, зафиксировать оплату).

4. **UX‑улучшения:**
   - фильтры/поиск по источнику, сумме, стадии, привязанным пациентам/записям;
   - визуальные сигналы «rot» (лиды, давно без движения) inline на Kanban;
   - быстрая навигация из канбана в Omnichannel/Booking/финансовые операции.

### 4. Связи с другими доменами

- **Omnichannel:** главный источник новых лидов и статуса коммуникаций.
- **Booking:** события создания/завершения/отмены визитов двигают стадии и обновляют суммы.
- **ERP:** факт выручки и маржинальности подтягивается для реальной оценки результатов лидов.
- **Loyalty:** крупные пакеты/абонементы могут отражаться как отдельные сделки или как атрибут LTV.
- **Tasks & AttentionFeed:** лидам без движения, с важной суммой или с провалами в конверсии могут соответствовать задачи/attention‑элементы.

