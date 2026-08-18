## DEV_EXECUTION_TRACKER_NEXT — пофазная реализация DEV_PROMPTS

> **Цель:** дать ролям `@DEV` и `@LEAD` один файл, который можно целиком класть в контекст и просить:  
> «выполни фазу N для DEV_PROMPT_xxx», отмечая прогресс по единым стадиям 1–6 из `./ARCH_DEV_COVERAGE_NEXT.md`.

---

## 0. Как этим пользоваться (контракт для роли `@DEV`)

- **Источник порядка:** использовать зависимости и приоритеты из `DEV_PROMPTS_NEXT.md` (раздел 3, строки 293–319).  
  Сначала блок 1 (P0), затем 2, 3, …, 8.
- **Контракт по эскалации к `@LEAD`:** когда менять архитектуру/контракты, а когда действовать самостоятельно, описано в `DEV_WORKFLOW_GUIDE_NEXT.md`.
- **Фазы для каждого `DEV_PROMPT_xxx`:**
  1. Understand  
  2. Design‑to‑code  
  3. Implement  
  4. Integrate  
  5. Observe  
  6. Stabilize
- **Вход в работу по фазе:**
  - в контекст агенту `@DEV` кладём:
    - этот файл `DEV_EXECUTION_TRACKER_NEXT.md`,
    - соответствующие `ARCH_DEV_xxx.md` и `ARCH_DEV_<ID>_TASKS.md`,
    - при необходимости — куски кода;
  - формулируем задачу в виде (пример):
    - «Выполни **фазу 2. Design‑to‑code** для `DEV_PROMPT_OMNI_POLICY_016`  
      строго по `ARCH_DEV_OMNI_POLICY_016.md` и `ARCH_DEV_OMNI_POLICY_016_TASKS.md`.  
      Оставайся в границах фазы 2 (DTO/сигнатуры/enum и пр.), но **предлагай лучшие варианты внутри этих рамок** — `@LEAD` выберет финальное решение при ревью.»
- **Ожидаемый результат от каждой фазы:**
  - **1. Understand:** прочитаны все связанные ARCH/GAPS, зафиксирован локальный план в `*_TASKS`, код не менялся или только минорные комментарии/фиксы;
  - **2. Design‑to‑code:** добавлены/обновлены DTO, сигнатуры сервисов, enum/словари, но без полной бизнес‑логики и без агрессивных миграций;
  - **3. Implement:** реализована доменная логика и тесты на инварианты;
  - **4. Integrate:** обновлены публичные API/роутеры/контракты фронта, соблюдена обратная совместимость где возможно;
  - **5. Observe:** добавлены логи/метрики/Attention/Tasks в нужных точках;
  - **6. Stabilize:** долги/временные обходы закрыты, статусы в DEV_PROMPTS/GAPS/ARCH‑артефактах синхронизированы.
- **Обновление чекбоксов:**  
  - чекбоксы в этом файле можно обновлять либо руками (`@LEAD`), либо отдельным вызовом агента, который правит только этот файл.
- **Источник правды закрытия пакета (фазы 1–6):** для каждого `DEV_PROMPT_*` с отмеченными `[x]` детальный факт «что сдано» смотреть в парном файле `./ARCH_DEV_<ID>_TASKS.md` — раздел **«Выполнено»**, итог **Stabilize** или финальный чеклист в конце документа (формулировка зависит от пакета). Этот трекер — пофазный снимок по решению `@LEAD`, без дублирования полного содержания TASKS.
- **@QA_ARCH (согласовано с `ARCH_DEV_CRM_EVENTS_007_TASKS`):** пакеты **до** `DEV_PROMPT_CRM_EVENTS_007` в трекере отмечены как завершённые по фазам 1–6 по заявке `@LEAD` (наличие кода и интеграций в репозитории). Для **`DEV_PROMPT_CRM_EVENTS_007`** галочки в трекере **намеренно не ставятся** — факт выполнения v1 смотреть только в разделе «Выполнено» файла `ARCH_DEV_CRM_EVENTS_007_TASKS.md`; пакеты **после** него в трекере остаются неотмеченными, пока `@LEAD` их не закроет.

---

