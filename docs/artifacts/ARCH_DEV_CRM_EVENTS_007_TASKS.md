## ARCH_DEV_CRM_EVENTS_007_TASKS — сверх‑детализированные dev‑таски

> Связанная архитектура: `ARCH_DEV_CRM_EVENTS_007.md`  
> Связанный DEV_PROMPT: `DEV_PROMPT_CRM_EVENTS_007` (P1, CRM‑1)

---

### 1. Understand — текущее движение лидов и ручные операции

1.1. **Разобрать текущий `LeadService` и CRM‑роутеры.**  
1.1.1. В сервисах CRM (например, `LeadService`) и роутере `admin_crm.py` найти:  
       - как и где создаются `LeadCard`;  
       - как меняется `LeadStage` (ручные операции, drag&drop, API‑вызовы).  
1.1.2. Зафиксировать, какие стадии используются сейчас и какие переходы уже существуют.

1.2. **Выявить связи лидов с Booking/ERP/Omnichannel.**  
1.2.1. Проверить, какие поля в `LeadCard` и связанных сущностях указывают на:  
       - `omnichannel_contact_id`/`conversation_id`;  
       - `patient_id`;  
       - `booking_id`(ы);  
       - атрибуцию (utm/source/campaign).  
1.2.2. Связать это с событийной картиной из `ARCH_BOOKING_NEXT.md`, `ARCH_ERP_NEXT.md`, `ARCH_ATTRIBUTION_NEXT.md`.

1.3. **Сопоставить с GAPS и целевым поведением.**  
1.3.1. Открыть `BACKEND_GAPS_CRM_NEXT.md` (CRM‑1, ATT‑1, TASK‑1), `ARCH_CRM_NEXT.md` и `ARCH_DEV_CRM_EVENTS_007.md`.  
1.3.2. Зафиксировать, какие конкретные GAPS относятся к отсутствию/частичной реализации автодвижения по событиям.

---

### 2. Design‑to‑code — событийный слой и LeadLifecycleService

2.1. **Определить доменные события CRM‑воронки.**  
2.1.1. На основе раздела 3.1 `ARCH_DEV_CRM_EVENTS_007.md` сформировать набор event‑DTO:  
       - `LeadEventContactCreated`, `LeadEventBookingCreated`, `LeadEventVisitCompleted`, `LeadEventBookingCancelled`, `LeadEventNoShow`, `LeadEventStale`.  
2.1.2. Для каждого события определить payload: `lead_id?`, `clinic_id`, `contact_id`, `patient_id`, `booking_id`, метаданные (source, campaign и т.п.).

2.2. **Спроектировать `LeadLifecycleService`.**  
2.2.1. Описать интерфейсы методов:  
       - `handle_contact_created`, `handle_booking_created`, `handle_visit_completed`, `handle_booking_cancelled`, `handle_no_show`, `handle_stale_lead`.  
2.2.2. Определить маппинг `event_type + current_stage → new_stage` (с опорой на `ARCH_CRM_NEXT.md` и описание стадий).  
2.2.3. Зафиксировать в ARCH‑файле/коде, где хранится этот маппинг (конфиг/таблица/словарь).

---

### 3. Implement — backend: события и переходы стадий

3.1. **Реализовать `LeadLifecycleService` и событийные DTO.**  
3.1.1. В application‑слое создать сервис (например, `lead_lifecycle_service.py`) и DTO‑классы событий.  
3.1.2. Обеспечить, что сервис умеет:  
       - находить/создавать `LeadCard` по контексту события;  
       - определять целевую стадию;  
       - выполнять переход стадии через централизованный механизм (state‑machine для `LeadStage`).

3.2. **Интегрировать события из Booking/ERP/Omnichannel.**  
3.2.1. В местах:  
       - создания `Booking`;  
       - завершения визита (`Booking.status=completed` через фасад);  
       - отмены/`no_show`;  
       - создания нового Omnichannel‑контакта/диалога;  
       - добавить генерацию соответствующих событий и вызов `LeadLifecycleService`.  
3.2.2. При необходимости использовать синхронные вызовы или очередь/таски (по решению @ARCH), но архитектурно заложить событийный слой.

