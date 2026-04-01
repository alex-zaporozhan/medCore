## ARCH_DEV_CRM_AI_009 — AI‑подсказки и действия в CRM

> DEV_PROMPT_CRM_AI_009 — «AI‑подсказки и действия в CRM (CRM‑3, OMNI‑3)»

---

## 1. Контекст и существующее состояние

### 1.1. Роль AI в CRM‑воронке

По `BUSINESS_PLAN_NEXT.md` и `ARCH_CRM_NEXT.md`:

- CRM‑домен:
  - управляет воронкой продаж:
    - `LeadPipeline`, `LeadStage`, `LeadCard`, `LeadNote`;
  - связан с:
    - Omnichannel (контакты и диалоги),
    - Booking (записи и статусы визитов),
    - ERP (фактические деньги),
    - Tasks/Attention (сигналы по застоям/рискам).

AI‑уровень для CRM должен:

- помогать операторам:
  - рекомендовать следующее действие по лиду;
  - подсвечивать «гниющие» лиды и крупные рисковые суммы;
  - предлагать сегментацию/приоритизацию;
- в ограниченном и безопасном виде:
  - инициировать действия:
    - движение по стадиям;
    - создание задач;
    - предложение записей/офферов (в связке с Booking/Omnichannel).

### 1.2. GAP CRM‑3 и OMNI‑3

По `BACKEND_GAPS_CRM_NEXT.md`:

- **CRM‑3 — ограниченная интеграция с AI‑слоем:**
  - архитектура предполагает, что AI/Omnichannel могут:
    - двигать карточки;
    - предлагать действия;
  - backend‑API для безопасного AI‑управления стадиями/лидами ещё не оформлен как tools‑набор.

По `BACKEND_GAPS_Omnichannel_NEXT.md`:

- **OMNI‑3 — неполная интеграция AI с CRM/Booking/Tasks:**
  - Omnichannel уже связан с CRM (переход в чат из Kanban),
  - но двусторонняя AI‑интеграция (AI меняет стадии/создаёт задачи) не оформлена через tools‑registry.

Риски:

- AI‑уровень либо остаётся сугубо «советчиком» в тексте, либо вмешивается в CRM «в обход» доменных правил;
- сложно контролировать, какие действия AI может выполнять, с какими правами и в каких клиниках;
- трудно трассировать влияние AI‑решений на воронку и деньги.

### 1.3. Связанные ARCH/DEV артефакты

- `ARCH_CRM_NEXT.md` — модель CRM/воронки.
- `ARCH_DEV_CRM_EVENTS_007.md` — автодвижение лидов по событиям.
- `ARCH_DEV_CRM_MONEY_008.md` — источник правды по деньгам в CRM.
- `ARCH_OMNICHANNEL_NEXT.md`, `ARCH_DEV_OMNI_REGISTRY_015.md` — Omnichannel & AI tools‑registry.
- `ARCH_TASKS_NEXT.md`, `ARCH_DEV_TASKS_MODEL_020.md`, `ARCH_DEV_TASKS_AI_021.md` — Tasks & Attention.
- `ARCH_DEV_OMNI_POLICY_016.md`, `ARCH_DEV_AI_TOKENIZATION_025.md` — политика ПД и tokenization.

---

## 2. Целевое состояние AI‑подсказок и действий в CRM

### 2.1. Жёсткие инварианты

1. **AI действует через те же сервисы и правила, что и люди.**
   - Любое изменение лида (стадия, поля) от имени AI:
     - проходит через `LeadService` и state‑machine стадий;
     - использует те же инварианты, что и ручные операции/автодвижение по событиям.

2. **AI‑действия полностью трассируются.**
   - Для каждого AI‑решения:
     - логируется:
       - `lead_id`, `clinic_id`, пред/новая стадия, инициатор (AI/человек);
       - ссылка на исходный контекст (диалог/метрики);
     - можно восстановить «почему» и «что именно» AI сделал.

3. **AI не может выйти за рамки ролей/пермишенов.**
   - AI‑tools для CRM:
     - ограничены `required_permissions`/roles (см. RBAC);
     - не могут делать то, что недоступно человеку с аналогичными правами.

4. **Рекомендации и действия разделены.**
   - AI может:
     - выдавать рекомендации (предложение стадии/действия) без автоизменения данных;
     - либо выполнять действия в ограниченных сценариях (по явной команде оператора или конфигу).

