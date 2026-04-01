## ARCH_DEV_OMNI_UI_017_TASKS — сверх‑детализированные dev‑таски

> Связанная архитектура: `ARCH_DEV_OMNI_UI_017.md`  
> Связанный DEV_PROMPT: `DEV_PROMPT_OMNI_UI_017` (P1, FO‑1/3, FADM‑4)

---

### 1. Understand — текущее состояние Omnichannel & AI‑UI

1.1. **Инвентаризация Omnichannel‑страниц и компонентов фронта.**  
1.1.1. Найти и просмотреть ключевые Omnichannel‑экраны/admin‑страницы:  
       - `AdminOmniChatPage.tsx` (основной чат);  
       - `AdminOmniChannelsPage.tsx` (список каналов/диалогов);  
       - `AdminOmniAiSettingsPage.tsx` (если есть отдельный экран настроек AI);  
       - Spotlight/`useAiAgent`, компоненты панели AI‑агента/Spotlight.  
1.1.2. Для каждого экрана зафиксировать:  
       - какие AI‑элементы уже отображаются (кнопки, панели, бейджи);  
       - какие контекстные блоки по CRM/Booking/Tasks присутствуют или отсутствуют.

1.2. **Инвентаризация AI‑статусов и feature‑флагов в UI.**  
1.2.1. Найти в фронтовом коде:  
       - любой конфиг/enum статусов AI‑функций (`stub/beta/prod` или аналоги);  
       - привязку UI‑элементов к этим статусам (бейджи, tooltips, disabled‑состояния);  
       - использование `ClinicAiSettings` или эндпоинтов настроек AI для управления UI.  
1.2.2. Зафиксировать, какие AI‑фичи сейчас выглядят как «production», но по факту являются stub/демо.

1.3. **Инвентаризация связки Omnichannel ↔ CRM/Booking/Tasks в UI.**  
1.3.1. В `AdminOmniChatPage` и смежных компонентах проверить:  
       - есть ли контекстная панель с информацией по контакту/лиду/пациенту;  
       - есть ли быстрые действия: «Открыть/создать лид», «Открыть расписание/запись», «Создать задачу»;  
       - как отображаются и используются Tasks/Attention, связанные с текущим диалогом.  
1.3.2. Сопоставить это с ожиданиями из `ARCH_OMNICHANNEL_NEXT.md` и `FRONTEND_GAPS_Omnichannel_NEXT.md` (FO‑1/2/3).

1.4. **Сопоставление с GAPS и ARCH_DEV.**  
1.4.1. Пройти по:  
       - `FRONTEND_GAPS_Omnichannel_NEXT.md` (FO‑1/2/3);  
       - `FRONTEND_GAPS_Admin_NEXT.md` (FADM‑4);  
       - `ARCH_DEV_OMNI_POLICY_016.md` (политика AI/ПД);  
       - `ARCH_DEV_OMNI_REGISTRY_015.md` (tools‑registry/Orchestrator);  
       - `ARCH_DEV_TASKS_MODEL_020.md`, `ARCH_DEV_TASKS_AI_021.md` (Tasks & Attention).  
1.4.2. Пометить, какие конкретные UI‑GAPS должны быть закрыты в рамках `DEV_PROMPT_OMNI_UI_017`, а какие относятся к backend/AI‑политике/registry и не дублировать их.

---

### 2. Design‑to‑code — модель статусов AI‑функций и UX‑паттерны Omnichannel

2.1. **Спроектировать модель `AiFeatureConfig` для фронта.**  
2.1.1. На основе `ARCH_DEV_OMNI_UI_017.md` описать типы:  
       - `AiFeatureStatus = "stub" | "beta" | "prod"`;  
       - `AiFeatureConfig { id, label, status, description? }`.  
2.1.2. Определить список AI‑фич для v1 (минимум):  
       - `omni.spotlight.agent`;  
       - `omni.tools.suggest_slots`;  
       - `omni.tools.crm_suggest_next_stage`;  
       - `omni.tools.create_task`.  
