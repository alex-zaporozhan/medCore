## BACKEND_GAPS_CRM_NEXT — домен CRM (Sales & Kanban)

### 1. Текущее состояние в коде

- **Сущности и сервисы:**
  - `LeadPipeline`, `LeadStage`, `LeadCard`, `LeadNote` (по коду и BUSINESS_LOGIC_V2).
  - `LeadService` реализует операции по выборке/изменению лидов, стадий, заметок.
- **API:**
  - `admin_crm.py`:
    - список pipelines и stages;
    - список лидов с фильтрами/пагинацией;
    - детальная карточка лида с заметками;
    - смена стадии (Kanban drag&drop);
    - создание заметок.
- **Frontend:**
  - `AdminSalesPipelinePage.tsx`:
    - Kanban‑доска с drag&drop;
    - агрегации по стадиям (количество, сумма по лиду);
    - переход в Omnichannel по `omnichannel_contact_id`.

### 2. Сравнение с ARCH_CRM_NEXT и BUSINESS_LOGIC_V2

- ARCH/V2 ожидают:
  - полную связку Omnichannel → Booking/Payments → CRM;
  - автоматическое создание и движение `LeadCard` по событиям;
  - использование ERP‑данных для `actual_value` и LTV;
  - глубокую интеграцию с AI/Omnichannel.
- Текущее состояние:
  - ручная Kanban с хорошей UI‑реализацией уже есть;
  - степень автодвижения по событиям ограничена/частичная (по коду и QA_AUDIT_NEXT).

### 3. Выявленные GAP’ы

- **CRM-1 — частичное/отсутствующее автодвижение по событиям (S2)** — *v1 закрыт в коде (`DEV_PROMPT_CRM_EVENTS_007`)*  
  - Реализованы слушатели шины → `LeadLifecycleService` (контакт, создание записи, завершение визита, отмена, no‑show, stale best‑effort), ручной Kanban использует тот же механизм смены стадии.  
  - Дальнейшее усиление: отдельный job для stale, дедуп задач, обогащение визита ERP‑суммами в `LeadEventVisitCompleted` — см. `ARCH_DEV_CRM_EVENTS_007_TASKS.md` (раздел «На потом») и `DEV_PROMPT_CRM_MONEY_008`.

- **CRM-2 — источник истины по деньгам не централизован (S2)** — *v1 закрыт в коде (`DEV_PROMPT_CRM_MONEY_008`)*  
  - `actual_value` пересчитывается из ERP (`financial_transactions`, type=income) по `lead_id` и/или `booking_id`; событие завершения визита не подставляет локальную выручку в CRM.  
  - `estimated_value` — прогноз (ручной PATCH или авто с прайса услуги по primary booking).  
  - Остаётся: полнота сценариев «несколько визитов» без `lead_id` на проводках, унификация с materialized ERP‑views, расширенный прогноз — см. `ARCH_DEV_CRM_MONEY_008_TASKS.md`.

- **CRM-3 — ограниченная интеграция с AI‑слоем (S2)**  
  - Архитектура предполагает, что AI/Omnichannel могут двигать карточки и предлагать действия;  
  - backend‑API для безопасного AI‑управления стадиями/лидами ещё не оформлен как tools‑набор.

### 4. Оценка сложности исправления

- **CRM-1:** средняя/высокая — потребуется добавить listener’ы/событийный слой вокруг Booking/Omnichannel/ERP.
- **CRM-2:** средняя — нужно аккуратное согласование полей с ERP‑сущностями и отчётами.
- **CRM-3:** средняя — это больше про проектирование AI‑tool API поверх уже существующих сервисов.

