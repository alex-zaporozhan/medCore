## ARCH_DEV_CRM_AI_009_TASKS — сверх‑детализированные dev‑таски

> Связанная архитектура: `ARCH_DEV_CRM_AI_009.md`  
> Связанный DEV_PROMPT: `DEV_PROMPT_CRM_AI_009` (P2, CRM‑3, OMNI‑3)

---

### 1. Understand — текущая интеграция CRM ↔ Omnichannel ↔ AI

1.1. **Инвентаризация CRM‑сервисов и точек изменения лида.**  
1.1.1. В backend‑модулях CRM найти:  
       - `LeadService` и смежные сервисы (`LeadPipeline`, `LeadStage`, `LeadCard`, `LeadNote`);  
       - все методы, которые меняют стадии/поля лида или создают/закрывают лиды.  
1.1.2. Для каждого метода зафиксировать:  
       - какие параметры он принимает (есть ли `clinic_id`, `actor`, причины изменения);  
       - используются ли state‑machine/валидаторы стадий;  
       - есть ли уже отдельные ветки/флаги для AI‑инициированных изменений.

1.2. **Инвентаризация существующих AI‑клиентов и tools, связанных с CRM.**  
1.2.1. В `ai/tools_registry.py`, Omnichannel‑orchestratorе и связанных модулях найти:  
       - зарегистрированные AI‑tools, которые уже работают с CRM/лидами (если есть);  
       - любые прямые вызовы AI/LLM, где в промпты явно подмешиваются данные о лидах, стадиях, задачах.  
1.2.2. Зафиксировать, какие из этих вызовов:  
       - только «советуют» (read‑only сценарии);  
       - уже меняют CRM‑данные (двигают стадии, создают задачи) и проходят ли они через `LeadService`/Tasks‑сервисы.

1.3. **Инвентаризация интеграции CRM ↔ Omnichannel.**  
1.3.1. В роутерах и фронте CRM/Omnichannel (`admin_crm.py`, Omnichannel‑API, `AdminSalesPipelinePage`, Omnichannel UI) найти:  
       - переходы из CRM‑Kanban в Omnichannel (открытие чата по лиду/контакту);  
       - обратные переходы из Omnichannel в CRM (открытие карточки лида, создание лида из чата);  
       - наличие/отсутствие AI‑кнопок на этих связках (например, «AI‑рекомендация стадии»).  
1.3.2. Зафиксировать, где сейчас UI ожидает AI‑поведение, а backend ещё не даёт безопасных API.

1.4. **Сопоставление с GAPS и другими ARCH_DEV.**  
1.4.1. Открыть:  
       - `BACKEND_GAPS_CRM_NEXT.md` (CRM‑3);  
       - `BACKEND_GAPS_Omnichannel_NEXT.md` (OMNI‑3);  
       - `ARCH_DEV_CRM_EVENTS_007.md`, `ARCH_DEV_CRM_MONEY_008.md`;  
       - `ARCH_DEV_OMNI_REGISTRY_015.md`, `ARCH_DEV_TASKS_MODEL_020.md`, `ARCH_DEV_TASKS_AI_021.md`.  
1.4.2. Для каждого GAPS CRM‑3/OMNI‑3 пометить, какие файлы/участки кода должны быть изменены в рамках этого DEV_PROMPT, а какие относятся к соседним промптам (чтобы избежать дублирования).

---

### 2. Design‑to‑code — CRM‑AI‑tools и контракты LeadService

2.1. **Уточнить и зафиксировать список CRM‑AI‑tools v1.**  
2.1.1. Подтвердить минимальный набор инструментов (согласно `ARCH_DEV_CRM_AI_009.md`):  
       - read‑only: `suggest_next_stage_for_lead`, `summarize_lead_context`;  
       - действия: `update_lead_stage`, `create_task_for_lead`.  
2.1.2. Определить для каждого tool:  
       - чёткое назначение;  
       - ограничения по ролям/пермишенам;  
       - допустимые частоты вызова (чтобы не генерировать лишний шум и нагрузку).

2.2. **Спроектировать DTO для CRM‑AI‑tools.**  
2.2.1. В отдельном модуле DTO (например, `src/application/dto/crm_ai_dto.py`):  
       - оформить классы `SuggestNextStageInput/Output`, `UpdateLeadStageInput/Output`, `CreateLeadTaskInput/Output` по эскизам из `ARCH_DEV_CRM_AI_009.md`, добавив при необходимости поля:  
         - `trace_id`, `initiated_by_ai`, `reason`, `clinic_id`, `lead_id`;  
         - ограничения типов (UUID, datetime и т.п.).  