## 1. Базовая безопасность и политика AI (P0)

### DEV_PROMPT_OMNI_POLICY_016 (P0) — AiSanitizer + провайдеры
- ARCH_DEV: `ARCH_DEV_OMNI_POLICY_016.md`
- TASKS: `ARCH_DEV_OMNI_POLICY_016_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_SEC_RBAC_022 (P0) — RBAC
- ARCH_DEV: `ARCH_DEV_SEC_RBAC_022.md`
- TASKS: `ARCH_DEV_SEC_RBAC_022_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

---

## 2. ERP‑узел и завершение визита (P0–P1)

### DEV_PROMPT_BKG_CORE_001 (P0) — фасад завершения визита
- ARCH_DEV: `ARCH_DEV_BKG_CORE_001.md`
- TASKS: `ARCH_DEV_BKG_CORE_001_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_ERP_NODE_010 (P0) — ERP‑узел
- ARCH_DEV: `ARCH_DEV_ERP_NODE_010.md`
- TASKS: `ARCH_DEV_ERP_NODE_010_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_ERP_LOYALTY_011 (P1) — ERP ↔ Loyalty
- ARCH_DEV: `ARCH_DEV_ERP_LOYALTY_011.md`
- TASKS: `ARCH_DEV_ERP_LOYALTY_011_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_ERP_REPORTS_012 (P2) — ERP‑отчётность
- ARCH_DEV: `ARCH_DEV_ERP_REPORTS_012.md`
- TASKS: `ARCH_DEV_ERP_REPORTS_012_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

---

## 3. Нормализация статусов и UX‑словари (P1)

### DEV_PROMPT_BKG_STATE_002 (P1) — статусы Booking
- ARCH_DEV: `ARCH_DEV_BKG_STATE_002.md`
- TASKS: `ARCH_DEV_BKG_STATE_002_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

---

## 4. Наблюдаемость и критичные цепочки (P1)

### DEV_PROMPT_OBS_CHAINS_023 (P1) — OBS‑цепочки
- ARCH_DEV: `ARCH_DEV_OBS_CHAINS_023.md`
- TASKS: `ARCH_DEV_OBS_CHAINS_023_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_BKG_ERRORS_005 (P1) — ошибки записи/платежей
- ARCH_DEV: `ARCH_DEV_BKG_ERRORS_005.md`
- TASKS: `ARCH_DEV_BKG_ERRORS_005_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_TASKS_MODEL_020 (P1) — Tasks ↔ Attention
- ARCH_DEV: `ARCH_DEV_TASKS_MODEL_020.md`
- TASKS: `ARCH_DEV_TASKS_MODEL_020_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

---

## 5. Omnichannel & AI‑слой (P1–P2)