2.1.3. Спроектировать, откуда фронт получает конфиг:  
       - статичный объект на фронте на первые итерации;  
       - или endpoint `GET /admin/omni/ai-features` с `AiFeatureConfig[]` по клинике.

2.2. **Спроектировать UX‑поведение Spotlight/AI‑агента по статусам.**  
2.2.1. Для `useAiAgent`/Spotlight описать:  
       - режим `stub`:  
         - явный текст «Функция в разработке / демо»;  
         - возможен демонстрационный ответ, но без реальных действий в доменах;  
         - disabled для доменных кнопок/интеграций;  
       - режим `beta`:  
         - реальный вызов Orchestrator/tools;  
         - бейдж `beta` + tooltip с ограничениями;  
       - режим `prod`:  
         - без дополнительных предупреждений, но с сохранением трассировки действий.  
2.2.2. Зафиксировать эти правила в описании hook’а/компонента, чтобы реализация была однозначной.

2.3. **Спроектировать UX контекстной панели Omnichannel.**  
2.3.1. На уровне дизайна UI описать структуру контекстной панели:  
       - блок контакта (имя/токен, телефон/обезличенный маркер, клиника);  
       - блок CRM: активный/последние `LeadCard` с основными полями;  
       - блок Booking: ближайшие/последние `Booking`;  
       - блок Tasks/Attention: открытые задачи/сигналы по этому пациенту/лиду.  
2.3.2. Спроектировать «быстрые действия» с панели:  
       - открыть/создать лид;  
       - открыть расписание/запись;  
       - создать задачу (с предзаполненным контекстом).

2.4. **Спроектировать точки интеграции с tools‑registry и RBAC.**  
2.4.1. Описать, как UI должен:  
       - запрашивать список доступных tools (`GET /admin/omni/available-tools` или аналогичный endpoint);  
       - пересекать `AiFeatureConfig` и доступные tools/пермишены пользователя;  
       - включать/отключать AI‑кнопки в зависимости от доступности инструмента и статуса фичи.  
2.4.2. Зафиксировать поведение при недоступности backend‑tool’а:  
       - UI показывает, что фича временно недоступна, а не ведёт себя как рабочая.

---

### 3. Implement — фронтовая модель статусов и Spotlight/AI‑agent

3.1. **Ввести/обновить модуль `AiFeatureConfig` и хук доступа.**  
3.1.1. Создать (или дооформить) общий модуль, например `frontend/src/shared/aiFeatures.ts`, содержащий:  
       - типы `AiFeatureStatus`, `AiFeatureConfig`;  
       - дефолтный словарь конфигураций на случай, если backend‑endpoint недоступен;  
       - хук `useAiFeatures(clinicId)` для получения актуальной конфигурации (с запросом к backend при наличии эндпоинта).  
3.1.2. Обеспечить кэширование/мемоизацию конфигурации по клинике, чтобы не перегружать backend запросами.

3.2. **Обновить Spotlight/`useAiAgent` под статусы фич.**  
3.2.1. В `useAiAgent` внедрить использование `AiFeatureConfig` для `omni.spotlight.agent`:  
       - в `stub`‑режиме:  
         - не вызывать Orchestrator/tools;  
         - отдавать предсказуемые демо‑ответы и явные подсказки о статусе;  
       - в `beta/prod`‑режимах:  
         - использовать реальный Orchestrator и tools‑registry;  
         - показывать бейдж `beta` в UI, если применимо.  
3.2.2. Обновить UI Spotlight/AI‑панели:  
       - добавить визуальные бейджи статуса (цветовая схема/label);  
       - добавить tooltips с описанием: что умеет AI в текущем режиме, а что нет.