2.2.2. Убедиться, что DTO:  
       - не тянут избыточные поля лида (особенно ПД) в AI‑слой;  
       - удобны для сериализации через tools‑registry (JSON‑совместимые типы).

2.3. **Спроектировать расширения LeadService для AI‑сценариев.**  
2.3.1. В `LeadService` (или смежном CRM‑сервисе) спроектировать методы/флаги:  
       - `update_stage_from_ai(lead_id, target_stage_id, reason, context) -> UpdateLeadStageResult`;  
       - `get_lead_context_for_ai(lead_id, clinic_id) -> LeadContextForAi` (агрегированные данные без ПД при `allow_personal_data=False`).  
2.3.2. Зафиксировать, что все action‑tools (`update_lead_stage`, `create_task_for_lead`) будут использовать эти методы, а не обходить сервис.

2.4. **Спроектировать ограничения по ПД и tokenization для CRM‑AI.**  
2.4.1. На основе `ARCH_DEV_OMNI_POLICY_016.md` и `ARCH_DEV_AI_TOKENIZATION_025.md` описать:  
       - какие поля лида/контакта могут попадать во внешние AI при `allow_personal_data=True`;  
       - как выглядят токены (`LEAD#...`, `PATIENT#...`) и где они используются в DTO и промптах;  
       - какие агрегаты (суммы, стадии, счётчики) можно безопасно передавать в любом режиме.  
2.4.2. Зафиксировать эти правила в docstring/комментариях к DTO/LeadService, чтобы реализация не отходила от политики ПД.

---

### 3. Implement — backend: реализация CRM‑AI‑tools и handlers

3.1. **Реализовать методы LeadService для AI‑сценариев.**  
3.1.1. Добавить в `LeadService`:  
       - `get_lead_context_for_ai` — сбор контекста по лиду:  
         - стадия, сумма/потенциал (`estimated_value`), актуальные задачи/Attention, базовые атрибуты (без ПД при необходимости);  
       - `update_stage_from_ai` — смена стадии:  
         - проверка допустимости перехода (state‑machine из `CRM_EVENTS_007`);  
         - логирование инициатора (`ai`) и причины (`reason` из DTO);  
         - корректная генерация доменных событий для автодвижения.  
3.1.2. Обеспечить, чтобы для AI‑переходов использовались те же инварианты, что и для ручных операций (никаких «скрытых» обходов).

3.2. **Зарегистрировать CRM‑AI‑tools в tools‑registry.**  
3.2.1. В `ai/tools_registry.py` (или аналогичном модуле):  
       - добавить дескрипторы tools: `suggest_next_stage_for_lead`, `update_lead_stage`, `create_task_for_lead`;  
       - привязать к ним:  
         - `input_schema`/`output_schema` — DTO из `crm_ai_dto.py`;  
         - `required_permissions`/`allowed_roles` (например, CRM‑операторы/менеджеры, с учётом RBAC‑матрицы).  
3.2.2. Убедиться, что tools используют `SafeAiClient`/`AiSanitizer` и tokenization‑слой через Orchestrator по `ARCH_DEV_OMNI_REGISTRY_015` и `ARCH_DEV_OMNI_POLICY_016`.

3.3. **Реализовать handlers для CRM‑AI‑tools.**  
3.3.1. Для `suggest_next_stage_for_lead`:  
       - получить контекст лида через `LeadService.get_lead_context_for_ai`;  
       - сформировать промпт/запрос к AI (через tools‑registry/Orchestrator) без нарушения политики ПД;  
       - вернуть `SuggestNextStageOutput` с рекомендованной стадией/доверительными параметрами.  
3.3.2. Для `update_lead_stage`:  
       - принять входной DTO, проверить RBAC и связь лида с `clinic_id`;  
       - вызвать `LeadService.update_stage_from_ai`, вернуть `UpdateLeadStageOutput`;  
       - логировать факт AI‑инициированной смены стадии.  
3.3.3. Для `create_task_for_lead`:  
       - использовать TaskService/AttentionFeedService согласно `ARCH_DEV_TASKS_MODEL_020`/`ARCH_DEV_TASKS_AI_021`;  
       - создавать задачу с `created_by="ai"` и связью с `lead_id`/`AttentionItem` (если есть).

