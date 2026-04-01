## ARCH_DEV_OMNI_REGISTRY_015_TASKS — сверх‑детализированные dev‑таски

> Связанная архитектура: `ARCH_DEV_OMNI_REGISTRY_015.md`  
> Связанный DEV_PROMPT: `DEV_PROMPT_OMNI_REGISTRY_015` (P1, OMNI‑1, OMNI‑3)

---

### 1. Understand — текущее состояние Orchestrator’а и AI‑вызовов

1.1. **Найти все места, где AI вызывает доменные сервисы напрямую.**  
1.1.1. В `OmnichannelAiOrchestrator`, Chat AI‑сервисах, анализе диалогов, AI Task Manager’е и смежных модулях найти все вызовы, где:  
       - код явно использует BookingService/CrmService/TasksService и т.п. в AI‑контексте;  
       - нет абстракции инструментов (реестр + handler).  
1.1.2. Зафиксировать список таких вызовов с указанием домена и типа операции (create_booking, cancel_booking, create_lead и т.д.).

1.2. **Понять, как сейчас устроен Orchestrator.**  
1.2.1. Изучить текущую реализацию AI‑оркестратора:  
       - как он формирует контекст для LLM;  
       - как (если уже) реализован function‑calling (список функций/tools, структура аргументов, обработка результатов);  
       - какие ограничения/проверки (RBAC, клиники, политика ПД) уже есть, а какие отсутствуют.  
1.2.2. Сопоставить с GAPS `BACKEND_GAPS_Omnichannel_NEXT.md` (OMNI‑1, OMNI‑3) и `NONFUNCTIONAL_AUDIT_NEXT.md` (OBS‑2).

1.3. **Согласовать минимальный набор AI‑tools для vNext.**  
1.3.1. На основе `ARCH_BOOKING_NEXT`, `ARCH_CRM_NEXT`, `ARCH_TASKS_NEXT` и `ARCH_OMNICHANNEL_NEXT` утвердить с @ARCH/@LEAD минимальный состав инструментов для первой версии:  
       - Booking/Schedule: `get_available_slots`, `create_booking`, `cancel_booking`, `reschedule_booking`;  
       - CRM/Leads: `create_lead_from_conversation`, `update_lead_stage`;  
       - Tasks/Attention: `create_task_from_attention`, `list_open_tasks_for_context`;  
       - Read‑only: `get_patient_summary`, `get_booking_summary` (без лишних ПД, с учётом политики ПД/токенизации).

---

### 2. Design‑to‑code — интерфейс AiTool, AiToolContext и реестр

2.1. **Спроектировать интерфейс `AiTool` и контекст `AiToolContext`.**  
2.1.1. Определить структуру `AiTool` по ARCH‑документу:  
       - `id: str`, `description: str`, `input_schema`, `output_schema`, `required_permissions`/`allowed_roles`, `handler(context, input)`.  
2.1.2. Определить `AiToolContext`:  
       - `trace_id`, `clinic_id`, `user_id`/`system_actor`, `roles`/`permissions`, источник вызова (`omni_chat`, `ai_task_manager`, `admin_tool` и т.п.).  
2.1.3. Зафиксировать, что все handlers получают контекст + входные DTO и не зависят от деталей Orchestrator’а.

2.2. **Спроектировать структуру реестра tools.**  
2.2.1. В модуле `src/application/ai/tools_registry.py` (или аналогичном) описать:  
       - хранение зарегистрированных инструментов (`TOOLS_REGISTRY` или класс‑реестр);  
       - методы: `get_tool(tool_id)`, `list_tools(context)` (с фильтрацией по ролям/клиникам/каналу).  
2.2.2. Продумать способ регистрации новых инструментов (функции/декораторы, отдельные модули, импортящиеся реестром).

---

### 3. Implement — реализация tools‑registry и базового набора инструментов

3.1. **Реализовать модуль `tools_registry`.**  
3.1.1. Создать модуль с определениями `AiTool`, `AiToolContext` и реализацией реестра (`TOOLS_REGISTRY`).  
3.1.2. Обеспечить типизацию input/output через pydantic‑модели, чтобы Orchestrator мог валидировать полезную нагрузку.

3.2. **Реализовать базовый набор инструментов vNext.**  
3.2.1. Для Booking/Schedule:  
       - создать handlers, которые через BookingService выполняют `get_available_slots`, `create_booking`, `cancel_booking`, `reschedule_booking`;  
       - гарантировать, что внутри они:  
         - уважают RBAC/clinic_id;  
         - не обходят фасад завершения визита/статусы, где это применимо.  
3.2.2. Для CRM/Leads:  
       - handlers для `create_lead_from_conversation`, `update_lead_stage` через CRM‑сервисы, без дублирования CRM‑логики в AI‑слое.  
3.2.3. Для Tasks/Attention:  
       - handlers для `create_task_from_attention`, `list_open_tasks_for_context`, использующие модель Tasks↔Attention из `ARCH_DEV_TASKS_MODEL_020_TASKS.md`.

3.3. **Обеспечить корректную работу с токенизацией в handlers.**  
3.3.1. В инструментах, где вход/выход содержит ссылки на сущности, использовать токенизацию (`PATIENT#...`, `BOOKING#...` и т.п.) согласно `ARCH_DEV_AI_TOKENIZATION_025.md`:  
       - при входе из AI: распарсить токены → внутренние id;  
       - при возврате в AI (если нужно) — конвертировать id в токены.  