5. **AI‑операции опираются на честные данные CRM/ERP/Booking.**
   - Рекомендации/решения:
     - используют:
       - фактические стадии и события (`CRM_EVENTS_007`);
       - ERP‑данные (`CRM_MONEY_008`, `ERP_REPORTS_012`);
       - Tasks/Attention сигналы.

---

## 3. Архитектурный дизайн AI‑tools для CRM

### 3.1. Категории CRM‑AI‑инструментов

Опираясь на `ARCH_DEV_OMNI_REGISTRY_015.md` и `ARCH_CRM_NEXT.md`, вводим категории:

- **Read‑only / аналитика:**
  - `suggest_next_stage_for_lead`
  - `summarize_lead_context`
- **Действия (под контролем RBAC/оператора):**
  - `update_lead_stage`
  - `create_task_for_lead`

Каждый tool:

- регистрируется в `ai/tools_registry.py`;
- имеет чёткий `input_schema`/`output_schema` и ограничения по ролям.

### 3.2. Примеры DTO (эскиз)

**suggest_next_stage_for_lead**

- Вход:

```python
class SuggestNextStageInput(BaseModel):
    clinic_id: UUID
    lead_id: UUID
```

- Выход:

```python
class StageSuggestion(BaseModel):
    stage_id: UUID
    confidence: float
    rationale: str | None = None


class SuggestNextStageOutput(BaseModel):
    lead_id: UUID
    current_stage_id: UUID
    suggested_stage: StageSuggestion | None
```

**update_lead_stage**

- Вход:

```python
class UpdateLeadStageInput(BaseModel):
    clinic_id: UUID
    lead_id: UUID
    target_stage_id: UUID
    reason: str | None = None
    initiated_by_ai: bool = True
```

- Выход:

```python
class UpdateLeadStageOutput(BaseModel):
    success: bool
    old_stage_id: UUID | None = None
    new_stage_id: UUID | None = None
    error_code: str | None = None
    error_message: str | None = None
```

**create_task_for_lead**

- Вход:

```python
class CreateLeadTaskInput(BaseModel):
    clinic_id: UUID
    lead_id: UUID
    title: str
    description: str | None = None
    due_date: datetime | None = None
    priority: str | None = None
    initiated_by_ai: bool = True
```

- Выход:

```python
class CreateLeadTaskOutput(BaseModel):
    task_id: UUID
    lead_id: UUID
```

---

## 4. Интеграция с LeadService, CRM‑слоем и событиями

### 4.1. LeadService как единая точка изменения лида

- AI‑tools **не** изменяют `LeadCard` напрямую:
  - все операции смены стадий/создания задач идут через:
    - `LeadService` (смена стадий) с использованием событийной логики из `ARCH_DEV_CRM_EVENTS_007.md`;
    - Task/Attention‑сервисы для задач.

- Возможный подход:
  - добавить в `LeadService` методы/флаги:
    - `update_stage_from_ai(lead_id, stage_id, reason, context)`:
      - проверяет допустимость перехода (state‑machine);
      - логирует инициатора `AI` и причину;
    - `get_lead_context_for_ai(lead_id)`:
      - агрегирует данные для промптов/аналитики (но без ПД, если запрещено).

### 4.2. Согласованность с автодвижением и деньгами

- AI‑действия не должны ломать логику:
  - автодвижения лидов по событиям (`CRM_EVENTS_007`);
  - обновления `estimated_value`/`actual_value` (`CRM_MONEY_008`).

- Принцип:
  - события доменов (Booking/ERP/Omnichannel) остаются **главным** источником движения;
  - AI‑движения:
    - используются:
      - либо для fine‑tuning стадий (например, уточнение внутри одной крупной категории);
      - либо только как рекомендации (оператор подтверждает).

---

## 5. Связь с Omnichannel & Tasks

### 5.1. Omnichannel контекст для CRM‑AI

- В Omnichannel:
  - AI‑анализ диалогов (`ConversationAiAnalysis`) может:
    - инициировать вызовы CRM‑AI‑tools:
      - `suggest_next_stage_for_lead`;
      - `create_task_for_lead`.

