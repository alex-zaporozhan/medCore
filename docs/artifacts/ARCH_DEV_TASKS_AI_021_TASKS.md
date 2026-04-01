## ARCH_DEV_TASKS_AI_021_TASKS — сверх‑детализированные dev‑таски

> Связанная архитектура: `ARCH_DEV_TASKS_AI_021.md`  
> Связанный DEV_PROMPT: `DEV_PROMPT_TASKS_AI_021` (P2, TASK‑2, OMNI‑3)

---

### ✅ Статус реализации (по коду, фактическое выполнение TASKS_AI_021)

#### 1) Understand / Inventory
- ✅ **Модель Tasks & Attention уже поддерживает связи**: `Task.attention_kind/attention_ref_id` и источники `Task.source` (`manual|ai_suggested|ai_auto|system`).
- ✅ **Сервисы/роутеры/селери точки найдены и использованы**: `TaskService`, `AttentionFeedService`, `admin_tasks`, `ai_tasks`.

#### 2) AiTaskSettings / ProposedTask / CreatedTaskResult
- ✅ **AiTaskSettings** (per-clinic): `src/domain/entities/ai_task_settings.py`
- ✅ **Миграция**: `alembic/versions/c9d0e1f2a3b4_ai_task_settings.py`
- ✅ **Сервис настроек**: `src/application/services/ai_task_settings_service.py`
- ✅ **Admin API для редактирования**: `src/api/v1/routers/admin_ai_tasks_settings.py` + подключение в `src/api/v1/router.py`
- ✅ **DTO пайплайна**: `src/application/dto/ai_task_manager_dto.py` (`ProposedTask`, `CreatedTaskResult`, `AnalysisContext`)

#### 3) AiTaskContextCollector / AiTaskAnalyzer (rules + optional LLM tool)
- ✅ **Collector без ПД/PII**: `AiTaskContextCollector` НЕ вызывает `AttentionFeedService.get_feed()` (избегаем загрузки `patient_phone/full_name` в память), делает минимальные SQL запросы.
- ✅ **Rule-based MVP сценарии**:
  - `booking.no_show_pattern`
  - `booking.erp_errors_cluster`
  - `crm.stale_leads`
- ✅ **LLM через tools-registry (опционально, с graceful fallback)**:
  - Tool: `src/application/ai/tools_tasks.py` (`AnalyzeAttentionForTasksTool`, `analyze_attention_for_tasks`)
  - Registry: `src/application/ai/tools_registry.py` (зарегистрирован `analyze_attention_for_tasks`)
  - Analyzer: `src/application/services/ai_task_manager_service.py` включает LLM-ветку при `AiTaskSettings.analyzer_thresholds["llm_enabled"]=true`, при ошибках — fallback на rules.
- ✅ **SafeAiClient + tokenization**:
  - Safe client через `build_safe_ai_client`
  - Tokenization для сущностей: `PATIENT#...`, `LEAD#...`, `BOOKING#...`
- ✅ **Доп. защита: дата рождения не отправляется в AI**:
  - добавлен токен `BIRTHDATE#...` (`src/application/ai/tokenization.py`)
  - рекурсивная токенизация ключей `birth_date|birthdate|dob|date_of_birth` перед отправкой (`src/application/ai/tools_tasks.py`)
  - unit‑тест: `tests/services/test_ai_tool_analyze_attention_for_tasks.py`

#### 4) AiTaskGenerator / запись задач
- ✅ **Запись строго через TaskService**: `AiTaskGenerator` создаёт задачи через `TaskService.create_task` (инварианты сохраняются).
- ✅ **Лимиты**: clinic/patient/doctor (best-effort).
- ✅ **Human-in-the-loop**:
  - `requires_confirmation=True` → `source=ai_suggested`
  - в confirm режиме `urgent/high` понижается до `medium`.
- ✅ **Идемпотентность/антишум**:
  - используется deterministic `Task.source_event_id` (uuid5) + проверка существующих open/in_progress AI‑задач, чтобы не плодить дубли.

#### 5) Celery / UI
- ✅ **Celery orchestration**:
  - `ai_tasks.run_ai_task_manager_for_clinic`
  - `ai_tasks.run_ai_task_manager_all_clinics`
  - расписание: `src/infrastructure/messaging/celery_app.py`