3.4. **Интеграция с Tasks/Attention.**  
3.4.1. В handlers/LeadService обеспечить, что:  
       - рискованные/крупные кейсы (лиды с большой суммой, застоявшиеся стадии) могут генерировать Attention/Tasks через Task‑слой;  
       - AI‑инициированные задачи помечаются как `created_by="ai"` и содержат информацию об источнике (лид, Omnichannel‑диалог).  
3.4.2. При необходимости добавить простую обвязку (`CrmAiTaskBridge`), которая скрывает детали связи между CRM‑AI‑tools и TaskService.

---

### 4. Integrate — CRM‑AI в Omnichannel и CRM‑UI

4.1. **Подключить CRM‑AI‑tools в Omnichannel Orchestrator.**  
4.1.1. В Omnichannel‑orchestratorе (backend):  
       - для сценариев анализа диалога (`ConversationAiAnalysis`) добавить вызовы:  
         - `suggest_next_stage_for_lead` (когда контекстом является лид/воронка);  
         - `create_task_for_lead` для предложений follow‑up задач.  
4.1.2. Обеспечить, чтобы Orchestrator не выполнял CRM‑действия автоматически, если бизнес‑логикой предусмотрено подтверждение оператором:  
       - в таких случаях возвращать в UI только рекомендации/предложения.

4.2. **Интегрировать CRM‑AI‑recommendations в Omnichannel UI.**  
4.2.1. В Omnichannel‑фронте (страницы чата/контакта):  
       - добавить область «AI‑рекомендации по лиду», где:  
         - отображаются предложенные следующие стадии/действия;  
         - есть кнопки «Применить»/«Игнорировать» для каждой рекомендации.  
4.2.2. Связать эти кнопки с action‑tools `update_lead_stage`/`create_task_for_lead`, вызывая их через backend‑API.

4.3. **Интеграция с CRM‑Kanban и UI лида.**  
4.3.1. В `AdminSalesPipelinePage` и карточке лида:  
       - добавить элементы:  
         - кнопка «AI‑рекомендация стадии» (вызов `suggest_next_stage_for_lead`);  
         - индикатор наличия AI‑рекомендаций (например, бейдж на колонке/карточке).  
4.3.2. Обеспечить, чтобы в beta‑режиме (по `ARCH_DEV_OMNI_UI_017`) эти функции были помечены как `beta` и их поведение не вводило операторов в заблуждение (например, не меняло стадии без явного подтверждения).

4.4. **Учесть согласованность с автодвижением и деньгами.**  
4.4.1. Проверить, что AI‑действия не ломают:  
       - автодвижение лидов по событиям из `CRM_EVENTS_007` (события доменов остаются основным драйвером);  
       - обновление `estimated_value`/`actual_value` из `CRM_MONEY_008`.  
4.4.2. При необходимости ограничить AI‑изменения стадий до «мягких» сценариев (уточнение внутри группы стадий) или «draft»‑режима (только рекомендации).

---

### 5. Observe — логирование и метрики CRM‑AI

5.1. **Логирование AI‑действий над лидами.**  
5.1.1. Добавить логи в handlers/LeadService для:  
       - всех вызовов `suggest_next_stage_for_lead`, `update_lead_stage`, `create_task_for_lead`;  
       - с полями: `trace_id`, `clinic_id`, `lead_id`, тип действия (`suggest_stage`, `update_stage`, `create_task`), инициатор (`ai`/`operator`), результат (успех/ошибка, код).  
5.1.2. Убедиться, что логи не содержат ПД (ФИО/телефоны), только идентификаторы и агрегированные значения.

5.2. **Метрики по эффективности и использованию CRM‑AI.**  
5.2.1. Ввести метрики:  
       - количество AI‑рекомендаций по лидам (по клиникам/пользователям);  
       - доля рекомендаций, которые были приняты (смена стадии, создание задачи) vs проигнорированные;  
       - количество ошибок/отказов по причинам (RBAC, валидация, конфликты state‑machine).  
5.2.2. Если это вписывается в OBS‑инфраструктуру, добавить таймеры:  
       - latency вызовов CRM‑AI‑tools;  
       - время отклика AI‑слоя на запросы CRM.

5.3. **Связь с Tasks/Attention и AI Task Manager.**  
5.3.1. Для кейсов, когда AI‑рекомендации не реализуются автоматически, но должны приводить к задачам:  
       - убедиться, что создаваемые Tasks имеют корректные поля (`created_by="ai"`, связь с `AttentionItem`/`LeadCard`) и попадают в аналитику `DEV_PROMPT_TASKS_AI_021`.  
