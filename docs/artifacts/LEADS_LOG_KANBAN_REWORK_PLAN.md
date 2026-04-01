## План работ QA_ARCH: «Лиды (лог)» как строгий дубль канбана

### Контекст и цель
Сейчас `/admin/leads-log` реализован как отдельная “упрощённая доска” (3 колонки + transcript справа) и **не переиспользует** существующий kanban‑UX из `AdminTasksPage`. Это противоречит требованию: **“сделать отдельную канбан страницу как дубликат того канбана что уже есть, но вместо задач — лиды”**.

Цель этой переработки:
- сделать `/admin/leads-log` **визуально и поведенчески** максимально идентичной `AdminTasksPage`
- при этом источником “лидов” будет **Task‑артефакт** (уже создаётся при `POST /admin/omni-chats/{id}/resolve`)
- transcript и “обогащение” — через `OmniLeadLog` (immutable snapshot), открываемое из kanban карточки

### Winner decisions (итоговые решения)
- **Kanban surface**: переиспользуем `AdminTasksPage`‑паттерн 1:1 (board/columns/WIP/drag UI остаются).
- **Источник карточек**: `Task` со `stream.slug = "leads-log"` и `status="done"` (по умолчанию).
- **Связь Task → LeadLog**: `Task.trace_id = "omni_lead_log:<uuid>"` (уже так создаётся).
- **Transcript UX**: drawer/side panel “Лог диалога” открывается по клику на карточку (или отдельной кнопкой в карточке), загружает `GET /admin/lead-logs/{id}`.
- **Фильтрация по дню**: day picker сверху страницы влияет на dataset (см. ниже — варианты реализации).

### Текущее состояние (факт‑чек)
- `POST /api/v1/admin/omni-chats/{chat_id}/resolve` создаёт:
  - `OmniLeadLog` (таблица `omni_lead_logs`)
  - `TaskStream(slug="leads-log")` (lazy)
  - `Task(status="done", source="system", trace_id="omni_lead_log:<id>")`
- `GET /api/v1/admin/lead-logs` и `GET /api/v1/admin/lead-logs/{id}` уже существуют.
- `frontend/src/admin/pages/AdminLeadsLogPage.tsx` сейчас **не** дубликат канбана — будет заменён.

---

## План действий (черновик v1)

### 1) UX/FE: сделать `/admin/leads-log` дублём `AdminTasksPage`
**Подход**: создать `AdminLeadsLogKanbanPage.tsx` как thin‑wrapper над канбан‑компонентами/кодом `AdminTasksPage`.

Вариант A (предпочтительный): *минимальная дифф‑переработка `AdminTasksPage` в “переиспользуемый канбан‑shell”*.
- Вынести из `AdminTasksPage` универсальные части:
  - заголовок/панель фильтров
  - board picker + columns config (если применимо)
  - stream picker
  - основной kanban grid (колонки по `task.status`)
  - DnD/reorder мутацию
  - drawer/details panel (TaskDetailsView) — оставляем, но расширяем под lead‑log
- Собрать 2 страницы:
  - `AdminTasksPage` использует “общий shell” с параметрами (обычные задачи)
  - `AdminLeadsLogPage` использует тот же shell, но с параметрами:
    - `fixedStreamSlug="leads-log"` (или `fixedStreamId`)
    - `defaultStatusFilter = ["done"]` (или показываем только done‑колонки)
    - отключить “создание задачи вручную” (или переименовать CTA)
    - включить lead‑log drawer

Вариант B (быстрый, но грязнее): *копипаст‑клон `AdminTasksPage` → заменить источники данных*.
- Быстрее, но риск расхождений с будущими правками канбана.
- Использовать только если вариант A упирается в большой рефактор.

**Выбор**: A, потому что вы хотите “строго как дубликат” и это снижает будущий техдолг.

### 2) Данные на странице: брать Task‑артефакты, но с “дневным” срезом
Требование: “календарь/день” показывает обращения за день.

Существующие `tasks` API ориентированы на workflow статусы/фильтры, но не на “closed_at day”.

Варианты:
- **2.A (самый чистый)**: добавить в backend endpoint именно под kanban‑dataset лид‑логов:
  - `GET /api/v1/admin/tasks?stream_slug=leads-log&completed_from&completed_to` (или `closed_from/to`)
  - расширить существующий list tasks фильтрами по `completed_at`/`created_at`
  - FE на `/admin/leads-log` подтягивает только task rows за выбранный день
- **2.B (быстро, но хуже)**: грузить все tasks stream `leads-log` и фильтровать на клиенте по `completed_at`.
  - не подходит для реальных объёмов и “enterprise” ожиданий

**Выбор**: 2.A — расширяем tasks list API фильтрами по датам.

### 3) LeadLog drawer: открыть immutable transcript из kanban
Реализация:
- парсить `lead_log_id` из `task.trace_id` по шаблону `omni_lead_log:<uuid>`
- добавить компонент `LeadLogDrawer`:
  - header: контакт/телефон/оператор/время закрытия/outcome badge
  - тело: transcript (plain text) + опционально structured view (если `transcript_json` есть)
  - кнопка “Открыть omni‑чат” (deep link) — опционально, если есть `omni_chat_id`