- ✅ **Celery DB engine reuse**: в `src/infrastructure/messaging/tasks/ai_tasks.py` engine/sessionmaker переиспользуются (не создаются заново каждый вызов).
- ✅ **UI Tasks**: `frontend/src/admin/pages/AdminTasksPage.tsx` — есть отдельный блок AI‑задач (`source=ai`) и бейдж/иконка для `ai_suggested|ai_auto`.

#### 6) Observe / Tests
- ✅ **Метрики**: `ai_task_manager_*` добавлены в `src/core/metrics.py`
- ✅ **Структурные логи без ПД**: runner логирует `clinic_id`, `trace_id`, `proposed`, `created_count` + ошибки.
- ✅ **Тесты**:
  - tool tests: `tests/services/test_ai_tool_analyze_attention_for_tasks.py`
  - базовые тесты пайплайна: `tests/services/test_ai_task_manager_service.py`
  - обновлены тесты Tasks&Attention: `tests/services/test_tasks_attention_status.py`

---

### На потом (предложения по улучшению)
- **SEC/RBAC**: завести permission `ai.tasks.run` и исполнять runner в явном техническом контексте с минимальными правами; добавить audit trail запусков.
- **Полноценная идемпотентность**: отдельная таблица `ai_task_dedup`/`ai_task_run_log` (clinic_id, task_class, natural_key, day, status), а не только `source_event_id`.
- **Collector coverage**: расширить privacy-safe сбор сигналов на retention/conflict/loyalty/ERP и другие high-signal источники без PII.
- **LLM hardening**: строгий allowlist `task_class`, лимитирование длины text полей, rate-limit per clinic, негативные тесты (invalid JSON / provider down) с гарантированным fallback.
- **UI для AiTaskSettings**: страница/секция админки для редактирования `ai-task-settings` (лимиты, allowed classes, `llm_enabled`, creation_mode).
- **Tokenization v2**: перейти от uuid-in-token к mapping table (псевдо‑ID), расширить токены для чувствительных полей централизованно.
- **Тестовая инфраструктура**: стабилизировать pytest schema setup (alembic upgrade head в test runner без `asyncio.run()`), и отдельно решить teardown issue на Windows/Python 3.14/asyncpg.

### 1. Understand — текущее состояние Tasks/Attention и AI‑интеграций

1.1. **Инвентаризация моделей и сервисов Tasks/Attention.**  
1.1.1. В доменном/ORM‑слое найти сущности:  
       - `Task`, `AttentionItem`, любые вспомогательные таблицы связок (например, `TaskAttentionLink` или поля `task.attention_id`);  
       - статусы задач, приоритеты, типы Attention.  
1.1.2. В application‑слое изучить сервисы:  
       - `TaskService`, `AttentionFeedService` (точные имена см. в `ARCH_DEV_TASKS_MODEL_020.md`);  
       - методы создания, обновления, закрытия задач, привязки к Attention и доменным объектам (Booking/ERP/CRM/Loyalty/Omni).

1.2. **Инвентаризация существующих AI‑интеграций с Tasks.**  
1.2.1. В сервисах AI/Omnichannel/Celery‑тасках найти:  
       - все места, где создаются/обновляются `Task`/`AttentionItem` от имени AI или на основе AI‑аналитики;  
       - любые Celery‑таски/cron‑процессы, которые анализируют доменные события и создают задачи.  
1.2.2. Для каждого такого места зафиксировать:  
       - проходят ли операции через TaskService/AttentionFeedService;  
       - отмечены ли задачи как AI‑инициированные (`created_by="ai"` или аналоги);  
       - как сейчас контролируется шум (фильтры, лимиты, ручное подтверждение).

1.3. **Инвентаризация источников сигналов для будущего AI Task Manager’а.**  
1.3.1. По `ARCH_DEV_TASKS_MODEL_020.md`, `ARCH_DEV_OBS_CHAINS_023.md` и доменным ARCH (Booking/ERP/CRM/Loyalty/Omni) собрать:  
       - какие типы Attention/событий являются приоритетными для AI‑анализа (no‑show, ERP‑сбои, CRM‑риски, лояльность и т.п.);  
       - какие метрики/логи уже доступны для анализа задач.  