### DEV_PROMPT_OMNI_REGISTRY_015 (P1) — tools‑registry и Orchestrator
- ARCH_DEV: `ARCH_DEV_OMNI_REGISTRY_015.md`
- TASKS: `ARCH_DEV_OMNI_REGISTRY_015_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_AI_TOKENIZATION_025 (P1) — tokenization‑слой
- ARCH_DEV: `ARCH_DEV_AI_TOKENIZATION_025.md`
- TASKS: `ARCH_DEV_AI_TOKENIZATION_025_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_BKG_AI_TOOLS_006 (P2) — AI‑tools для Booking/Schedule
- ARCH_DEV: `ARCH_DEV_BKG_AI_TOOLS_006.md`
- TASKS: `ARCH_DEV_BKG_AI_TOOLS_006_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_CRM_AI_009 (P2) — AI в CRM
- ARCH_DEV: `ARCH_DEV_CRM_AI_009.md`
- TASKS: `ARCH_DEV_CRM_AI_009_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_TASKS_AI_021 (P2) — AI Task Manager
- ARCH_DEV: `ARCH_DEV_TASKS_AI_021.md`
- TASKS: `ARCH_DEV_TASKS_AI_021_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

### DEV_PROMPT_OMNI_UI_017 (P1) — UX Omnichannel/AI
- ARCH_DEV: `ARCH_DEV_OMNI_UI_017.md`
- TASKS: `ARCH_DEV_OMNI_UI_017_TASKS.md`
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

---

## 6. CRM & Attribution (P1–P2)

### DEV_PROMPT_CRM_EVENTS_007 (P1) — автодвижение лидов
- ARCH_DEV: `ARCH_DEV_CRM_EVENTS_007.md`
- TASKS: `ARCH_DEV_CRM_EVENTS_007_TASKS.md`
- **Статус (@QA_ARCH / согласовано с `@LEAD`):** факт реализации v1 и оставшаяся работа описаны **только** в `ARCH_DEV_CRM_EVENTS_007_TASKS.md` («Выполнено», «На потом»); **фазы 1–6 в этом трекере намеренно без галочек**, чтобы не дублировать TASKS-файл.
- Фазы:
  - [ ] 1. Understand
  - [ ] 2. Design‑to‑code
  - [ ] 3. Implement
  - [ ] 4. Integrate
  - [ ] 5. Observe
  - [ ] 6. Stabilize

### DEV_PROMPT_CRM_MONEY_008 (P1) — деньги в CRM
- ARCH_DEV: `ARCH_DEV_CRM_MONEY_008.md`
- TASKS: `ARCH_DEV_CRM_MONEY_008_TASKS.md`
- **Статус (@QA_ARCH):** v1 в коде и документации GAPS/DEV_PROMPTS; детальный чек‑лист и «на потом» — в `ARCH_DEV_CRM_MONEY_008_TASKS.md` (в т.ч. раздел «Предложения на потом»).
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [x] 5. Observe
  - [x] 6. Stabilize

---

## 7. Loyalty, Paperless, Tasks (P2+)

### DEV_PROMPT_LOY_FAMILY_013 (P2) — FamilyLink и шэринг
- ARCH_DEV: `ARCH_DEV_LOY_FAMILY_013.md`
- TASKS: `ARCH_DEV_LOY_FAMILY_013_TASKS.md`
- **Статус (@QA_ARCH / 2026‑03):** в коде сдано **ядро backend v1** (см. **`ARCH_DEV_LOY_FAMILY_013.md`** §«Статус реализации», **`ARCH_DEV_LOY_FAMILY_013_TASKS.md`** — **«Выполнено»**). Фазы **1** (письменная инвентаризация в отдельных GAPS/UX‑артефактах), **4** (UI/Omni/AI), **6** (полная стабилизация: e2e‑тесты цепочки, синхронизация `DEV_PROMPTS`/`UX_FLOWS`) — **открыты**; хвосты и рубрика **«На потом»** — в TASKS.
- Фазы:
  - [ ] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [ ] 4. Integrate
  - [x] 5. Observe
  - [ ] 6. Stabilize

### DEV_PROMPT_LOY_AI_014 (P3) — AI‑кампании лояльности
- ARCH_DEV: `ARCH_DEV_LOY_AI_014.md`
- TASKS: `ARCH_DEV_LOY_AI_014_TASKS.md`
- Фазы (@QA_ARCH / 2026‑03, MVP rules без LLM):
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement (частично: без AI/Omni/FamilyLink‑владельца)
  - [~] 4. Integrate (UI лояльности + Tasks; Omni/AI — нет)
  - [x] 5. Observe (логи/метрики/Celery)
  - [~] 6. Stabilize (тесты ограничены; CI БД — на потом)

### DEV_PROMPT_PPR_MODEL_018 (P2) — модели форм/связей
- ARCH_DEV: `ARCH_DEV_PPR_MODEL_018.md`
- TASKS: `ARCH_DEV_PPR_MODEL_018_TASKS.md`
- **Статус (@QA_ARCH / 2026‑03‑20):** в коде сдана **v1 PPR‑2** (статусы, миграция `h4i5j6k7l8m9`, гейт в `BookingCompletionService`, SAVEPOINT loyalty+ERP+`completed`, админка/типы). Детали — **`ARCH_DEV_PPR_MODEL_018.md`** (§статус, §8 сводка), **`ARCH_DEV_PPR_MODEL_018_TASKS.md`** — **«Выполнено»** и **«На потом»**. Полное закрытие фаз Observe/Stabilize и обновление `DEV_PROMPTS_NEXT.md`/GAPS — по TASKS.
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement (v1: модели, сервисы, миграции, тесты)
  - [x] 4. Integrate (гейт завершения визита, API/админка v1)
  - [~] 5. Observe (логи/часть метрик; дашборд покрытия визитов — в «На потом»)
  - [~] 6. Stabilize (pytest зависит от миграций на тестовой БД; CI stamp — в «На потом»)

### DEV_PROMPT_PPR_ESIGN_019 (P3) — e‑signature пакет
- ARCH_DEV: `ARCH_DEV_PPR_ESIGN_019.md`
- TASKS: `ARCH_DEV_PPR_ESIGN_019_TASKS.md`
- Фазы:
  - [ ] 1. Understand
  - [ ] 2. Design‑to‑code
  - [ ] 3. Implement
  - [ ] 4. Integrate
  - [ ] 5. Observe
  - [ ] 6. Stabilize

---

## 8. Booking / Prepayment / Payments — прочие узлы

### DEV_PROMPT_BKG_MULTI_003 (P1) — multi‑clinic‑логика
- ARCH_DEV: `ARCH_DEV_BKG_MULTI_003.md`
- TASKS: `ARCH_DEV_BKG_MULTI_003_TASKS.md` (в конце — **«На потом»** @QA_ARCH)
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [~] 5. Observe (метрики/Task по mismatch; полные логи/фронт‑events — в TASKS «На потом»)
  - [~] 6. Stabilize (API‑тесты + `QA_CHECKLIST_BKG_MULTI.md`; автотесты PWA — в «На потом»)

### DEV_PROMPT_BKG_WAITLIST_004 (P2) — waitlist
- ARCH_DEV: `ARCH_DEV_BKG_WAITLIST_004.md`
- TASKS: `ARCH_DEV_BKG_WAITLIST_004_TASKS.md` (в конце — **«Выполнено»** / **«На потом»** @QA_ARCH)
- Фазы:
  - [x] 1. Understand
  - [x] 2. Design‑to‑code
  - [x] 3. Implement
  - [x] 4. Integrate
  - [~] 5. Observe (счётчики + логи; гистограммы/Attention/Task — в TASKS «На потом»)
  - [~] 6. Stabilize (миграция + unit; E2E/CI, синхронизация UX‑GAPS — в TASKS «На потом»)

---

## 9. Security & Observability — доп. задачи

### DEV_PROMPT_PERF_SPOTS_024 (P2) — перф‑оптимизации
- ARCH_DEV: `ARCH_DEV_PERF_SPOTS_024.md` (§8 — статус v1)
- TASKS: `ARCH_DEV_PERF_SPOTS_024_TASKS.md` (в конце — **«Выполнено»** / **«На потом»** @QA_ARCH)
- **Глубокий перф (Engine L2):** `ARCH_PERF_ENGINE_L2_DEEP_2026.md` (предагрегаты ERP, Celery, virtual, курсор Kanban)
- **Витрины ERP payroll / materials / ROI (эпик 026):** `ARCH_DEV_ERP_VITRINES_026.md`, `ARCH_DEV_ERP_VITRINES_026_TASKS.md`
- **Статус (@QA_ARCH / 2026-03-20):** эпик **026** и расширение L2 по витринам — **в коде**; **`NONFUNCTIONAL_AUDIT_NEXT.md`** §5; полный статус — **`ARCH_DEV_ERP_VITRINES_026.md`** (§статус), **`ARCH_PERF_ENGINE_L2_DEEP_2026.md`** §6.
- Фазы:
  - [~] 1. Understand (частично: зоны риска закрыты точечным кодом; полный baseline — в TASKS «На потом»)
  - [~] 2. Design‑to‑code (частично; L2 — в `ARCH_PERF_ENGINE_L2_DEEP_2026.md`)
  - [x] 3. Implement (v1: CRM kanban projection, один SQL list+total, лимит периода отчётов, HTTP metrics)
  - [x] 4. Integrate (API+фронт projection, Alert при усечённой выборке)
  - [~] 5. Observe (HTTP + CRM counter; baseline до/после, связка с `business_chain_*` — в TASKS «На потом»)
  - [~] 6. Stabilize (нагрузочные тесты, GAPS, алерты под `status_class` — в TASKS «На потом»)

---

## 10. Журнал согласованных правок (документ)

- **2026-03-20 (@QA_ARCH / @DEV):** в §0 добавлен контракт **«источник правды закрытия пакета»** (детали сдачи — в парном `./ARCH_DEV_<ID>_TASKS.md`); в цитате про фазы 1–6 указан полный путь к `./ARCH_DEV_COVERAGE_NEXT.md`. Митигация выборочного аудита: [`QA_ARCH_AUDIT_ARCH_AND_CODE_PRE_007_50PCT.md`](./QA_ARCH_AUDIT_ARCH_AND_CODE_PRE_007_50PCT.md); изоляция ошибок в `EventBus` и метрика `domain_event_handler_failures_total` — см. `ARCH_AUDIT_NEXT.md` §4.
- **2026-03-20 (@QA_ARCH):** пакет **`DEV_PROMPT_LOY_FAMILY_013`**: зафиксирована реализация v1 в **`ARCH_DEV_LOY_FAMILY_013.md`**, детальные **«Выполнено»** / **«На потом»** — в **`ARCH_DEV_LOY_FAMILY_013_TASKS.md`**; обновлены **`BACKEND_GAPS_Loyalty_NEXT.md`** (LOY‑1), фазы в §7 этого файла. Полное закрытие фаз 1/4/6 — по TASKS.
- **2026-03-20 (@QA_ARCH):** пакет **`DEV_PROMPT_PPR_MODEL_018`**: зафиксирована **v1 PPR‑2** в **`ARCH_DEV_PPR_MODEL_018.md`**, **«Выполнено»** / **«На потом»** — в **`ARCH_DEV_PPR_MODEL_018_TASKS.md`**; обновлены §7 этого файла и **`BACKEND_GAPS_Paperless_NEXT.md`** §5. Полное закрытие фаз 5–6 и синхронизация `DEV_PROMPTS_NEXT.md` — по TASKS.
- **2026-03-20 (@QA_ARCH / @DEV):** пакет **`DEV_PROMPT_BKG_MULTI_003`**: **v1 core** — блок **«Статус реализации»** в **`ARCH_DEV_BKG_MULTI_003.md`**, таблица фаз и **«На потом»** — в **`ARCH_DEV_BKG_MULTI_003_TASKS.md`**; ручной регресс — **`QA_CHECKLIST_BKG_MULTI.md`**; фазы 5–6 частично (см. §7 выше).
- **2026-03-20 (@QA_ARCH / @DEV):** пакет **`DEV_PROMPT_BKG_WAITLIST_004`**: **v1 core** — §8 **«Статус реализации»** в **`ARCH_DEV_BKG_WAITLIST_004.md`**, **«Выполнено»** и **«На потом»** — в **`ARCH_DEV_BKG_WAITLIST_004_TASKS.md`**; обновлены **`BACKEND_GAPS_Booking_NEXT.md`** (BKG‑4), **`DEV_PROMPTS_NEXT.md`**, §2 **`ARCH_DEV_COVERAGE_NEXT.md`**; фазы 5–6 частично (см. §8 выше).
- **2026-03-20 (@QA_ARCH):** пакет **`DEV_PROMPT_PERF_SPOTS_024`**: **v1** зафиксирован в **`ARCH_DEV_PERF_SPOTS_024.md` §8**, **«Выполнено»** / **«На потом»** — в **`ARCH_DEV_PERF_SPOTS_024_TASKS.md`**; глубокий перф вынесен в **`ARCH_PERF_ENGINE_L2_DEEP_2026.md`**; §9 этого файла обновлён (фазы 3–4 [x], остальные [~]).
- **2026-03-20 (@QA_ARCH):** эпик **`ERP_VITRINES_026`** (payroll / materials / ROI + unified `POST .../erp-aggregates/refresh`) — **в коде**; **`ARCH_DEV_ERP_VITRINES_026.md`** §статус, **`ARCH_DEV_ERP_VITRINES_026_TASKS.md`** (G1–G5 [x], **«На потом»**); **`NONFUNCTIONAL_AUDIT_NEXT.md`** §5; **`ARCH_PERF_ENGINE_L2_DEEP_2026.md`** §6 и **`ARCH_PERF_ENGINE_L2_DEEP_2026_TASKS.md`** §8.2.
- **2026-03-20 (@QA_ARCH):** **сводный бэклог** хвостов из `ARCH_DEV_*_TASKS` + L2 — **`QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md`** (полный охват 26+1 файла, секции G–K); **промпт @DEV** по волнам исполнения — **`DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md`**; ссылки в **`ARCHITECTURE_EXCELLENCE_PASSPORT.md`** §16.
- **2026-03-20 (@DEV):** **Wave 1 (Observability)** по **`DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md`**: метрика **`erp_aggregate_nightly_kind_failures_total`** (A19); шаги **`llm_first` / `llm_followup` / `llm_final` / `tool_execute`** в **`business_chain_omni_ai_step_duration_seconds`** (B2); **`prepare`** в **`business_chain_booking_erp_step_duration_seconds`**, лог **`crm_publish`** (B1); колонка **`tasks.trace_id`** + API (B4); правила **`deploy/prometheus/dental_booking_alerts.yml`**; **`NONFUNCTIONAL_AUDIT_NEXT.md`** §6 (A7, A19, A22, B5, H3); предупреждение **`crm_lead_actual_value_erp_missing_fact`** в логах (H3).
- **2026-03-20 (@DEV):** **Wave 2.1** (`QA_ARCH` **A13–A16** subset): таблица **`erp_aggregate_manual_refresh_audit`** + лог **`erp_manual_refresh_audit`**; per-kind **`erp_*_read_from_aggregate`** + **`Settings.erp_read_from_aggregate_for_kind`** (A14); тест паритета с **отрицательным** income (A16); API-тест аудита POST refresh.
- **2026-03-20 (@DEV):** **Wave 2.2** (**A15**, **A18**): **`ORDER BY`** для materials (raw + витрина) и attribution (raw, согласовано с витриной); описания **`items`** в DTO для OpenAPI; артефакт **`./ERP_VITRINES_L2_EXPLAIN_ATTRIBUTION.md`** (EXPLAIN/индексы ROI/attribution).
- **2026-03-20 (@DEV):** **Wave 2.3** (**A5**, **A6**, **A11**): таблица **`erp_aggregate_coverage_watermark`** + **`watermark_trusts_empty_range`** → **`trust_empty_if`** в **`resolve_erp_aggregate_rows`** (все четыре GET ERP); **`pg_advisory_xact_lock`** на POST refresh; **`ErpAggregateService.refresh_clinic_erp_aggregates_window`** + Celery **`erp_tasks.refresh_clinic_erp_aggregates_window`**; второй подписчик **`BOOKING_COMPLETED`** (Redis debounce, флаги **`ERP_AGGREGATE_EVENT_*`**); nightly — одна транзакция на клинику с lock.
- **2026-03-20 (@QA_ARCH):** закрытие рисков отчёта W1/W2 — **`./NONFUNCTIONAL_AUDIT_NEXT.md`** (§5–§6); **`clinic_bucket`** для цепочки Booking→ERP; **`erp_aggregate_nightly_kind_failures_total`** без `clinic_id`; **`erp_aggregate_empty_trusted_total`**; **`../../MIGRATION_UPGRADE.md`** (watermark + event env); **`./QA_ARCH_W1_W2_FOLLOWUP_PLAN_2026.md`**; обновлены **`BACKEND_GAPS_ERP_NEXT.md`**, **`ARCH_DEV_ERP_VITRINES_026_TASKS.md`** (nightly semantics).
- **2026-03-21 (@LEAD / @QA_ARCH):** **`DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG` Wave 3** — **закрыта**; решения зафиксированы в **`./LEAD_DECISIONS_QA_ARCH_WAVES.md`** (канон политики Loyalty = **`ARCH_DEV_ERP_LOYALTY_011`**, единый PR для W3 допустим, pytest/head миграций = операционный gate). Обновлены **`DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md`**, **`QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG.md`**, **`ARCHITECTURE_EXCELLENCE_PASSPORT.md`** §16.

