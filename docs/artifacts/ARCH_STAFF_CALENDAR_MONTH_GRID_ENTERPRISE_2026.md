# ARCH_STAFF_CALENDAR_MONTH_GRID_ENTERPRISE_2026 — month-grid календарь (роль @ARCH, Enterprise)

> **Цель артефакта:** зафиксировать end-to-end архитектуру “настоящего” month-grid календаря на странице `http://localhost:3010/admin/calendar`:
> - табличная сетка дней текущего месяца
> - в каждой ячейке: события (мини time-render), мини-заголовки/иконки, маркеры reminders и “новые приглашения”
> - визуальные/звуковые уведомления (как “новое событие/сообщение”) и кнопка подтверждения “я увидел”
>
> **Связь с текущей базой:** `ARCH_PHASE_01_STAFF_CORE_2026.md` (календарь внутри staff-collab P1).

---

## 1. Business Goals (BIZ)

1. Оператор/администратор должен за 1–2 взгляда понимать:
   - какие события в конкретный день (в т.ч. сколько и на какое время)
   - где у него “новое” (он добавлен на коллективное совещание)
   - где его “ждёт” событие через 15 минут (напоминание по start)
2. Оповещения должны быть:
   - визуальные (подсветка/маркер/бейдж в ячейке и/или в заголовке дня)
   - звуковые (требование: “звук 3 раза” при появлении нового)
3. У приглашённых участников есть прозрачный action:
   - “Подтвердить что увидел” (ack) — это должно быть видно создателю.

---

## 2. Non-Goals (что не делаем в этом документе)

- Полноценный drag-and-drop месяц-календаря (перемещение событий) — можно отложить на отдельный enterprise-спринт.
- Переписывание механики Celery “send reminders”: в этом архитектурном пакете мы используем существующую таблицу `staff_calendar_reminder_deliveries` как источник времени `fire_at` (и отдельно рассчитываем, где этот `fire_at` попадает в день).
- Полная интеграция со “всеми каналами уведомлений” (Telegram/Email/SMS) — UI-нотификации и логика “ack/visual markers” внедряются независимо.

---

## 3. UX Requirements (month-grid)

### 3.1 Навигация
- Кнопки: `<<` (прошлый месяц), `Сегодня`, `>>` (следующий месяц).
- Заголовок: “Март 2026” (ru).

### 3.2 Сетка дней
- 7 колонок (пн–вс) + строки 5/6 (как у типичных календарей).
- Дни, которые не относятся к текущему месяцу, показываются в “disabled style” (не как отдельные данные, а как визуальные буферы для сетки).

### 3.3 Контент ячейки (что показывать)
В каждой ячейке дня `D`:

1. **Time-render событий** (полоски/рендер “как в полноценном календаре”):
   - Если событие не `all_day`: render mini time-bar внутри ячейки
   - Если `all_day`: отдельная иконка/бейдж “Весь день”
   - Если событий много: stack по 2–3 верхних позициям, остальные как `+N`
2. **Иконки/мини-заголовки**:
   - событие: `title` (1–2 строки, truncate)
   - “Связь с задачей” (если `task_id != null`) — маленькая иконка
3. **Reminders маркер**:
   - если у события `reminder_minutes_before > 0` и `fire_at` попадает в день `D`, то показываем “колокольчик/точку”
   - при “новом” состоянии (скоро/только что) дополнительно выделяем цветом
4. **Invites маркер (новое событие/сообщение для конкретного пользователя)**:
   - если текущий админ — приглашённый участник и приглашение ещё не ack’нуто, то в ячейке показываем маркер “новое”
   - этот маркер должен быть именно “новое для меня”, а не “новое вообще”

### 3.4 Детализация по клику
- Клик по дню: открыть `Modal/Drawer` со списком событий дня и действиями.
- Клик по событию: открыть карточку события внутри этого Modal:
  - участники
  - напоминание (когда наступит `fire_at`)
  - если пользователь — приглашённый: кнопка `Подтвердить что увидел` (ack)
  - если пользователь — создатель: отображение списка ack’нувших (или хотя бы счетчиков).

---

## 4. Domain/Data Architecture

### 4.1 Существующие сущности
- `StaffCalendarEvent`:
  - `starts_at`, `ends_at`, `all_day`
  - `created_by_admin_id`, `task_id`
  - участники: `StaffCalendarEventParticipant`
  - `reminder_minutes_before` (опционально)
- `StaffCalendarReminderDelivery` (Celery):
  - `event_id` (unique per event)
  - `fire_at`, `sent_at`

### 4.2 Новая сущность: invitation (ack “я увидел”)

Добавить таблицу:
- `staff_calendar_event_invitations`
  - `id` (UUID, pk)
  - `clinic_id` (UUID, индекс)
  - `event_id` (UUID, FK -> `staff_calendar_events`, ondelete=CASCADE)
  - `invitee_admin_id` (UUID, FK -> `admins`, индекс)
  - `created_at` (default now)
  - `acknowledged_at` (nullable)