3.3. **Применить статусы к AI‑кнопкам в Omnichannel и CRM‑UI.**  
3.3.1. Для AI‑кнопок в Omnichannel (предложение слотов, CRM‑AI‑действия и т.п.):  
       - обернуть отображение/доступность в проверку `AiFeatureConfig` + доступных tools;  
       - для `stub`‑тех фичей:  
         - показывать их как выключенные/демо, либо скрывать, но с явным объяснением на уровне страницы.  
3.3.2. В CRM‑Kanban/карточке лида, где появляются AI‑кнопки (например, «AI‑рекомендация стадии»):  
       - также использовать `AiFeatureConfig` и отображать `beta`/`stub`‑лейблы в соответствии с архитектурными требованиями.

---

### 4. Implement — усиление Omnichannel‑контекста и быстрых действий

4.1. **Реализовать/усилить контекстную панель в `AdminOmniChatPage`.**  
4.1.1. Добавить или дооформить компонент контекстной панели (sidebar) cо структурой из раздела 2.3:  
       - контакт (обезличенные данные + клиника);  
       - CRM‑блок (связанные лиды/воронка);  
       - Booking‑блок (записи/история визитов);  
       - Tasks/Attention‑блок (открытые задачи/сигналы).  
4.1.2. Обеспечить загрузку этих данных через соответствующие backend‑API (CRM/Booking/Tasks), не дублируя бизнес‑логику.

4.2. **Добавить быстрые действия из Omnichannel в CRM/Booking/Tasks.**  
4.2.1. В контекстной панели реализовать кнопки:  
       - «Открыть/создать лид» → переход к CRM‑странице/модалке с привязкой к текущему контакту;  
       - «Открыть расписание/запись» → переход на admin schedule/booking с предзаполненным фильтром по пациенту/клинике;  
       - «Создать задачу» → модалка создания Task с автоматическим заполнением контекста Omnichannel.  
4.2.2. Убедиться, что вызовы соответствуют контрактам `ARCH_DEV_CRM_EVENTS_007`, `ARCH_DEV_BKG_CORE_001`, `ARCH_DEV_TASKS_MODEL_020` (не обходят доменные сервисы).

4.3. **Интегрировать AI‑рекомендации в Omnichannel UI.**  
4.3.1. Если уже реализованы CRM‑AI‑tools (`DEV_PROMPT_CRM_AI_009`) и AI Task Manager (`DEV_PROMPT_TASKS_AI_021`):  
       - добавить раздел «AI‑рекомендации» в Omnichannel‑панели:  
         - предложения по следующему действию (смена стадии лида, создание задачи, приглашение на запись);  
         - кнопки для принятия/отклонения рекомендаций.  
4.3.2. Обеспечить, чтобы принятие рекомендаций вызывало соответствующие tools/эндпоинты (CRM‑AI‑tools, Task‑создание), а не произвольные изменения данных.

---

### 5. Observe — логирование Omnichannel‑UI и UX‑инварианты

5.1. **Логирование кликов по AI‑элементам UI.**  
5.1.1. В фронте (через систему event‑логов/telemetry) добавить события:  
       - клики по AI‑кнопкам (Spotlight, Omnichannel, CRM‑AI‑элементы);  
       - активация/деактивация AI‑фич (по смене конфигурации);  
       - принятие/отклонение AI‑рекомендаций.  
5.1.2. Убедиться, что события содержат:  
       - `trace_id` (если есть), `clinic_id`, тип фичи (`omni.spotlight.agent`, `omni.tools.suggest_slots` и т.п.), статус (`stub/beta/prod`), но не содержат ПД.

5.2. **UX‑инварианты для AI‑UI (в духе `ROLE_QA_ARCH`).**  
5.2.1. На уровне стилей и компонентов обеспечить:  
       - консистентные состояния кнопок AI: `default/hover/active/disabled`;  
       - визуальное отличие `stub`/`beta`/`prod` (иконки/цвета/бейджи), чтобы оператор всегда понимал уровень готовности фичи.  