3.3.2. Не передавать «голые» id или ПД наружу при `allow_personal_data=False`.

---

### 4. Implement — интеграция Orchestrator’а с tools‑registry

4.1. **Обновить OmnichannelAiOrchestrator для работы через реестр.**  
4.1.1. В Orchestrator’е убрать жёсткие вызовы доменных сервисов, заменить их:  
       - формированием `AiToolContext` (на основе текущего чата/пользователя/клиники);  
       - получением списка доступных инструментов через `list_tools(context)`;  
       - вызовом нужного handler’а через `TOOLS_REGISTRY`.  
4.1.2. Обеспечить, что Orchestrator не знает деталей реализации handlers, только контракты input/output.

4.2. **Интегрировать Orchestrator с SafeAiClient и tokenization.**  
4.2.1. Использовать `build_safe_ai_client` / SafeAiClient по `clinic_id` (см. `ARCH_DEV_OMNI_POLICY_016_TASKS.md`) для всех LLM‑вызовов.  
4.2.2. Перед передачей контекста в LLM применять tokenization‑слой (см. `ARCH_DEV_AI_TOKENIZATION_025.md`):  
       - заменять идентификаторы сущностей на токены;  
       - гарантировать отсутствие ПД в промпте при `allow_personal_data=False`.  
4.2.3. После получения ответа:  
       - распознавать токены и мапить их обратно в id;  
       - передавать только id/токены в AI‑tools, не «сырые» строки из ответа.

4.3. **Встроить RBAC и ограничения в Orchestrator.**  
4.3.1. На уровне Orchestrator’а и/или `list_tools(context)` фильтровать доступные инструменты по:  
       - ролям/пермишенам (из контекста пользователя/системы, согласно `ARCH_DEV_SEC_RBAC_022.md`);  
       - каналу (например, пациентский чат vs админский Omni‑интерфейс);  
       - типу сценария (ручной/AI‑only).  
4.3.2. Гарантировать, что LLM не видит и не может вызвать инструменты, которые недоступны в данном контексте.

---

### 5. Observe — логи и метрики AI‑tools

5.1. **Добавить структурированные логи calls/tools.**  
5.1.1. В единой точке вызова tools (реестр/Orchestrator) логировать:  
       - `trace_id`, `tool_id`, `source` (omni_chat/ai_task_manager/...);  
       - `clinic_id`, `actor` (user/system/AI);  
       - результат (`success`/`error`), коды ошибок.  
5.1.2. Убедиться, что логи не содержат ПД и совместимы с общим OBS‑форматом (см. `ARCH_DEV_OBS_CHAINS_023_TASKS.md`).

5.2. **Собрать метрики по AI‑tools.**  
5.2.1. Ввести счётчики и гистограммы:  
       - `ai_tool_calls_total{tool_id, source, status}`;  
       - `ai_tool_call_duration_seconds{tool_id}`.  
5.2.2. При наличии мониторинга — добавить графики/алерты по ключевым инструментам (например, частота ошибок `create_booking` из AI).

5.3. **Покрыть ключевые сценарии тестами.**  
5.3.1. Тесты на фильтрацию tools:  
       - проверка, что пользователи/контексты без нужных пермишенов не видят и не могут вызывать соответствующие инструменты.  
5.3.2. Тесты на корректность работы базового набора tools:  
       - корректный вызов доменных сервисов;  
       - корректная обработка ошибок и возврат структурированных результатов.  
5.3.3. Тесты интеграции с Orchestrator’ом:  
       - LLM‑симуляция function‑calling (минимальная), корректная маршрутизация вызовов через реестр.

---

### 6. Stabilize — обновление GAPS и документации

6.1. **Синхронизировать статусы GAPS и DEV_PROMPT.**  
6.1.1. Обновить `DEV_PROMPTS_NEXT.md`, указав статус `DEV_PROMPT_OMNI_REGISTRY_015`.  
6.1.2. В `BACKEND_GAPS_Omnichannel_NEXT.md` и `NONFUNCTIONAL_AUDIT_NEXT.md` отметить закрытые/уточнённые пункты OMNI‑1/OMNI‑3/OBS‑2.

6.2. **Уточнить архитектурные документы Omnichannel & AI.**  
6.2.1. При необходимости скорректировать `ARCH_OMNICHANNEL_NEXT.md` и/или `ARCH_AUDIT_NEXT.md`, чтобы зафиксировать:  
       - роль tools‑registry;  
       - ограничения Orchestrator’а;  
       - место tokenization‑слоя и политики ПД в AI‑потоке.

### "На потом"

Расширить набор tools: добавить cancel_booking, reschedule_booking, CRM/Leads и Tasks/Attention‑инструменты по мере появления стабильных фасадов в сервисах.
RBAC/фильтрация tools: вынести в list_tools_for_context полноценную фильтрацию по ролям, каналу (omni_chat vs admin), сценарию (ручной/AI‑only).
Перенос легаси AI‑сервисов: постепенно перевести ChatAiService и ConversationAnalysisService на единый SafeAiClient+tools‑registry/agent‑подход, чтобы сократить дублирование промптов и логики.