3.3. **Обновить `LeadService` для единообразия переходов.**  
3.3.1. Вынести логику смены стадий из разбросанных участков кода в единый механизм, который использует `LeadLifecycleService`/state‑machine.  
3.3.2. Обеспечить, чтобы ручной drag&drop в Kanban и автодвижение по событиям использовали один и тот же код перехода стадий.

---

### 4. Implement — наблюдаемость и Tasks/Attention для CRM‑цепочек

4.1. **Добавить логирование переходов стадий.**  
4.1.1. В `LeadLifecycleService` логировать каждое изменение стадии: `trace_id`, `lead_id`, `clinic_id`, `event_type`, `from_stage`, `to_stage`, инициатор (событие/пользователь/AI).  
4.1.2. Убедиться, что логи соответствуют общему OBS‑формату (`ARCH_DEV_OBS_CHAINS_023_TASKS.md`).

4.2. **Добавить базовые метрики по CRM‑воронке.**  
4.2.1. Ввести метрики:  
       - количество лидов, создаваемых по источникам/кампаниям;  
       - частота переходов в `Win`/`Lost` по событиям;  
       - доля «застоявшихся» лидов;  
       - среднее время от `New` до `Win`/`Lost`.  
4.2.2. Связать метрики с атрибуцией (для ROI) и OBS‑цепочками.

4.3. **Интегрировать проблемные случаи с Tasks/Attention.**  
4.3.1. Определить критерии, когда CRM‑события должны порождать Tasks/Attention (rot, частые отмены/no‑show по лиду, крупные суммы без движения и т.п.).  
4.3.2. Реализовать генерацию Attention/Tasks через слой Tasks&Attention (`ARCH_DEV_TASKS_MODEL_020_TASKS.md`), указывая `lead_id`, контекст и `trace_id`.

---

### 5. Stabilize — тесты и обновление артефактов

5.1. **Покрыть автодвижение тестами.**  
5.1.1. Написать/обновить тесты для `LeadLifecycleService`:  
       - создание лида по контактам Omnichannel;  
       - перевод при создании записи;  
       - перевод в `Win` при успешном завершении визита (с ERP‑данными);  
       - перевод в соответствующие потерянные/нестандартные стадии при отменах и no‑show;  
       - выявление и обработка «застоявшихся» лидов.  
5.1.2. Проверить, что ручные изменения стадий (drag&drop) корректно логируются и не ломают автоматические правила.

5.2. **Синхронизировать GAPS и документацию.**  
5.2.1. Обновить `DEV_PROMPTS_NEXT.md`, указав статус `DEV_PROMPT_CRM_EVENTS_007`.  
5.2.2. В `BACKEND_GAPS_CRM_NEXT.md` и `BACKEND_GAPS_Attribution_NEXT.md` отметить закрытые/уточнённые пункты CRM‑1/ATT‑1/TASK‑1.  
5.2.3. При необходимости скорректировать `ARCH_CRM_NEXT.md` и `ARCH_AUDIT_NEXT.md`, отражая новую событийную модель воронки.

---

## Выполнено в коде (факт по результату реализации)

### События и payload/trace_id

- **Типизированные event‑DTO воронки** (вместо одного общего контейнера):  
  `LeadEventContactCreated`, `LeadEventBookingCreated`, `LeadEventVisitCompleted`, `LeadEventBookingCancelled`, `LeadEventNoShow`, `LeadEventStale` — `src/application/dto/lead_lifecycle_dto.py`.
- **Добавлены события**: `BookingCancelled`, `BookingNoShow` и поддержка `trace_id` для booking/contact событий.  
  Файл: `src/application/events/standard_events.py`
- **Публикация событий в доменных потоках**:
  - `BookingCreated` (patient/admin) с `trace_id` — `src/application/services/booking_service.py`
  - `BookingCancelled` с `trace_id` — `src/application/services/booking_service.py`
  - `BookingNoShow` с `trace_id` — `src/application/services/booking_service.py` (+ проброс `context` в роутере `src/api/v1/routers/bookings.py`)
  - `BookingCompleted` (через фасад completion) с `trace_id=actor.trace_id` — `src/application/services/booking_completion_service.py`
  - `ContactCreated` при создании нового omnichannel контакта — `src/application/services/integration_gateway_service.py`

### LeadLifecycleService и переходы стадий

