# ARCH_PHASE_01_STAFF_CORE_2026 — фаза 1 (роль @ARCH)

> **Ссылка:** `MASTER_PRODUCT_ROADMAP_2026.md` § фаза 1.

## 1. Цель

Внутренний контур сотрудника: лента (вместо/слияние с attention), мессенджер персонала, календарь с совещаниями, Kanban с чатом задачи, база знаний с изоляцией по роли.

## 2. Границы контекста

**Отдельно от** омниканала с клиентом: другие сущности сообщений/комнат; не смешивать потоки в одной таблице без дискриминатора типа чата.

## 3. Данные

- Посты/комментарии/вложения: `clinic_id` + автор + политика публикации (настройки владельца).
- Staff chat: `conversation` тип `STAFF` | `STAFF_GROUP`; сообщения с вложениями — лимиты размера, антивирус/политика — позже.
- Календарь: события, участники, напоминания (Celery/cron).
- Задачи: расширение существующей модели — колонки, много исполнителей, чат задачи, связь с календарём.
- База знаний: папки, документы, **видимость по роли/категории персонала**.

## 4. Мультитенантность

Все сущности фазы — строго по `clinic_id`; группы персонала не пересекают клиники.

## 5. Безопасность

RBAC: мастер не видит внутренние чаты владельца, если не участник; политика «кто может постить в ленту».

## 6. UI

Центрированные модалки для создания событий/задач; все подписи RU (`ARCH_CROSS_CUTTING_UI_I18N_2026.md`). Уведомления: три канала звука (продуктовое требование).

## 7. Риски

Раздувание scope ленты до «полного Facebook» — держать MVP: пост, комментарий, вложение, политика.

## 8. Зависимости

Фаза 0 (стабильный CI и tenant).

## 9. Статус реализации (коробка, 2026-03)

| Тема | Сделано в коде |
|------|----------------|
| Лента `/admin` | KPI (выручка, новые пациенты, отмены/неявки) **без** карточки «записи на сегодня»; блоки «Посты команды» и «Лента внимания» на одной странице; маршрут `/admin/attention` редиректит на `/admin`. |
| RBAC ленты | Посты/комментарии staff feed: `manage_staff_collab`; просмотр: `view_staff_collab`. UI: кнопка «Новый пост» по `GET /v1/admin/auth/session`. |
| Мессенджер персонала | Комнаты/сообщения строго по `clinic_id` и участникам клиники; эндпоинты под `require_permissions` (см. `admin_staff_collab.py`). |
| Календарь | CRUD событий, напоминания (Celery); связь с задачей: `task_id` в create и PATCH (`StaffCalendarEventUpdate`). UI: создание и **редактирование** (в т.ч. участники и `task_id`), кнопка «Изменить» на карточке. Участники: `staff_calendar_event_participants`, право `invite_staff_calendar_participants`. |
| Kanban / задачи | Колонки open / in progress / done, drag; чат задачи; отображение `role_assignee`; ссылка «Календарь» с `task_id`. UI: несколько исполнителей в форме создания (MultiSelect). |
| База знаний | Документы с `folder_key` (папки в UI), `visible_roles` при создании/редактировании. |
| Несколько исполнителей | Таблица `task_assignees` + поле `assignee_ids` в API; legacy `assignee_id` синхронизируется; очередь по роли — `role_assignee` без личных исполнителей. |

## 10. Ссылки на реализацию в репозитории (зафиксировано)

| Тема | Где в коде |
|------|------------|
| Staff collab (лента, чат, календарь, KB) | `src/api/v1/routers/admin_staff_collab.py`; сервис `src/application/services/staff_collaboration_service.py` |
| Календарь: участники, PATCH, `task_id` | DTO `StaffCalendarEventCreate` / `StaffCalendarEventUpdate` в `src/application/dto/staff_collab_dto.py`; право `invite_staff_calendar_participants` в `src/application/rbac_matrix.py` |
| Задачи: мульти-исполнители | `task_assignees`, `TaskService` / `admin_tasks.py`; `staff_collaboration_service` — участники комнаты чата задачи |
| Frontend: лента, задачи, календарь, настройки-хаб | `AdminDashboardPage.tsx`, `AdminTasksPage.tsx`, `AdminStaffCalendarPage.tsx`, `AdminLayout.tsx` (сайдбар), `AdminSettingsPage.tsx` (ссылки на разделы без дубля в меню) |
| RBAC сессии для UI | `GET /v1/admin/auth/session`, `frontend/src/hooks/useAdminSession.ts` |

**Вне P1 (отдельные треки):** консолидация **двух** страниц «каналы» (`/admin/channels` vs `/admin/omni-channels`) в один продуктовый UX — в бэклоге по `MASTER` §4; в хабе «Настройки» обе ссылки доступны. Enterprise: сеть салонов и staff chat — см. `docs/architecture/STAFF_CHAT_MULTITENANCY.md`, `ENTERPRISE_STAFF_NETWORK_AND_CHAT_2026.md`.

## История

| Дата | Изменение |
|------|-----------|
| 2026-03-24 | §10: ссылки на код; уточнение Kanban UI; примечание про каналы и Enterprise staff chat |
| 2026-03-24 | §9: статус реализации P1 |
| 2026-03-24 | Первая версия документа фазы |