1.3.2. Зафиксировать, какие источники будут использоваться в первом MVP AI Task Manager’а, чтобы не усложнять реализацию.

1.4. **Сопоставление с GAPS и соседними ARCH_DEV.**  
1.4.1. Открыть:  
       - `BACKEND_GAPS_Tasks_NEXT.md` (TASK‑2);  
       - `BACKEND_GAPS_Omnichannel_NEXT.md` (OMNI‑3);  
       - `NONFUNCTIONAL_AUDIT_NEXT.md` (OBS‑2).  
1.4.2. Отметить, какие пункты относятся именно к AI Task Manager’у (анализ+генерация задач), а какие — к базовой модели Tasks/Attention (`ARCH_DEV_TASKS_MODEL_020`) или Omnichannel/AI‑registry.

---

### 2. Design‑to‑code — компоненты AiTaskAnalyzer / AiTaskGenerator / AiTaskSettings

2.1. **Спроектировать классы/интерфейсы AI Task Manager’а.**  
2.1.1. На уровне application‑слоя описать интерфейсы:  
       - `AiTaskAnalyzer`:  
         - метод `analyze(attention_items, existing_tasks, metrics_context) -> list[ProposedTask]`;  
       - `AiTaskGenerator`:  
         - метод `generate(proposed_tasks, settings) -> list[CreatedTaskResult]`;  
       - `AiTaskSettings`:  
         - модель/конфиг per‑clinic с флагами и лимитами.  
2.1.2. Зафиксировать эти интерфейсы в коде (абстрактные классы/протоколы), даже если часть реализации v1 будет упрощена.

2.2. **Спроектировать модель/хранилище `AiTaskSettings`.**  
2.2.1. В доменном/ORM‑слое описать сущность/таблицу `AiTaskSettings` (или близкий объект конфигурации):  
       - `clinic_id`;  
       - флаг `ai_tasks_enabled`;  
       - список (или битовая маска) разрешённых классов задач (Booking/ERP/CRM/Loyalty/Omni);  
       - лимиты: максимум задач в день на клинику/пациента/доктора;  
       - режим подтверждения: «требуется ручное подтверждение» vs «автосоздание задач».  
2.2.2. Определить, как настройки будут редактироваться (отдельный админ‑UI/endpoint или статичный конфиг v1), и зафиксировать это в комментариях.

2.3. **Определить MVP‑набор классов AI‑задач.**  
2.3.1. Совместно с `ARCH_DEV_*` других доменов (по документации) выбрать 1–3 реально полезных сценария для MVP, например:  
       - «частые no‑show по пациенту/врачу» (Booking);  
       - «подозрительные ERP‑сбои по визитам/клиникам» (ERP);  
       - «лиды с крупной суммой без движения» (CRM).  
2.3.2. Для каждого класса описать:  
       - критерии срабатывания (на основе Attention/метрик);  
       - целевую задачу (title/description/priority);  
       - кто исполнитель (роль/пользователь/группа).

2.4. **Спроектировать формат `ProposedTask` и связи с Attention.**  
2.4.1. В DTO/доменном слое описать `ProposedTask`:  
       - ссылка на `clinic_id`, `source_attention_id` (если есть), доменный объект (booking_id/lead_id/patient_id);  
       - предлагаемый `title`, `description`, `priority`, тип задачи;  
       - флаги: `requires_confirmation`, `initiated_by_ai`.  
2.4.2. Обеспечить, чтобы `ProposedTask` легко конвертировался в реальную `Task` через TaskService, не нарушая инвариантов `ARCH_DEV_TASKS_MODEL_020`.

---

### 3. Implement — сбор сигналов и анализ (AiTaskAnalyzer)

3.1. **Реализовать сбор входных данных для анализа.**  
3.1.1. В отдельном сервисе/модуле (например, `AiTaskContextCollector`) реализовать функции:  
       - загрузка свежих/открытых `AttentionItem` с приоритетами high/medium по клинике;  
       - загрузка связанных задач по этим Attention/доменным объектам (чтобы не дублировать уже существующие задачи);  
       - при необходимости — загрузка метрик из OBS (через адаптер, если есть API).  
