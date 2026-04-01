# 🚀 DEV_PROMPTS_STAFF_CALENDAR_MONTH_GRID_ENTERPRISE_2026 — пошаговая реализация month-grid (для @DEV)

> **Файл-связка:** [`ARCH_STAFF_CALENDAR_MONTH_GRID_ENTERPRISE_2026.md`](./ARCH_STAFF_CALENDAR_MONTH_GRID_ENTERPRISE_2026.md)

> **Цель:** превратить текущую реализацию календаря (week-list карточки событий) в enterprise month-grid:
> - событийные time-bars внутри day-cell
> - маркеры reminders (за 15 минут) и “новое приглашение для меня”
> - кнопка ack приглашения + отображение creator-статусов
> - “sound 3 + visual” при появлении новых сигналов

---

## 0. Scope / Участники

- Домены: staff-collab calendar
- Страницы: `frontend/src/admin/pages/AdminStaffCalendarPage.tsx`
- Backend: `src/api/v1/routers/admin_staff_collab.py`, `src/application/services/staff_collaboration_service.py`
- БД: новая таблица `staff_calendar_event_invitations` + DTO/эндпоинты

---

## 1. Pre-checks (минимум перед началом)

1. Убедиться, что текущий календарный CRUD работает (создание/редактирование/участники).
2. Оценить влияние на миграции (новая таблица + индексы).
3. Проверить, что Celery reminders не ломаются (уже есть `staff_calendar_reminder_deliveries` и расчёт `fire_at`).

---

## 2. Backlog: dev таски (рекомендуемый порядок)

### 2.1 Backend: новая invitation table + service sync

1. **Добавить ORM сущность**
   - файл: `src/domain/entities/staff_calendar_event_invitation.py` (создать)
   - модель: `StaffCalendarEventInvitation` с уникальностью `(event_id, invitee_admin_id)`

2. **Миграция**
   - файл: `alembic/versions/<NEW_REV>_staff_calendar_event_invitations.py` (создать)
   - up: create table + indexes
   - down: drop table

3. **Сервис: создание приглашений при create event**
   - файл: `src/application/services/staff_collaboration_service.py`
   - метод: `create_calendar_event(...)`
   - после сохранения `StaffCalendarEvent` и `StaffCalendarEventParticipant`:
     - собрать final list invitee ids = (creator + participants)
     - создать invitation rows для каждого invitee, если не существует

4. **Сервис: sync invitations при update event**
   - метод: `update_calendar_event(...)`
   - когда меняется `participant_admin_ids`:
     - вычислить added = new - old
     - вычислить removed = old - new
     - для added: создать invitation rows (ack null)
     - для removed: удалить invitation rows
   - осторожно: если participant останется, ack сохраняется.

5. **Сервис: cascade на delete event**
   - delete event уже должен каскадно удалять participants; гарантировать cascade invitation тоже (FK ondelete=CASCADE)

6. **Сервис: endpoint-ready helpers**
   - helper methods (не публичные):
     - `_get_user_invitation_ack_map(event_ids, user_id)`
     - `_count_unseen_invitations(event_ids, user_id)`

**Acceptance criteria:**
- invitation rows появляются при создании события для всех участников
- ack не сбрасывается при update, если человек остался участником
- при удалении участника invitation пропадает

---

### 2.2 Backend: API endpoints для month-grid + ack

1. **DTO**
   - файл: `src/application/dto/staff_collab_dto.py`
   - добавить структуры для response:
     - `CalendarEventChip` (минимальные поля для day-cell)
     - `CalendarDayCell`
     - `StaffCalendarMonthGridResponse`
     - `StaffCalendarEventDetailsResponse` (если нужна детализация)
     - `StaffCalendarInvitationAckResponse`

2. **Month-grid summary endpoint**
   - файл: `src/api/v1/routers/admin_staff_collab.py`
   - роут: `GET /v1/admin/staff/calendar/month?from=<iso>&to=<iso>`
   - логика (service layer):
     - fetch events за диапазон [from,to] (enterprise: пересечение с диапазоном предпочтительнее)
     - fetch participants for fetched events (одним запросом)
     - определить, где `current_admin_id` является участником (для reminders + invites)
     - fetch invitations для current admin + fetched event_ids (одним запросом)
     - reminders: fetch `StaffCalendarReminderDelivery` для event_ids; разнести по `fire_at` день в DTO
   - сформировать response: days[date].events + reminder_events + unseen_invite_count

3. **Ack endpoint**
   - роут: `POST /v1/admin/staff/calendar/events/{event_id}/invitations/ack`
   - проверить:
     - event существует и belongs_to clinic
     - текущий admin является creator или participant
   - обновить invitation row: `acknowledged_at = utc_now_naive()` (или utc_now если тайз-колонка)
   - вернуть `acknowledged_at` и общий unseen count (опционально)

