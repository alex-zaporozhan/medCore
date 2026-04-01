# QA/ARCH Roadmap: “Мини‑календарь везде + события из Kanban”

## Цель
Сделать единый UX-подход к календарям в админке:
- единый мини-календарь для выбора дня/месяца (плотный и компактный);
- единый time-picker с “скроллом/колесом” и “быстрым выбором”;
- запрет наложений (backend авторитетно возвращает `400`, UI — дизейбитит занятые варианты);
- возможность создавать события:
  - из страницы календаря (staff collab);
  - из карточки задачи в Kanban;
  - из других “календарных” частей системы (где есть UI типа расписания).

## Что уже сделано (по текущей ветке)
### Staff month-grid calendar (enterprise)
- `AdminStaffCalendarPage`:
  - микро/месячный выбор в модалке создания;
  - защита от наложений через вычисления по событиям дня + backend запрет;
  - отдельные правки UI: “быстрый выбор часа”, центрирование, скрытие выбора месяца при выборе дня+времени;
  - глобальное центрирование модалок через Mantine theme.
- Backend:
  - `_sync_calendar_reminder` приведён к naive UTC, чтобы избежать asyncpg timezone-errors;
  - добавлена серверная проверка наложений (`calendar_event_overlap` -> HTTP `400`).
- Тесты:
  - `test_staff_calendar_month_grid_and_ack.py` проходит;
  - добавлен `tests/api/test_staff_calendar_event_overlap.py`.

## Где в системе сейчас есть “календарные UI” (frontend)
Найдено статически по коду фронта (первые кандидаты для обновления):
1. `frontend/src/admin/pages/AdminStaffCalendarPage.tsx`
   - staff collaboration events, month-grid + month-based time selection.
2. `frontend/src/admin/pages/SchedulePage.tsx`
   - использует `frontend/src/admin/components/ScheduleCalendarGrid.tsx` (грид расписания).
3. `frontend/src/admin/pages/AdminDoctorSchedulePage.tsx`
   - отдельный режим расписания.
4. `frontend/src/admin/pages/AdminTasksPage.tsx`
   - Kanban задач (внутри есть `datetime-local` для планирования задач; событий из задач пока не прокинуты).

Важно: “мини‑календарь” как отдельный reusable-компонент в текущем коде *не выделен* (фактически микро-календарь уже реализован внутри `AdminStaffCalendarPage`). Поэтому для “везде” нужно:
- либо вынести/унифицировать текущий мини-календарь в общий компонент;
- либо создать аналог с тем же интерфейсом и использовать его в расписании и Kanban flows.

## Архитектурные заметки (@ARCH)
### 1) Компонентная унификация
Нужны общие UI-строительные блоки (единый контракт пропсов):
- `MiniCalendarMonthGrid`:
  - вход: `selectedDateIso`, `onDaySelect`, `visibleMonthAnchor`, `onMonthChange`, `compact` (плотность);
  - выход: выбранная дата (ISO `YYYY-MM-DD`).
- `CompactTimePicker`:
  - режим: create/edit;
  - вход: `selectedDayIso`, `valueStart`, `valueEnd`, `onChangeStart`, `onChangeEnd`, `stepMinutes`;
  - UX: “часики” (час +5м для минут) + колесо мыши;
  - выход: start/end в формате `HH:mm` (а в submit — склеивание в ISO datetime).

Компоненты должны быть “чистыми” по состоянию (минимум собственных side-effects). side-effects (данные занятости) — через хук.

### 2) Авторитет backend по “no overlap”
Даже если UI дизейбитит:
- backend всё равно проверяет overlap и возвращает `400`;
- UI обязан показывать `detail` (и желательно `trace_id` из `ApiErrorWithCode`) для диагностики.

### 3) Данные “занятость/свободно”
Для staff month-grid:
- источником overlap-информации служат события из `GET /calendar/month`.
Для расписания (SchedulePage):
- источником занятости служит существующий endpoint расписания (в коде сейчас `useAdminSchedule`).

Поэтому единый time-picker должен уметь работать с разными провайдерами:
- `availabilityProvider(type="staff_month_grid" | "schedule")`.

## Право на создание/приглашение (owner-driven)
Требование: “администраторы не могут создавать события на всех; это должен включать владелец по настройке”.

Текущее поведение backend:
- уже есть RBAC-проверки на:
  - `manage_staff_collab` (доступ к calendar endpoints);
  - `invite_staff_calendar_participants` (если `participant_admin_ids` не пустой).

Что нужно дополнить под “owner-driven” (рекомендуемая схема):
1. Ввести owner-config (таблица/настройки) вида:
   - `staff_collab_event_create_scope`:
     - например: `self_only | manager_scope | clinic_wide` (или список разрешенных ролей/админов).
2. Добавить RBAC/per-tenant policy:
   - endpoint owner управляет правом;
   - backend при `create_calendar_event` проверяет, что вызывающий имеет право на заданный scope.

UI/UX при этом:
- MultiSelect “Участники” должен:
  - либо показываться только когда allowed (или показывать disabled с подсказкой),
  - либо показываться всегда, но дизейблится приглашение при отсутствии permission.

## Большой следующий шаг: Kanban -> “добавить событие”
Текущий контракт backend уже поддерживает `task_id` в `StaffCalendarEventCreate/Update`.
Нужно сделать UI:
1. В карточке Kanban задач добавить кнопку:
   - “Добавить событие” / “В календарь”.
2. При клике:
   - открыть модалку создания staff calendar event;
   - prefill `task_id` автоматически (не требовать UUID вручную);
   - prefill участников (по текущей бизнес-логике):
     - либо “пригласить всех участников задачи”;
     - либо “пригласить минимально-выбранных”.
3. Если задача не выбрана (например, события создаются не из карточки):
   - отдельный UI-поиск задач по строке:
     - скролл по списку;
     - пагинация/инкремент;
     - кнопка “подключить”.

Backend для поиска задач:
- создать новый endpoint:
  - например `GET /v1/admin/tasks/search?query=&limit=&cursor=`
  - возвращает `id`, `title`, `context info` (клиент/lead/статус).

## “Мини-календарь везде” (schedule/booking)
Карта работ:
1. SchedulePage / AdminDoctorSchedulePage:
   - заменить текущие date-controls на `MiniCalendarMonthGrid` в compact-режиме;
   - подтвердить, что раскладка не ломает существующую grid-логику.
2. “Везде где есть календари”:
   - если где-то есть выбор даты/времени, но без month-grid:
     - нужно решить: заменяем на mini-calendar или оставляем date/time inputs.

## E2E-план (не потеряться)
Нужна единая таблица сценариев:
1. staff calendar:
   - create from day click -> prefill day;
   - choose hour/minutes -> no month picker until user “изменить”;
   - overlap attempt -> UI показывает error.
2. schedule:
   - date navigation via mini calendar;
   - create booking (если предусмотрено) через выбранную дату.
3. Kanban task card:
   - click “add event” -> calendar opens -> prefill task_id;
   - select participants -> create succeeds.

## Где добавить анализ @ARCH “как делать”
При старте каждой фазы:
- фиксировать “какой data contract нужен” (какие API возвращают список событий/занятость);
- фиксировать “какие UI-модули общие” (MiniCalendar/TimePicker);
- фиксировать “какие ограничения backend” (overlap, permissions, timezone).