- **Расширен `LeadLifecycleService`**:
  - `handle_contact_created`
  - `handle_booking_created`
  - `handle_visit_completed` (завершение визита / `Booking.status=completed`)
  - `handle_booking_cancelled`
  - `handle_no_show`
  - `handle_stale_lead`  
  Файл: `src/application/services/lead_lifecycle_service.py`
- **Переходы стадий** выполняются централизованно через `LeadService.update_stage_from_ai(... initiated_by_ai=False ...)` (валидируется state-machine семантик стадий) и публикуют `LeadStageChanged`.  
  Файл: `src/application/services/lead_service.py`
- **Для cancel/no_show** лид теперь закрывается в `status="lost"` (добавлен `LeadService.close_lead_as_lost`).  
  Файлы: `src/application/services/lead_service.py`, `src/application/services/lead_lifecycle_service.py`

### Единообразие ручных и авто переходов (drag&drop == event-driven path)

- **Ручной drag&drop** (`/admin/crm/leads/{lead_id}/stage`) переведён на тот же audited‑путь, что и автопереходы:
  - `LeadService.change_lead_stage(... request_context=...)` вызывает `update_stage_from_ai(... initiated_by_ai=False ...)`.
  - В роутере пробрасывается `request_context` (actor/trace/permissions).  
  Файлы: `src/application/services/lead_service.py`, `src/api/v1/routers/admin_crm.py`

### Наблюдаемость и метрики CRM‑воронки

- **Логи** переходов в `LeadLifecycleService` (attempt/applied/failed) в формате цепочки OBS:  
  `trace_id`, `event_type`, `from_stage_id`, `from_semantic`, `to_stage_id`, `to_semantic`, `lead_id`, `clinic_id`, `reason`, `initiator`, поле `chain=crm_lifecycle`.  
  Файл: `src/application/services/lead_lifecycle_service.py`
- **Добавлены метрики** (Prometheus, low-cardinality):
  - `crm_leads_created_total{clinic_id,source,utm_campaign}`
  - `crm_lead_stage_transitions_total{clinic_id,from_semantic,to_semantic,initiator}`
  - `crm_lead_time_to_close_seconds{clinic_id,outcome}`
  - `crm_lead_lifecycle_transitions_total{clinic_id,event_type,outcome}` — исход event-driven перехода из lifecycle
  - `crm_lead_stale_handled_total{clinic_id,outcome}` — обработка stale (stage_applied / noop / …)
  - `crm_lead_visit_completion_outcomes_total{clinic_id,outcome}` — закрытие лида после визита vs пропуск (нет won / сбой transition)
  - `crm_lead_booking_onboarded_total{clinic_id,outcome}` — `BookingCreated`: существующий лид vs создан новый  
  Файлы: `src/core/metrics.py`, `src/application/services/lead_service.py`

### Tasks/Attention интеграция по событиям

- **Включено реальное создание задач** по событиям `BookingCancelled` / `BookingNoShow` (system tasks, best-effort, через отдельную AsyncSession): `lead_id`, дедуп по `dedup_id` в payload / `Task.source_event_id`, `trace_id` и `event_id` в описании, `due_at` в UTC.  
  Файл: `src/application/events/tasks_event_handlers.py`  
  Регистрация обработчиков: `src/main.py`

### Инварианты после QA_ARCH (доп. итерация)

- Закрытие лида `success` после визита — **только** если успешен audited‑переход в won (`close_lead_as_success(..., update_stage=False)`).
- При `BookingCreated`, если нет открытого лида по пациенту/контакту — **создаётся** лид (`LeadService.create_lead_for_patient_booking`).
- События записи: **`dedup_id`** (uuid5) во всех `make_booking_*`; опционально **`contact_id`** в `BookingCreated`; **`visit_revenue`** в `BookingCompleted` из `BookingCompletionService`.
- **`DomainEvent.event_id`** — уникальный id публикации для трассировки.

### Тесты