Инварианты:
- `Unique(event_id, invitee_admin_id)`
- invitation создаётся:
  - при создании события для каждого `participant_admin_id` и для `created_by_admin_id` (если он не совпадает)
  - при добавлении нового участника в PATCH
- invitation удаляется:
  - при исключении участника из списка участников (PATCH/удаление события)

---

## 5. Notification Semantics (ваше ТЗ: “новое сообщение/новое событие”)

### 5.1 “Новое, что меня добавили”
Источник истины: `staff_calendar_event_invitations`:
- “новое” для конкретного админа = `acknowledged_at IS NULL`

Что показывать:
- маркер в day-cell месяца
- sound + visual when the count of unseen invitations increases (появились “новые” после последнего опроса/визита)

### 5.2 “Скоро начало (через 15 минут)”
Источник истины: `staff_calendar_reminder_deliveries`:
- у события есть `reminder_minutes_before`
- Celery вычисляет `fire_at = starts_at - reminder_minutes_before`

Для month-grid:
- если `fire_at` попадает в день `D` — показываем маркер reminders

Для sound trigger:
- “звуковое событие” = переход в окно “сейчас + 15 минут” (например, если `now` пересёк `fire_at`).
- Реализация на фронте: периодический polling summary endpoint и локальное хранение “последней известной сигнатуры” (чтобы не проигрывать звук бесконечно).

---

## 6. API Contract (Enterprise)

### 6.1 Month-grid summary endpoint (рекомендуется один, чтобы UI был простым)

Добавить:
`GET /v1/admin/staff/calendar/month?from=<iso>&to=<iso>`

Требования:
- отдавать data “под текущую страницу” (диапазон из month-nav)
- фильтровать по `clinic_id` из RequestContext
- события: `from/to` используется как диапазон по `starts_at` (или по пересечению диапазонов — enterprise-выбор см. ниже)
- приглашения: только те, где current admin является invitee
- reminders: только по событиям, где current admin является участником

Response (пример DTO):
- `month`: { from, to }
- `days`: array of
  - `date` (YYYY-MM-DD)
  - `is_in_current_month` (bool)
  - `events`: list of `CalendarEventChip`:
    - `id`, `title`, `starts_at`, `ends_at`, `all_day`, `task_id`, `created_by_admin_id`
  - `reminder_events`: list of `CalendarEventChip` (или ids)
  - `unseen_invite_count`: number
  - `unseen_invite_events`: list of ids (если нужно для детализации)
- `notification_signals`:
  - `unseen_invites_count`
  - `reminders_due_now_count` (опционально, для “sound 3” триггера)

**Enterprise выбор по диапазону событий:**
- MVP: отдаём все события где `starts_at` в [from,to]
- Enterprise: отдаём события, которые пересекают [from,to] (start < to && end > from), чтобы корректно отображать длительные события.

### 6.2 Event details for modal

Добавить:
`GET /v1/admin/staff/calendar/events/{event_id}`

Response:
- событие
- список участников
- напоминание (reminder_minutes_before, fire_at, sent_at)
- invitation status for current admin (`acknowledged_at`)
- creator view: ack summary (сколько участники ack’нули)

### 6.3 Ack endpoint (кнопка “Подтвердить что увидел”)

Добавить:
`POST /v1/admin/staff/calendar/events/{event_id}/invitations/ack`

Поведение:
- текущий админ обязан быть invitee (participant или creator)
- обновить `acknowledged_at = now()`
- вернуть обновленный статус

---

## 7. RBAC и Security (enterprise-grade)

1. Чтение календаря: `view_staff_collab`.
2. CRUD событий: `manage_staff_collab` (как сейчас).
3. Изменение participants: `invite_staff_calendar_participants` (как сейчас).
4. Ack invitation:
   - permission code может не требоваться (или требовать “view_staff_collab”),
   - но обязательно проверять принадлежность текущего админа участнику события.

---

## 8. Performance and Scalability

- Month-range: ограничить запрос по `from/to`.
- Делать агрегации на backend, а не в N+1:
  - собрать события за диапазон
  - собрать participants для этих событий одним запросом
  - собрать invitations для current admin для этих событий одним запросом
  - собрать reminders deliveries для этих событий (уникально per event) одним запросом
- Индексы для новой таблицы:
  - `ix_staff_calendar_event_invitations_clinic_invitee (clinic_id, invitee_admin_id, acknowledged_at)`
  - `ix_staff_calendar_event_invitations_event_id (event_id)`

---

## 9. Observability

Логи:
- когда пользователь ack’нул приглашение
- когда не прошла проверка “пользователь не является участником”

Метрики:
- `calendar_invitation_ack_total{clinic_id}`
- `calendar_month_load_latency_seconds{clinic_bucket}`

---

## 10. Rollout Plan (чтобы не ломать enterprise)

1. Фича-флаг на фронте:
   - `STAFF_CALENDAR_MONTH_GRID_V1`
2. Backend может поставляться одновременно (endpoint добавляется без поломки текущего).
3. На первом релизе отрисовывать:
   - только events time-bars + reminder marker
   - invitations ack marker + ack action в деталях