5.2.2. Реализовать понятные сообщения об ошибках:  
       - при сбое AI/Orchestrator’а UI не «падает», а показывает контролируемый toast/notification;  
       - пользователь понимает, что именно не сработало (без «магического» 500).

5.3. **Связь UI‑логов с backend‑OBS.**  
5.3.1. Согласовать формат event‑логов UI с OBS‑цепочками из `ARCH_DEV_OBS_CHAINS_023.md`:  
       - использовать общие `trace_id`/корреляционные идентификаторы, чтобы можно было связать UI‑события с backend‑логами/метриками AI‑слоя.  
5.3.2. При необходимости описать в `ARCH_DEV_OMNI_UI_017.md` или `ARCH_AUDIT_NEXT.md`, какие UI‑события являются ключевыми для мониторинга готовности/эффективности AI‑функций.

---

### 6. Stabilize — тесты, QA‑чеклисты и синхронизация артефактов

6.1. **Покрытие Omnichannel/AI‑UI тестами.**  
6.1.1. Добавить/обновить тесты (unit/компонентные/интеграционные) для:  
       - `useAiAgent` и AI‑панели Spotlight (поведение в `stub/beta/prod`);  
       - отображения/доступности AI‑кнопок в Omnichannel/CRM‑UI в зависимости от `AiFeatureConfig` и доступных tools;  
       - контекстной панели Omnichannel (наличие данных CRM/Booking/Tasks и корректность быстрых действий).  
6.1.2. Проверить сценарии:  
       - многоклиничный контекст (если применимо) — корректная работа AI‑UI при смене клиники;  
       - временная недоступность backend‑endpoint’ов (fallback к статичным конфигам/корректным сообщениям).

6.2. **QA‑чеклист для FO‑1/2/3, FADM‑4.**  
6.2.1. На основе `ROLE_QA_ARCH.md` и `FRONTEND_GAPS_*_NEXT.md` сформировать внутренний QA‑чеклист (можно прямо в коде/доках):  
       - для FO‑1:  
         - все места, где AI‑функция фактически stub, помечены как таковые;  
       - для FO‑2/3:  
         - связка Omnichannel ↔ CRM/Booking/Tasks покрыта контекстной панелью и быстрыми действиями;  
       - для FADM‑4:  
         - Omnichannel воспринимается как рабочий центр (доступны основные действия без прыжков по всему приложению).  
6.2.2. Договориться с QA/ARCH, какие тест‑кейсы считать блокирующими для выкатки Omni‑UI‑изменений.

6.3. **Синхронизация документации и GAPS.**  
6.3.1. После завершения реализации обновить:  
       - `DEV_PROMPTS_NEXT.md` — статус `DEV_PROMPT_OMNI_UI_017`;  
       - `FRONTEND_GAPS_Omnichannel_NEXT.md` (FO‑1/2/3) и `FRONTEND_GAPS_Admin_NEXT.md` (FADM‑4) — отметить закрытые/уточнённые пункты;  
       - при необходимости `ARCH_AUDIT_NEXT.md` — описать принятые UX‑инварианты для AI‑UI.  
6.3.2. Зафиксировать в `ARCH_DEV_COVERAGE_NEXT.md`, что для `OMNI_UI_017` существует и поддерживается `ARCH_DEV_OMNI_UI_017_TASKS.md` с полным циклом 1–6.

---

### Выполнено (в коде, 2026‑03)

**Фронт: модель AI‑статусов и применение к UI**
- Добавлен модуль фич и статусов: `frontend/src/shared/aiFeatures.ts`:
  - `AiFeatureStatus = "stub" | "beta" | "prod"`
  - дефолтные конфиги фич v1: `omni.spotlight.agent`, `omni.tools.suggest_slots`, `omni.tools.crm_suggest_next_stage`, `omni.tools.create_task`
  - хук `useAiFeatures(clinicId)` (memo + fallback) с мягкой привязкой к `GET /v1/admin/ai-status`
