## BACKEND_GAPS_Tasks_NEXT — домен Tasks & Attention Feed

### 1. Текущее состояние в коде

- **Сущности:** `Task`, `AttentionFeed`/`AttentionItem` DTO;  
  используются в `AttentionFeedService` и соответствующих роутерах.
- **Сервисы:**
  - `AttentionFeedService` аггрегирует follow‑up по чатам, ERP‑ошибки, retention/loyalty‑gap.
- **API/Frontend:**
  - `admin_tasks.py`, `AdminTasksPage.tsx`;
  - `admin_attention_feed.py`, `AdminAttentionFeedPage.tsx`.

### 2. Сравнение с ARCH_TASKS_NEXT и BUSINESS_LOGIC_V2

- ARCH/V2 ожидают:
  - плотную интеграцию Tasks и AttentionFeed;
  - AI Task Manager (ночной/периодический генератор задач).
- Фактическое состояние:
  - AttentionFeed уже мощный и связанный с многими доменами;
  - Tasks реализованы, но AI‑менеджер задач и «двусторонняя» связка с AttentionFeed остаются в основном идеей.

### 3. Выявленные GAP’ы

- **TASK-1 — слабая формализация связи Task ↔ AttentionItem (S2)**  
  - нет явной модели/связи, показывающей, какие задачи созданы из каких attention‑элементов и как их статус влияет на ленту.  
  - *Частично по CRM‑цепочке:* системные задачи по `BookingCancelled` / `BookingNoShow` получают `lead_id` (если лид найден по записи), идемпотентность по `dedup_id` в payload события / `Task.source_event_id`; полная двусторонняя связка Task ↔ AttentionItem остаётся в зоне TASK‑1.

- **TASK-2 — AI Task Manager как незавершённый модуль (S2)**  
  - бизнес‑логика описывает nightly‑процесс с AI, но в коде нет выделенного слоя для генерации и валидации таких задач.

### 4. Оценка сложности исправления

- **TASK-1:** средняя — нужно добавить связи/метаданные, не ломая существующую логику AttentionFeed.
- **TASK-2:** средняя — зависит от развития AI‑слоя и требований к объёму задач.