3.1.2. Сформировать агрегированный `AnalysisContext` с разбивкой по доменам и объектам.

3.2. **Реализовать базовый `AiTaskAnalyzer` для MVP‑классов задач.**  
3.2.1. В `AiTaskAnalyzer` реализовать логику:  
       - группировка Attention/событий по пациенту/врачу/клинике/типу;  
       - применение простых правил/порогов для выбора объектов, требующих задач (например, N no‑show за период, M ERP‑ошибок за сутки и т.п.);  
       - формирование `ProposedTask` по каждому отобранному кейсу.  
3.2.2. При необходимости интегрировать LLM‑анализ как отдельный tool через tools‑registry (e.g. `analyze_attention_for_tasks`), но оставить правила fallback‑логики на случай недоступности AI.

3.3. **Задействовать tokenization и SafeAiClient при использовании LLM.**  
3.3.1. Если `AiTaskAnalyzer` вызывает LLM (через tools‑registry), убедиться, что:  
       - все данные проходят через `SafeAiClient`/`AiSanitizer` и tokenization‑слой согласно `ARCH_DEV_OMNI_POLICY_016` и `ARCH_DEV_AI_TOKENIZATION_025`;  
       - в промпт не попадают ПД, только токены и агрегированные значения.  
3.3.2. Добавить логирование базовых LLM‑вызовов (trace_id, тип анализа, без ПД).

3.4. **Инкапсулировать связь с доменными ARCH_DEV.**  
3.4.1. В реализации `AiTaskAnalyzer` явно указать, какие типы Attention/цепочек он поддерживает в v1 (ссылки/комментарии на соответствующие `ARCH_DEV_*` доменов), чтобы в будущем легко добавлять новые сценарии.

---

### 4. Implement — генерация и запись задач (AiTaskGenerator)

4.1. **Реализовать `AiTaskGenerator` с учётом настроек и лимитов.**  
4.1.1. В `AiTaskGenerator` реализовать:  
       - фильтрацию `ProposedTask` по `AiTaskSettings` текущей клиники:  
         - отключённые классы задач → сразу отметать;  
         - превышение лимитов задач в день/на объект → агрегировать или игнорировать;  
       - преобразование `ProposedTask` в реальные задачи через TaskService.  
4.1.2. Внедрить поддержку режима подтверждения:  
       - если `requires_confirmation=True` или настройки требуют human‑in‑the‑loop:  
         - создавать задачи в статусе draft/low priority или создавать Attention/«AI‑предложение», которое оператор должен подтвердить;  
       - иначе — создавать обычные задачи с `created_by="ai"`.

4.2. **Интеграция с TaskService/AttentionFeedService.**  
4.2.1. Для каждой создаваемой задачи:  
       - использовать TaskService для записи, не обходя доменные инварианты;  
       - заполнять поля: `created_by="ai"`, `source_attention_id`, доменный объект (booking_id/lead_id и т.п.), `ai_reason`/`ai_payload` при необходимости.  
4.2.2. При ошибках записи задач (конфликт статусов, проблемы с доменной сущностью) логировать событие и, при необходимости, создавать Attention о сбое AI Task Manager’а.

4.3. **Учесть SEC/RBAC‑ограничения.**  
4.3.1. Обеспечить, чтобы все операции генерации задач выполнялись от имени технического контекста/роли с пермишенами `ai.tasks.run` и минимумом дополнительных прав (по `ARCH_DEV_SEC_RBAC_022`):  
       - доступ только к чтению необходимых доменных слоёв;  
       - запись только через TaskService/AttentionFeedService.  
4.3.2. Не допускать, чтобы AI Task Manager напрямую менял ERP/Booking/CRM/Loyalty — он только создаёт задачи и Attention.

---

### 5. Integrate — планировщик, Omnichannel и UI

5.1. **Интегрировать AI Task Manager с планировщиком/Celery.**  
5.1.1. Создать Celery‑таску/планировщик (например, `run_ai_task_manager_for_clinic`):  
       - вход: `clinic_id`, опционально период/фильтры;  
       - шаги:  
         - загрузка `AiTaskSettings` для клиники;  
         - сбор контекста через `AiTaskContextCollector`;  
         - вызов `AiTaskAnalyzer` → список `ProposedTask`;  
         - вызов `AiTaskGenerator` → создание задач.  