- `useAiAgent` переведён на статусы:
  - в `stub` режиме **нет network вызовов**, возвращается предсказуемый демо‑ответ
  - в `beta/prod` вызывается `/v1/ai/agent`
  - файл: `frontend/src/hooks/useAiAgent.ts`
- Статусы (`stub/beta/prod`) и tooltips/disabled применены к AI‑элементам:
  - Spotlight “Спросить AI”: `frontend/src/admin/layouts/AdminLayout.tsx`
  - OmniChat AI‑блок и кнопки: `frontend/src/admin/pages/AdminOmniChatPage.tsx`
  - CRM AI‑блоки в воронке продаж: `frontend/src/admin/pages/AdminSalesPipelinePage.tsx`

**Backend: tools‑registry intersection (available‑tools)**
- Добавлен endpoint доступных tools для UI: `GET /v1/admin/omni/available-tools`
  - RBAC: `require_permissions("view_dashboard")`
  - источником правды является `src/application/ai/tools_registry.list_tools_for_context(...)` (учёт `allowed_roles` / `required_permissions`)
  - файлы:
    - `src/api/v1/routers/admin_omni_tools.py`
    - подключение: `src/api/v1/router.py`
- Фронт‑хук для available tools:
  - `frontend/src/hooks/useAvailableAiTools.ts` (react‑query + `hasAll([...toolIds])`)
- В UI сделано пересечение `AiFeatureConfig ∩ availableTools`:
  - CRM/Omni AI‑кнопки отключаются не только по `stub`, но и если backend tool недоступен/нет прав
  - файлы: `AdminOmniChatPage.tsx`, `AdminSalesPipelinePage.tsx`

**Telemetry UI‑событий (без ПД)**
- Добавлен backend endpoint: `POST /v1/admin/ui-events` (логирование в backend‑логи; без ПД)
  - файл: `src/api/v1/routers/admin_ui_events.py`
  - подключение: `src/api/v1/router.py`
- Добавлен фронтовый транспорт: `frontend/src/shared/uiEvents.ts` (`logUiEvent`, ошибки игнорируются)
- Подключены события для ключевых AI‑кликов (Spotlight/Omni/CRM).

**Тесты (vitest)**
- Обновлён тест страницы воронки продаж под новые хуки:
  - `frontend/src/admin/pages/__tests__/AdminSalesPipelinePage.test.tsx`
- Добавлен unit‑тест `useAiAgent` на ветки `stub` (без network) и `beta` (с network):
  - `frontend/src/hooks/__tests__/useAiAgent.test.ts`

---

### На потом (улучшения / следующий пакет)

1) **Контекстная панель Omnichannel “как рабочий центр” (FO‑2/3, FADM‑4)**  
   Довести `AdminOmniChatPage` до структуры 2.3:
   - CRM‑блок (связанные лиды/стадии/быстрые действия)
   - Booking‑блок (ближайшие/последние записи)
   - Tasks/Attention‑блок (задачи/сигналы по текущему пациенту/лиду)

2) **Единый UI‑компонент статуса фичи**  
   Вынести повторяющуюся логику бейджа/tooltip в `AiFeatureBadge` (единые цвета/тексты).

3) **Единый “effective AI availability” слой**  
   Сейчас availability проверяется локально в местах использования; можно сделать общий helper:
   - `isFeatureEnabled(featureId, requiredTools[])`
   - единая причина/код недоступности (stub vs no-permission vs tool-missing vs backend-down).

4) **Тесты Omnichannel страницы**  
   Добавить тесты на `AdminOmniChatPage`: disabled/tooltip при недоступных tools, отсутствие вызовов в `stub`.

5) **Систематизация telemetry ↔ OBS**  
   Согласовать словарь `event_name`/`meta` и связку `trace_id` с цепочками OBS (см. `ARCH_DEV_OBS_CHAINS_023.md`).

6) **UI‑ошибки: централизованный toast/notification**  
   Добавить единый механизм показов ошибок AI/Orchestrator (без “магических 500”), с graceful fallback.