5.3.2. Зафиксировать, какие типы CRM‑AI‑сигналов в будущем будут анализироваться AI Task Manager’ом (чтобы избежать дублирования логики).

---

### 6. Stabilize — тесты и синхронизация артефактов

6.1. **Покрытие backend CRM‑AI тестами.**  
6.1.1. Написать/обновить unit‑тесты для:  
       - `LeadService.get_lead_context_for_ai` (правильная агрегация данных, отсутствие ПД при нужных настройках);  
       - `LeadService.update_stage_from_ai` (допустимые и недопустимые переходы стадий, корректное логирование и события);  
       - handlers `suggest_next_stage_for_lead`, `update_lead_stage`, `create_task_for_lead` (основные позитивные/негативные сценарии).  
6.1.2. Добавить тесты на соблюдение RBAC/clinic‑границ:  
       - невозможность менять лиды чужой клиники;  
       - корректные ошибки при недостаточных правах.

6.2. **Интеграционные тесты с Omnichannel/Tasks.**  
6.2.1. Добавить интеграционные тесты, покрывающие цепочки:  
       - Omnichannel‑диалог → CRM‑AI‑рекомендация → принятие рекомендации → изменение стадии/создание задачи;  
       - Omnichannel/CRM‑UI → явный вызов CRM‑AI‑tools → ожидаемые обновления в CRM/Tasks.  
6.2.2. Убедиться, что при ошибках AI/Orchestrator’а UI получает контролируемые сообщения, а данные CRM не оказываются в «подвешенном» состоянии.

6.3. **Синхронизация документации и GAPS.**  
6.3.1. После завершения реализации обновить:  
       - `DEV_PROMPTS_NEXT.md` — статус `DEV_PROMPT_CRM_AI_009`;  
       - `BACKEND_GAPS_CRM_NEXT.md` (CRM‑3) и, при необходимости, `BACKEND_GAPS_Omnichannel_NEXT.md` (OMNI‑3);  
       - `ARCH_AUDIT_NEXT.md`, если требуется зафиксировать, что AI‑действия в CRM реализованы по инвариантам.  
6.3.2. Зафиксировать в арх‑артефактах (при необходимости), какие CRM‑AI‑сценарии реализованы в v1 и какие остаются в roadmap.

---

### На потом (улучшения/долги после v1)

N.1. **Семантика стадий как first‑class конфиг.**  
N.1.1. Добавить UI в админке для настройки `pipeline: semantic → stage_id` (например, в настройках pipeline/stages).  
N.1.2. Добавить seed/миграцию по умолчанию для новых клиник/пайплайнов (автозаполнение семантики по `code`/`name`/`order`).  
N.1.3. Расширить набор семантик (если нужно по `CRM_EVENTS_007`): `qualified`, `contacted`, `proposal`, `negotiation`, `no_show` и т.п.  

N.2. **Строже и прозрачнее поведение state‑machine.**  
N.2.1. Для AI‑переходов: “draft‑режим” по умолчанию (только рекомендации), а auto‑apply включать флагом/политикой клиники.  
N.2.2. Для manual drag&drop: опционально включаемая строгая валидация (сейчас только diagnostic‑лог).  
N.2.3. Ввести единый код ошибок для нарушений матрицы (`stage_transition_not_allowed`, `semantics_not_configured`) и стабильные 4xx в API.  

N.3. **Observability: разрезы метрик и качество рекомендаций.**  
N.3.1. Добавить метрики принятия/игнора на уровне UI событий (включая user_id/role где допустимо) и связать с trace_id.  
N.3.2. Добавить latency для AI‑слоя и “time‑to‑accept” (время от генерации рекомендации до принятия/игнора).  
N.3.3. Добавить распределение по типам рекомендаций и pipeline/stage семантикам (без ПД).  

N.4. **Omnichannel orchestrator интеграция (по OMNI‑таскам).**  
N.4.1. Устойчивый контракт `chat/contact → lead_token` (или `lead_id`) + кеш/идемпотентность резолва.  
N.4.2. Вынос “какие рекомендации показывать” в единый слой policy/rules (чтобы не дублировать в CRM UI и Omni UI).  

N.5. **Стабилизация и тест‑инфраструктура.**  
N.5.1. Контракт‑тесты на API для CRM‑AI и semantics endpoints.  
N.5.2. Интеграционные тесты “pipeline semantics configured/unconfigured” (fallback‑поведение, запреты, события).  
N.5.3. E2E тесты UI (Kanban/Omni) на сценарии “suggest → apply/ignore → metrics/logs”.  

