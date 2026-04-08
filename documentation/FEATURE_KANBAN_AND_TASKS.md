# Kanban, задачи, потоки и теги

> **Версия:** 2026-04-02. **Источник фактов:** роутеры `admin_tasks`, `admin_task_boards`, `admin_task_streams`, `admin_task_tags`; `frontend/src/admin/pages/AdminTasksPage.tsx`; pytest в `tests/api/test_admin_tasks_*.py`, `test_admin_task_boards.py`, `test_admin_task_streams_and_tags.py`.

## Назначение

В админке раздел **Задачи** (`ROUTE_PATHS.admin.tasks`, URL `/admin/tasks`) — канбан по статусам задач клиники: колонки, порядок (reorder), массовые операции, фильтры (в том числе по потокам и тегам). Сценарий лидов может использовать ту же поверхность на `/admin/leads-log` (см. код страницы и права).

## API (REST v1)

| Модуль | Prefix | Роль |
|--------|--------|------|
| `admin_tasks` | `/admin/tasks` | Список и создание на `(root)`, детали, комментарии, claim, переходы, reorder, bulk status, календарный контекст, приглашения на staff calendar events |
| `admin_task_boards` | `/admin/task-boards` | Колонки доски (`PUT .../columns`) |
| `admin_task_streams` | `/admin/task-streams` | Потоки (PATCH) |
| `admin_task_tags` | `/admin/task-tags` | Теги |

Полная таблица методов: [router_surface/INDEX.md](./router_surface/INDEX.md), разделы 43–46.

## Фронтенд

- Страница: `frontend/src/admin/pages/AdminTasksPage.tsx`.
- Тест UI: `frontend/src/admin/pages/__tests__/AdminTasksPage.test.tsx`.
- Пути: `frontend/src/routePaths.ts` — ключи `tasks`, `leads-log`.

## Метрики

В роутерах: `task_bulk_status_total`, `task_context_admin_events_total` (см. INDEX). Общие HTTP-метрики: `src/main.py`, endpoint `GET /metrics`.

## Тесты (backend)

- `tests/api/test_admin_tasks_rbac.py`
- `tests/api/test_admin_tasks_workflow_and_calendar.py`
- `tests/api/test_admin_tasks_reorder_concurrency.py`
- `tests/api/test_admin_tasks_rate_limit.py`
- `tests/api/test_admin_task_boards.py`
- `tests/api/test_admin_task_streams_and_tags.py`

E2E и фронт: [TESTING_SURFACE.md](./TESTING_SURFACE.md).

---

Reference: [API_V1_ROUTER_MANIFEST.md](./API_V1_ROUTER_MANIFEST.md) · [SCRIBE_ROUTER_CHECKLIST.md](./SCRIBE_ROUTER_CHECKLIST.md)
