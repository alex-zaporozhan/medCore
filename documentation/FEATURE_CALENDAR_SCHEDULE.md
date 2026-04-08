# Календарь и расписание

> **Версия:** 2026-04-02 | Несколько слоёв: **слоты для записи**, **админское расписание клиники**, **личный/командный календарь персонала**, **связка задач с календарём**.

## Запись пациента (публичное расписание)

- **Модуль:** `schedule` — префикс **`/doctors`** (доступные слоты и логика записи с точки зрения API v1).
- **Связка:** `bookings` — пути без единого `APIRouter.prefix`; см. декораторы в `bookings.py` и INDEX.

## Расписание в админке

- **`admin_schedule`**, **`admin_doctor_schedule`** — префиксы **`/admin/clinics`** и **`/admin/doctors`** соответственно (таблица в [API_V1_ROUTER_MANIFEST.md](./API_V1_ROUTER_MANIFEST.md)).
- **UI:** `/admin/schedule`, `/admin/doctor-schedule` (`routePaths.ts`).

## Календарь персонала (события staff)

- **Модуль:** `admin_staff_collab` — префикс **`/admin/staff`**: создание/обновление событий, месячная сетка, приглашения, ack и т.д. (полный список путей — [router_surface/INDEX.md](./router_surface/INDEX.md)).
- **UI:** `/admin/calendar`.

## Задачи и календарь

- **Модуль:** `admin_tasks` — эндпоинты вида `.../calendar-context`, приглашения на события (`.../calendar-events/.../invite`). См. раздел `admin_tasks` в INDEX и [FEATURE_KANBAN_AND_TASKS.md](./FEATURE_KANBAN_AND_TASKS.md).

## Тесты

- Примеры: `tests/api/test_schedule.py`, `tests/api/test_staff_calendar_event_*.py`, `tests/api/test_admin_tasks_workflow_and_calendar.py` — полный список по INDEX для перечисленных модулей.

---

Reference: [SCRIBE_ROUTER_CHECKLIST.md](./SCRIBE_ROUTER_CHECKLIST.md)
