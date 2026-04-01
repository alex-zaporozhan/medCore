## ARCH_TASKS_NEXT — домен Tasks & Attention Feed

### 1. Краткое описание домена

Домен **Tasks & Attention Feed** превращает «шум» операционных событий в **управляемый список действий**:

- tasks — задачи для людей (админов, менеджеров, владельцев);
- attention feed — «лента внимания» по ключевым событиям (follow‑up, retention‑gap, ERP‑ошибки и т.п.);
- AI Task Manager — генерация задач на основе данных и анализа.

### 2. Актуальная модель сущностей (по коду / BUSINESS_LOGIC_CURRENT/V2)

- `Task` — сущность задачи:
  - `id`, `clinic_id`, `title`, `description`, `assignee_id`, `status`, `priority`, `due_date`,
  - ссылки на `booking_id`/`patient_id`/`lead_id` и др. (по описанию V2 и коду).
- `AttentionFeed`, `AttentionItem` / DTO:
  - собирает follow‑up по чатам, ERP‑ошибки, retention‑gap и loyalty‑gap события.

Сервисы:

- `AttentionFeedService` в `src/application/services/attention_feed_service.py`:
  - уже агрегирует follow‑up, retention, loyalty и конфликтные ситуации в одну ленту;
  - использует `Booking`, `ChatMessage`, `Conversation`, `Patient`, `Task`, `CustomerSubscription`, `Wallet`, `LoyaltyPolicy`.

Frontend:

- `AdminAttentionFeedPage.tsx`;
- `AdminTasksPage.tsx`.

### 3. Целевая модель vNext

1. **Сильная связка Tasks ↔ AttentionFeed:**
   - `AttentionItem` может порождать одну или несколько `Task` (с пометкой «создано из AttentionFeed/AI»);
   - изменение статуса задач (done/cancelled) отражается в AttentionFeed (например, скрытие/отметка как обработано).

2. **AI Task Manager (V2):**
   - периодические AI‑запуски:
     - анализируют AttentionFeed, отмены, пустые окна расписания, бездвижные лиды, падающий LTV и т.п.;
     - генерируют набор задач в формате (title/description/due_date/assignee/role);
   - backend:
     - валидирует и создаёт `Task` с метаданными «создано AI»;
     - пишет событие в AttentionFeed.

3. **Единая модель статусов и приоритетов:**
   - статус: `open`, `in_progress`, `done`, `cancelled`;
   - приоритет: числовой/ранговый (согласованный между AttentionFeed и Task списком).

4. **UX‑центр задач:**
   - `AdminTasksPage` показывает:
     - задачи с фильтрами по доменам, клинике, источнику (ручная/AI/система);
     - быстрые переходы к связанным сущностям (визит, пациент, лид, чат).

### 4. Связи с другими доменами

- **Booking:** задачи по no‑show, массовым отменам, перегрузке расписания.
- **ERP:** задачи по ERP‑ошибкам, подозрительным движениям денег/склада.
- **CRM:** задачи по «застывшим» лидам и важным сделкам.
- **Loyalty:** задачи по клиентам с высоким балансом, но низкой активностью.
- **Omnichannel & AI:** задачи по follow‑up из чатов, выявленным AI‑паттернам риска.

### 5. Frontend Kanban Hardening (2026-03)

Для `AdminTasksPage` принят production-профиль канбана:

- центрированные модалки деталей/создания/чата;
- отдельный фильтр-свимлейн «Ждут моего подтверждения»;
- WIP-лимиты по колонкам + визуальный контроль перегруза;
- DnD между колонками и перестановка внутри колонки;
- правила переходов (в `done` только при checklist и без blocked);
- SLA overdue и Aging-индикаторы на уровне колонки;
- blocked state + причина блокировки;
- bulk-операции и быстрые фильтры;
- audit-лента перемещений;
- keyboard DnD (`Alt+ArrowLeft/Right`).

До появления серверного контракта (`rank`, `blocked_reason`, history endpoint) часть состояния хранится во frontend persistence (local/session).