5.1.2. Настроить период запуска (например, каждые N минут/часов) с учётом нагрузки и бизнес‑требований.

5.2. **Интеграция с Omnichannel/Tasks‑UI.**  
5.2.1. В админском UI задач (Tasks‑страницы) добавить возможность:  
       - фильтровать и просматривать задачи `created_by="ai"`;  
       - видеть связи с Attention и доменными сущностями;  
       - (опционально) отмечать задачи как «бесполезные/спам» для обратной связи на настройки/анализ.  
5.2.2. В Omnichannel/CRM‑UI (по возможности):  
       - отобразить для операторов, что некоторые задачи предложены AI (бейдж/иконка);  
       - при сценариях human‑in‑the‑loop — предоставить интерфейс подтверждения/отклонения предложенных задач.

5.3. **Интеграция с tools‑registry/AI‑инфраструктурой.**  
5.3.1. Если `AiTaskAnalyzer` использует LLM через tools‑registry:  
       - зарегистрировать соответствующий tool (e.g. `analyze_attention_for_tasks`) в `ai/tools_registry.py` с формальными входами/выходами;  
       - убедиться, что Omnichannel/AI‑инфраструктура может переиспользовать этот tool при необходимости (например, для визуализации предложений).  
5.3.2. Обеспечить, чтобы конфигурация AI‑режимов (`ai_tasks_enabled`, provider_type, allow_personal_data) подтягивалась из общего `AiConfigService`/`ClinicAiSettings`.

---

### 6. Observe — логи, метрики, контроль шума и стабилизация

6.1. **Логирование работы AI Task Manager’а.**  
6.1.1. Везде, где работает `AiTaskAnalyzer`/`AiTaskGenerator` и планировщик:  
       - логировать: `clinic_id`, количество проанализированных Attention/объектов, количество предложенных и реально созданных задач;  
       - фиксировать причины отказа от создания задач (лимиты, отключённые классы, конфликты).  
6.1.2. Логи должны быть достаточно структурированными, чтобы их можно было использовать в OBS/мониторинге без ПД.

6.2. **Метрики эффективности и шума.**  
6.2.1. Ввести метрики:  
       - количество сгенерированных AI‑задач по типам и клиникам;  
       - доля задач, переведённых в `done/cancelled` против оставленных навсегда `open`;  
       - количество задач, явно помеченных операторами как «бесполезные/спам» (если такой функционал реализован);  
       - время выполнения AI Task Manager’а и частоту ошибок.  
6.2.2. Связать эти метрики с общими OBS‑цепочками по `ARCH_DEV_OBS_CHAINS_023`, чтобы оценивать вклад AI‑задач в обработку критичных событий.

6.3. **Тесты для AI Task Manager’а.**  
6.3.1. Написать/обновить unit‑тесты для:  
       - `AiTaskAnalyzer` (набор искусственных Attention/Tasks → ожидаемый список `ProposedTask` для выбранных MVP‑сценариев);  
       - `AiTaskGenerator` (ограничения по `AiTaskSettings`, поведение при превышении лимитов, режим подтверждения);  
       - планировщика/обвязки (сценарий end‑to‑end на небольшом наборе данных).  
6.3.2. Добавить негативные тесты:  
       - недоступность AI/LLM (падение на tools‑registry) → graceful degradation (либо только правила, либо пропуск);  
       - некорректные настройки (отсутствие `AiTaskSettings` для клиники) → безопасный no‑op.

6.4. **Синхронизация документации и GAPS.**  
6.4.1. После реализации обновить:  
       - `DEV_PROMPTS_NEXT.md` — статус `DEV_PROMPT_TASKS_AI_021`;  
       - `BACKEND_GAPS_Tasks_NEXT.md` — отметить закрытые/уточнённые пункты TASK‑2;  
       - `NONFUNCTIONAL_AUDIT_NEXT.md` (OBS‑2) — зафиксировать, что AI Task Manager покрыт логами/метриками.  
6.4.2. При необходимости дополнить `ARCH_AUDIT_NEXT.md` описанием реализованного AI Task Manager’а и критериев его эффективности (что считать успешной работой/шумом).

---

