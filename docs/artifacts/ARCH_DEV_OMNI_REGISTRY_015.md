## ARCH_DEV_OMNI_REGISTRY_015 — tools‑registry и AI Orchestrator

> DEV_PROMPT_OMNI_REGISTRY_015 — «tools‑registry и AI Orchestrator (OMNI‑1, OMNI‑3)»

---

## 1. Контекст и существующее состояние

### 1.1. Роль Omnichannel & AI в системе

- Omnichannel объединяет каналы коммуникации (мессенджеры, email, web/PWA‑чат) и поверх них строит:
  - единый слой диалогов (`Conversation`, `OmnichannelMessage`, `OmnichannelContact`);
  - AI‑уровень, который:
    - помогает операторам;
    - инициирует действия в доменах (Booking, CRM, Tasks, Loyalty и т.д.);
    - генерирует отчёты/аналитику.

### 1.2. Проблема (GAPS OMNI‑1, OMNI‑3)

- Сейчас в коде:
  - есть зачатки `OmnichannelAiOrchestrator` и отдельных AI‑сервисов (Chat AI, анализ диалогов, AI‑tasks);
  - вызовы доменов из AI‑уровня не нормализованы:
    - нет единого `tools_registry`, описывающего разрешённые операции;
    - часть логики жёстко зашита в orchestrator или сервисы;
    - трассировка действий AI по доменам затруднена.
- Риски:
  - сложно контролировать, что именно AI может делать (и в каких границах ролей/RBAC);
  - сложно отследить ошибочные/опасные действия;
  - тяжело расширять набор инструментов без дублирования кода.

### 1.3. Связанные ARCH/DEV артефакты

- `ARCH_OMNICHANNEL_NEXT.md` — целевая модель Omnichannel & AI.
- `ARCH_DECISIONS_NEXT.md` — принципы AI‑слоя:
  - AI всегда использует доменные сервисы, не пишет напрямую в БД;
  - не обходит RBAC/multi‑tenant;
  - все AI‑действия трассируются.
- `ARCH_DEV_OMNI_POLICY_016.md` — политика ПД и AI‑провайдеров (SafeAiClient, AiSanitizer).
- `ARCH_DEV_AI_TOKENIZATION_025.md` — tokenization‑слой для безопасной работы с идентификаторами в AI.
- Доменные ARCH‑файлы (`ARCH_BOOKING_NEXT`, `ARCH_CRM_NEXT`, `ARCH_TASKS_NEXT` и др.) — описывают операции, которые могут быть обёрнуты в AI‑tools.

---

## 2. Целевое состояние: tools‑registry и Orchestrator

### 2.1. Жёсткие инварианты

1. **Все действия AI над доменами проходят через tools‑registry.**
   - Ни один AI‑контекст (Omni‑чат, AI‑reports, AI‑tasks) не вызывает доменные сервисы напрямую.
   - Любой «инструмент» описан в реестре и имеет:
     - чёткий контракт входа/выхода;
     - ограничения по ролям/пермишенам/клиникам;
     - логи и метрики.

2. **Orchestrator работает только с зарегистрированными инструментами.**
   - AI‑агент (LLM‑уровень) видит список доступных tools:
     - с описаниями и типами аргументов;
     - но не знает деталей реализации.

3. **Tools‑registry не обходит RBAC и политику ПД.**
   - Каждый tool:
     - проверяет пермишены/роль (или принимает уже проверенный контекст);
     - использует SafeAiClient/AiSanitizer только там, где это нужно (для внешних AI‑вызовов);
     - не нарушает `allow_personal_data` и tokenization‑политику.

4. **Все вызовы инструментов трассируются.**
   - Для каждого вызова:
     - лог/метрики содержат: tool_id, контекст (clinic_id, user_id/role или системный), результат/ошибку, trace_id.

5. **Tools‑registry расширяем без рефакторинга Orchestrator.**
   - Добавление нового инструмента:
     - не требует изменения ядра orchestrator’а;
     - сводится к регистрации описания/обработчика в одном месте.

### 2.2. Базовый набор инструментов (vNext)

> Конкретный перечень уточняется по `ARCH_BOOKING_NEXT`, `ARCH_CRM_NEXT`, `ARCH_TASKS_NEXT`, но архитектурно закладываем категории:

- **Booking / Schedule:**
  - `get_available_slots`
  - `create_booking`
  - `cancel_booking`
  - `reschedule_booking`
- **CRM / Leads:**
  - `create_lead_from_conversation`
  - `update_lead_stage`
- **Tasks & Attention:**
  - `create_task_from_attention`
  - `list_open_tasks_for_context`
- **Information / Read‑only:**
  - `get_patient_summary` (через безопасный слой, без лишних ПД);
  - `get_booking_summary`.

Каждый инструмент:

- строго типизирован:
  - вход: DTO (в т.ч. токены вместо «голых» id, если инструмент инициируется из AI);
  - выход: DTO, пригодный для отображения в UI и/или дальнейших действий.

---

## 3. Архитектурный дизайн tools‑registry

### 3.1. Структура модуля

- Новый модуль, например `src/application/ai/tools_registry.py` (или аналогичная структура).
- Содержит:
  - описание DTO для входов/выходов;
  - интерфейс `AiTool`:
    - `id: str`;
    - `description: str`;
    - `input_schema`: pydantic‑модель;
    - `output_schema`: pydantic‑модель;
    - `allowed_roles` / `required_permissions` / ограничения по доменам/clinic_id;
    - `handler(context, input) -> output`.
  - реестр:
    - `TOOLS_REGISTRY: dict[str, AiTool]` или класс‑реестр с методами:
      - `get_tool(tool_id)`;
      - `list_tools(context)` (фильтрует по роли/клинике/каналу).

### 3.2. Контекст вызова инструмента

- Вводим общий `AiToolContext`:
  - `trace_id`;
  - `clinic_id`;
  - `user_id`/`system_actor` (для системных/AI‑тасков);
  - `roles`/`permissions`;
  - источник вызова (`omni_chat`, `ai_task_manager`, `admin_tool`, ...).
- Контекст:
  - создаётся Orchestrator’ом / вызывающим кодом;
  - передаётся во все handlers;
  - используется для:
    - проверки прав;
    - логирования;
    - выбора стратегии (например, разные ограничения по каналам).

### 3.3. Обработчики инструментов

- Каждый `handler`:
  - вызывает **существующие доменные сервисы**:
    - BookingService, CrmService, TasksService и т.д.;
  - не содержит своей бизнес‑логики (только адаптерную);
  - следит за:
    - корректной работой с tokenization‑слоем (принимает токены, преобразует в id и обратно);
    - корректной обработкой ошибок:
      - бросает контролируемые исключения с кодами;
      - не протекает «сырой» текст ошибок от внешних AI/инфраструктуры к пользователю.

### 3.4. Логирование и метрики

- Внутри tools‑registry:
  - логируем:
    - `trace_id`, `tool_id`, `source`, `clinic_id`, `actor`, `result_status`, коды ошибок;
  - собираем метрики:
    - `ai_tool_calls_total{tool_id, source, status}`;
    - `ai_tool_call_duration_seconds{tool_id}`.

---

## 4. Архитектурный дизайн Orchestrator’а

### 4.1. Роль Orchestrator’а

- Orchestrator:
  - принимает запрос из Omnichannel/AI‑контекста (чат, команда, админский вызов);
  - формирует промпт/контекст для LLM (с учётом политики ПД и токенизации);
  - управляет циклом function‑calling:
    - предоставляет LLM список tools;
    - принимает запрос tool‑вызова;
    - валидирует и вызывает handler через tools‑registry;
    - отдаёт результат LLM;
    - повторяет цикл по необходимости;
  - возвращает финальный результат:
    - оператору/клиенту (через Omnichannel UI);
    - или backend‑слою (если это «фоновая» AI‑операция).

### 4.2. Интеграция с SafeAiClient и tokenization

- Orchestrator:
  - использует `build_safe_ai_client` / SafeAiClient по `clinic_id` (см. `ARCH_DEV_OMNI_POLICY_016.md`);
  - перед отправкой сообщений:
    - применяет tokenization‑слой для доменных идентификаторов (см. `ARCH_DEV_AI_TOKENIZATION_025.md`);
  - после получения ответа:
    - распознаёт токены;
    - мапит их обратно в доменные id;
    - не позволяет «голым» ПД из ответа проходить дальше при `allow_personal_data=False`.