- Orchestrator:
  - по результату AI:
    - либо показывает рекомендации оператору в Omnichannel UI;
    - либо (в ограниченных сценариях) вызывает action‑tools (`update_lead_stage`, `create_task_for_lead`) по подтверждению оператора.

### 5.2. Tasks & Attention

- Для рискованных/важных кейсов:
  - AI‑решения могут создавать/обновлять AttentionItem/Tasks:
    - например:
      - лидам с крупной суммой без движения → `TASK`/`Attention` с рекомендацией follow‑up;
      - лиды с частыми отменами → задача для менеджера.

- Связь с `ARCH_DEV_TASKS_MODEL_020.md`:
  - задачи, созданные AI, помечаются как `created_by="ai"`;
  - сохраняется связь `Task ↔ LeadCard ↔ AttentionItem`.

---

## 6. Безопасность, ПД и наблюдаемость

### 6.1. Политика ПД и tokenization

- CRM‑AI‑tools:
  - не передают ПД (ФИО, телефоны, адреса) во внешние AI при `allow_personal_data=False`;
  - используют:
    - токены (`LEAD#...`, `PATIENT#...`) там, где это необходимо;
    - агрегированные числовые/категориальные данные (суммы, количества, стадии) для аналитики.

### 6.2. Observability

- Логирование:
  - для каждого AI‑действия над лидом:
    - `trace_id`, `lead_id`, `clinic_id`, тип действия (`suggest_stage`, `update_stage`, `create_task`), инициатор (`ai`/`operator`), результат.

- Метрики:
  - количество AI‑рекомендаций;
  - доля рекомендаций, принятых операторами;
  - количество AI‑инициированных изменений стадий/задач;
  - ошибки/отказы по кодам и причинам (RBAC, валидация, конфликт с событиями).

---

## 7. Dev‑чек‑лист для DEV_PROMPT_CRM_AI_009

### 7.1. Аналитика

1. Изучить:
   - `LeadService`, `admin_crm.py`, `AdminSalesPipelinePage`;
   - существующие интеграции с Omnichannel (переходы из Kanban в чат и обратно).
2. Сопоставить с:
   - `BACKEND_GAPS_CRM_NEXT.md` (CRM‑3);
   - `ARCH_DEV_CRM_EVENTS_007.md`, `ARCH_DEV_CRM_MONEY_008.md`;
   - `ARCH_DEV_OMNI_REGISTRY_015.md`.

### 7.2. Проектирование CRM‑AI‑tools

3. Определить список CRM‑tools v1:
   - минимум: `suggest_next_stage_for_lead`, `update_lead_stage`, `create_task_for_lead`.
4. Описать DTO (input/output) для каждого tool:
   - добавить в подходящий DTO‑модуль (например, `crm_ai_dto.py`).

### 7.3. Реализация handlers и интеграция с tools_registry

5. В `ai/tools_registry.py`:
   - зарегистрировать CRM‑tools с:
     - `id`, `description`, `input_schema`, `output_schema`;
     - `required_permissions`/`allowed_roles` (например, CRM‑операторы/менеджеры).
6. Реализовать handlers:
   - использовать `LeadService` и Tasks‑сервисы;
   - соблюдать:
     - state‑machine стадий;
     - политику ПД/tokenization.

### 7.4. Интеграция с Omnichannel и UI

7. В Omnichannel/CRM‑UI:
   - подключить CRM‑AI‑tools:
     - показывать рекомендации по стадию/действиям;
     - дать операторам возможность принять/отклонить их;
   - в beta‑режиме явно пометить AI‑функции как `beta` (см. `ARCH_DEV_OMNI_UI_017.md`).

### 7.5. Observability и Tasks

8. Добавить логирование/метрики для CRM‑AI‑действий.
9. Интегрировать с Tasks/Attention:
   - для сценариев, где AI‑сигналы должны создавать задачи, а не просто менять стадии.

### 7.6. Документация и GAPS

10. После реализации:
    - обновить:
      - `DEV_PROMPTS_NEXT.md` (статус DEV_PROMPT_CRM_AI_009);
      - `BACKEND_GAPS_CRM_NEXT.md` (CRM‑3);
      - при необходимости `BACKEND_GAPS_Omnichannel_NEXT.md` (OMNI‑3) и `NONFUNCTIONAL_AUDIT_NEXT.md`.