- Добавлены/расширены тесты `LeadLifecycleService` и manual path:
  - contact_created → создание лида
  - booking_created → attach booking + stage move; сценарий **создания нового лида** при первой записи (`test_lead_lifecycle_booking_created_creates_lead_when_none`)
  - booking_completed → win + success close + **`actual_value` из visit_revenue**
  - booking_cancelled/no_show → lost + close
  - stale → stage move
  - manual drag&drop → audited path  
  Файлы: `tests/services/test_lead_lifecycle_service.py`, `tests/unit/test_booking_event_dedup.py` (стабильность `dedup_id`).

### Зафиксировано при аудите @QA_ARCH (итерация после v1)

- Согласованы инварианты: success‑close только после успешного audited‑перехода; автосоздание лида на `BookingCreated`; `dedup_id` / `lead_id` / UTC в задачах по отмене и no‑show; прокидывание выручки визита в CRM через `BookingCompleted`.
- В архитектурных артефактах отражено: `ARCH_CRM_NEXT.md` §2.1, `ARCH_AUDIT_NEXT.md`, `ARCH_DEV_CRM_EVENTS_007.md` §1.4, GAPS (CRM, Attribution, Tasks), `DEV_EXECUTION_TRACKER_NEXT.md` (статус пакета), при необходимости — `ARCH_DEV_OBS_CHAINS_023.md` (перекрёстная ссылка на логи CRM lifecycle).

---

## На потом

### Эволюция продукта и @DEV (идеи без жёсткого приоритета)

- **Валидация payload шины → DTO**: Pydantic‑схемы на границе `DomainEvent` (жёсткие типы вместо `payload.get`).
- **Stale как отдельный доменный поток**: периодический job (Celery beat/cron), публикующий `LeadEventStale`, вместо best‑effort внутри AI Task Manager.
- **Полное покрытие funnel‑метрик**: gauge/снимок доли stale в популяции; win/lost с явной разбивкой по доменным событиям в отчётах; связка с ROI (частично перекрыто `crm_lead_visit_completion_outcomes_total`, `crm_lead_booking_onboarded_total`).
- **Тесты Tasks/Attention на Windows**: стабилизировать async teardown (pytest-asyncio / asyncpg), чтобы `tests/services/test_tasks_attention_status.py` был зелёным.
- **Расширение `Booking` ↔ Omnichannel**: при появлении `omnichannel_contact_id` на сущности записи — всегда прокидывать его в `BookingCreated` без эвристики через открытый лид.

### На потом — @QA_ARCH (ревью качества и следующие проверки)

1. **Контракт шины ↔ CRM**: зафиксировать в отдельном мини‑доке или в `ARCH_TESTS` таблицу обязательных/опциональных полей payload для `BookingCreated` / `Completed` / `Cancelled` / `NoShow` / `ContactCreated` и прогонять контрактный тест (или Pydantic‑модель) в CI — сейчас опираемся на соглашение в коде и ручной аудит.
2. **Путь lost после cancel/no‑show**: явно задокументировать и по желанию унифицировать с success‑путём (строго «transition ok → close» или намеренное «close перезаписывает стадию») и добавить тест на согласованность логов `crm_lead_lifecycle_*` с фактическим `LeadCard.status`.
3. **Интеграционный зелёный барьер для CRM lifecycle**: вынести минимальный набор сценариев из `test_lead_lifecycle_service.py` в job CI с гарантированной Postgres‑фикстурой (или маркер `integration`), чтобы не зависеть от skip в локальной среде — см. `docs/TESTING_CANON.md` §2.1.
4. **OBS‑словарь**: сверить ключи `chain` / `step` в `LeadLifecycleService` с эталонными именами в `ARCH_DEV_OBS_CHAINS_023.md` §4 и внести в OBS‑TASKS единую таблицу «шаг → обязательные поля лога» для цепочки CRM.
5. **E2E smoke воронки**: один сценарий «контакт → лид → запись → complete (фасад) → Kanban видит стадию/закрытие» в Playwright или API‑цепочке — для регрессии после изменений в шине или семантиках стадий.
6. **Дедуп задач — граничные случаи**: тест на повторную публикацию того же логического события (тот же `dedup_id`) после перевода задачи в `done` (ожидаемое поведение: новая задача или нет — зафиксировать в ARCH и покрыть тестом).
7. **Связка TASK‑1 полная**: после появления явной модели Task ↔ AttentionItem — проставить обратные ссылки из Attention на системные задачи по CRM и проверить дашборд админа на дубли/шум.