### 4.3. Безопасность и ограничения

- Orchestrator:
  - получает `AiToolContext` с уже проверенными пермишенами (или сам вызывает RBAC‑проверки до tools‑registry);
  - фильтрует список tools, видимый LLM:
    - по ролям/пермишенам/каналу/типу пользователя;
  - не даёт LLM вызывать:
    - инструменты, не зарегистрированные в реестре;
    - инструменты, которые не доступны в данном контексте.

---

## 5. Dev‑чек‑лист для DEV_PROMPT_OMNI_REGISTRY_015

### 5.1. Аналитика

1. Найти все текущие места, где:
   - AI‑уровень вызывает доменные сервисы напрямую (Booking, CRM, Tasks и др.);
   - Orchestrator (или аналоги) уже реализуют function‑calling, но без реестра.
2. Сопоставить их с GAPS:
   - `BACKEND_GAPS_Omnichannel_NEXT.md` (OMNI‑1, OMNI‑3);
   - `NONFUNCTIONAL_AUDIT_NEXT.md` (OBS‑2 и связанные пункты).

### 5.2. Введение tools‑registry

3. Создать модуль `ai/tools_registry.py` (или эквивалент).
4. Описать:
   - интерфейс `AiTool`;
   - `AiToolContext`;
   - реестр `TOOLS_REGISTRY` с API для получения/списка инструментов.
5. Реализовать минимальный набор инструментов vNext:
   - по Booking (слоты, создание/отмена);
   - по CRM (создание лида, движение стадий);
   - по Tasks/Attention (создание задач по контексту).

### 5.3. Интеграция Orchestrator’а

6. Обновить `OmnichannelAiOrchestrator`:
   - чтобы он:
     - формировал `AiToolContext`;
     - использовал `TOOLS_REGISTRY` для выдачи списка tools;
     - вызывал handlers по id;
     - логировал/собирал метрики вокруг вызовов.
7. Убедиться, что:
   - все вызовы внешнего AI идут через SafeAiClient/AiSanitizer;
   - используется tokenization‑слой для идентификаторов.

### 5.4. RBAC и ограничения

8. Для каждого инструмента:
   - задать `required_permissions`/`allowed_roles`;
   - реализовать проверку в `AiToolContext`/handler;
   - убедиться, что AI не может выполнить операцию, недоступную человеку с аналогичными правами.

### 5.5. Наблюдаемость и тесты

9. Добавить:
   - структурированные логи вызовов инструментов;
   - метрики по количеству и времени работы tools.
10. Написать тесты:
    - на корректность фильтрации доступных tools по ролям/каналам;
    - на корректность работы минимального набора инструментов;
    - на отказоустойчивость (ошибка доменного сервиса не «рвёт» orchestrator, а возвращается контролируемо).

### 5.6. Документация и связь с GAPS

11. Обновить:
    - `DEV_PROMPTS_NEXT.md` (статус DEV_PROMPT_OMNI_REGISTRY_015);
    - `BACKEND_GAPS_Omnichannel_NEXT.md` и `NONFUNCTIONAL_AUDIT_NEXT.md` — отметить закрытые/переформулированные GAPS.

---

## 6. Связь с другими DEV_PROMPTS

- После реализации DEV_PROMPT_OMNI_REGISTRY_015:
  - DEV_PROMPT_BKG_AI_TOOLS_006, DEV_PROMPT_CRM_AI_009, DEV_PROMPT_TASKS_AI_021 получают опору в виде единого tools‑registry;
  - DEV_PROMPT_OMNI_POLICY_016 и DEV_PROMPT_AI_TOKENIZATION_025 работают поверх чётко структурированного AI‑слоя;
  - Tasks & Attention (DEV_PROMPT_TASKS_MODEL_020, DEV_PROMPT_TASKS_AI_021) могут уверенно использовать события и метрики tools‑registry для генерации и трекинга задач;
  - Security & Observability (DEV_PROMPT_SEC_RBAC_022, DEV_PROMPT_OBS_CHAINS_023, DEV_PROMPT_PERF_SPOTS_024) получают единое место для контроля доступа, логов и перфоманса AI‑инструментов.