4. **Event details endpoint (для modal)**
   - роут: `GET /v1/admin/staff/calendar/events/{event_id}`
   - вернуть:
     - event data
     - participants
     - reminder info
     - invitation ack status для текущего админа
     - если current admin = creator: ack status summary для участников

**Acceptance criteria:**
- month endpoint возвращает правильные “новые” invitation markers именно для текущего админа
- ack endpoint корректно скрывает “новое” после нажатия и не даёт ack сторонним
- details endpoint отдаёт данные для UI modal

---

### 2.3 Frontend: month-grid UI + данные + модалки

1. **Refactor страницы**
   - файл: `frontend/src/admin/pages/AdminStaffCalendarPage.tsx`
   - заменить weekAnchor/startOf(week) на monthAnchor:
     - `monthAnchor = dayjs()` state
     - `rangeFrom = monthAnchor.startOf('month')`
     - `rangeTo = monthAnchor.endOf('month')`

2. **Новые hooks**
   - файл: `frontend/src/hooks/useStaffCollab.ts`
   - добавить:
     - `useStaffCalendarMonthGrid(fromIso, toIso)` -> response DTO
     - `useAckStaffCalendarInvitation(eventId)` mutation -> ack response
     - (опционально) `useStaffCalendarEventDetails(eventId)`

3. **queryKeys**
   - файл: `frontend/src/queryKeys.ts`
   - добавить ключи:
     - `staffCollab.calendarMonth(fromIso,toIso)` (или по anchor month)
     - `staffCollab.calendarEventDetails(eventId)`

4. **Компонент MonthGrid**
   - внутри `AdminStaffCalendarPage.tsx` или отдельный файл `frontend/src/admin/components/staff-calendar/MonthGrid.tsx`
   - реализация day-cell:
     - отображать time bars:
       - рассчитать позицию/высоту внутри cell на основе `starts_at`/`ends_at`
       - склеить в 2–3 слоя (stack) + `+N`
     - добавить markers:
       - reminder marker (icon with color)
       - unseen invitation marker (icon “новое для меня”)

5. **Modal/Drawer**
   - клик по day-cell: показывать:
     - список событий этого дня
     - у каждого события: коротко, плюс action ack (если применимо)
   - клик по event: загрузить event details (если нужно) и открыть edit modal (уже существующий edit modal можно расширить)

6. **Редактирование/создание событий**
   - использовать существующую механику create/edit:
     - time pickers, participants, reminder_minutes_before, task_id
   - после success:
     - invalidate month-grid query key

**Acceptance criteria:**
- month-grid рендерится корректно для текущего месяца и включает дни сетки
- time bars выглядят “как в полноценном календаре” (видно время/длительность)
- маркеры invitations/reminders корректны по данным backend

---

### 2.4 Frontend: “sound 3 + visual” триггеры

1. **Hook сигналов**
   - В `AdminStaffCalendarPage.tsx` или отдельном hook:
     - query summary через `useStaffCalendarMonthGrid` (или дополнительный “signals-only” endpoint)
     - хранить `lastSignalsSignature` в `useRef` / state
     - сравнивать:
       - unseen_invites_count
       - reminders_due_now_count (если будет в DTO)

2. **Логика воспроизведения**
   - при росте unseen_invites_count или изменении reminders_due_now_count:
     - play sound: 3 повторения (например, 0s + 0.7s + 1.4s)
     - визуально: toast/badge highlight (например, подсветка day-cell и/or фиксированный alert сверху)

3. **Источник audio**
   - если в проекте нет аудио ассетов:
     - выбрать один локальный файл (или использовать WebAudio beeps)
   - продумать: отключаемо пользователем (enterprise UX: settings).

**Acceptance criteria:**
- звук проигрывается ограниченно и только при появлении новых сигналов (без спама)

---

## 3. Тест-план (минимум)

### Backend
1. Unit tests на service:
   - create_calendar_event создаёт invitations
   - update_calendar_event sync добавляет/удаляет invitations
   - ack endpoint обновляет acknowledged_at
2. Router tests (pytest):
   - 403/404 когда admin не является участником
   - корректный response shape для month endpoint

### Frontend
1. TypeScript compile (уже у вас enforced).
2. Ручная проверка:
   - создать событие с несколькими участниками
   - убедиться, что на остальных “новое” подсвечено до ack
   - нажать ack и проверить скрытие marker
   - убедиться, что reminder marker появляется по fire_at в нужный день.

---

## 4. Предложения на последующие итерации (если не будет закрыто другим DEV_PROMPT)

1. SSE/WebSocket вместо polling для точного момента “напоминание начнётся через 15 минут”.
2. Полноценный drag/drop “перенос событий” внутри month-grid (с перерахчётом time bars).
3. Интеграция календарных сигналов в общий `AttentionFeed` (чтобы “новое событие/сообщение” было единым центром уведомлений для всей админки).
4. Более богатый render в day-cell: группировка по типам (meet/task/all-day) и color-coding по категориям.