- кэширование: react‑query ключ `["admin-lead-log", id]`

### 4) Omni‑чат: сделать закрытие “не прячущимся”
Проблема из факта: “Закрыть диалог” показывается только после claim и неочевидна.

План:
- В шапке диалога всегда показывать:
  - если unassigned: `Взять в работу` (как сейчас)
  - если assigned me/owner: `Закрыть диалог` (как сейчас)
  - если assigned другому: disabled “В работе у <admin>” (без закрытия)
- После клика `Закрыть диалог`:
  - optimistic UI: сразу уводить из “В работе” списка (или помечать закрытым)
  - toast “Лид зафиксирован в логе” + CTA “Открыть Лиды (лог)”

### 5) Контракты/типизация: укрепить resolve
- заменить `response_model=dict` на DTO (`OmniChatResolveResponseDto`)
- унифицировать формат ошибок: `{code,message}` (как в остальном omni API)
- уточнить RBAC:
  - `resolve` требует `omni.inbox.manage`
  - lead logs требуют `leads.log.view`

### 6) Навигация и права
- добавить пункт меню в админ‑сайдбар: “Лиды (лог)” (виден при `leads.log.view`)
- проверить `AdminRightsPoliciesPage` домены: `leads` добавлен (уже)

### 7) Тесты/проверки
- FE:
  - `npm run build`
  - Playwright: добавить e2e smoke:
    - страница `/admin/leads-log` рендерится
    - фильтр дня меняет dataset (mock)
    - drawer открывается и показывает transcript
- BE:
  - unit/contract тест на `resolve` idempotency
  - тест на `/lead-logs` RBAC deny/allow
  - тест на новые date‑filters в tasks list

---

## Пересмотр плана (самопроверка на упущения)
Проверка на “строго дубль”:
- мы не должны сделать “похожую” страницу, мы должны **переиспользовать** те же компоненты/UX паттерны канбана.
  - Вариант A решает это; Вариант B — риск drift.

Проверка на “вместо задач — лиды”:
- данные будут всё равно `Task`, но семантика — “лид‑лог”.
  - Поэтому в UI копии канбана нужно:
    - переименовать лейблы (“Задачи” → “Лиды (лог)”, “Задача” → “Обращение”)
    - скрыть неуместные действия (создание/claim/assignees, если не нужно)

Проверка на производительность:
- фильтрация по дню должна быть серверной → пункт 2.A обязателен.

Проверка на корректность времени:
- сейчас `/lead-logs?day=` использует UTC день.
  - На канбан‑странице лучше привязать день к таймзоне клиники (или хотя бы явно показывать “UTC”).
  - Это улучшение можно запланировать как follow‑up, но минимум — не ломать.

---

## QA‑критика (что можно запланировать ещё лучше) → правки плана

### Критика 1: “День” должен быть в TZ клиники, иначе отчёты будут неверны
**Правка**:
- В backend tasks date‑filters принимать ISO дату + tz offset/clinic tz:
  - `day=YYYY-MM-DD` и сервер строит границы дня в TZ клиники
  - или `from/to` уже в UTC, но FE рассчитывает по TZ клиники

MVP решение:
- использовать TZ из `clinic.timezone` (если есть) при вычислении day bounds в backend для `/lead-logs` и нового tasks‑фильтра.

### Критика 2: “Outcome booked” по LeadCard.primary_booking_id слишком слабый сигнал
**Правка**:
- при resolve сохранять `booking_id` не только из `LeadCard.primary_booking_id`, но и:
  - искать booking, созданный в интервале между `opened_at..closed_at+N` и связанный с contact/patient
  - если нет уверенности — outcome UNKNOWN

MVP:
- оставить как есть, но добавить `UNKNOWN` вместо “NOT_BOOKED” при отсутствии lead (сейчас ставится NOT_BOOKED).

### Критика 3: Нужна наблюдаемость/аудит “resolve”
**Правка**:
- логировать событие (метрики или audit log): кто закрыл, какой чат, какой lead_log_id.

### Критика 4: Idempotency и гонки
**Правка**:
- обеспечить транзакционность: закрытие чата + вставка lead_log + task должны быть атомарными
- уникальный constraint `omni_chat_id` есть; при IntegrityError возвращать существующий lead_log_id.

---

## Обновлённый план (v2, финальный)
1) Рефактор kanban‑shell из `AdminTasksPage` → переиспользуемый компонент.
2) Сделать `AdminLeadsLogPage` как wrapper канбана с фиксированным stream `leads-log`.
3) Добавить server‑side фильтр tasks по `completed_at` (day bounds).
4) Подключить `LeadLogDrawer` по `Task.trace_id`.
5) Улучшить omni‑chat header UX для `Закрыть диалог` + toast/CTA.
6) Усилить backend `resolve`: DTO response, idempotency via unique+IntegrityError, outcome UNKNOWN в сомнительных случаях.
7) Навигация: пункт меню + RBAC gating.
8) Тесты FE+BE (минимум smoke + idempotency).

