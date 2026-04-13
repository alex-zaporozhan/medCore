# Admin Task Detail

## Метаданные

- **Path:** `/admin/tasks/:taskId`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminTaskDetailsPage` (внутри `AdminAuthGuard` → `AdminLayout`, не `AdminShellSegmentPage`)
- **Файл страницы:** `frontend/src/admin/pages/AdminTaskDetailsPage.tsx`
- **Основной контент:** `frontend/src/admin/components/TaskDetailsView.tsx` (`mode="page"`; тот же компонент переиспользуется из Kanban-модалки с `mode="modal"`)

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminTaskDetailsPage.tsx`<br>`frontend/src/admin/components/TaskDetailsView.tsx ← импорт из frontend/src/admin/pages/AdminTaskDetailsPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminTaskDetailsPage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/admin/pages/AdminTaskDetailsPage.tsx` |
| Строк (сумма по фрагментам) | 875 |
| Хуки (эвристика, union) | `useAdminAdmins`, `useAdminSession`, `useAdminTaskDetails`, `useInviteTaskCalendarParticipants`, `usePatchAdminTaskAssigneesMutation`, `usePatchAdminTaskDueMutation`, `usePatchAdminTaskStreamTagsMutation`, `usePostTaskComment`, `useTaskCalendarContext`, `useTaskComments`, `useTaskStreamsQuery`, `useTaskTagsQuery`, `useTaskTransitions`, `useUpdateAdminTaskMetaMutation`, `useUpdateAdminTaskStatusMutation` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Полноэкранный просмотр и правка одной задачи клиники: описание, приоритет/статус, исполнители (при правах), поток и теги, срок, блокировка, комментарии команды, краткая история переходов статусов. Кнопка «Назад к Kanban» ведёт на список досок.

## Логика и данные

- **Хуки (страница):** только маршрутизация и оболочка.
- **Хуки (`TaskDetailsView`):** `useAdminSession`, `useAdminAdmins`, `useTaskStreamsQuery`, `useTaskTagsQuery`, `useAdminTaskDetails` (`useAdminTaskDetails.ts`), `useTaskTransitions`, `useTaskCalendarContext`, `useTaskComments`, `usePostTaskComment`, `usePatchAdminTaskAssigneesMutation`, `usePatchAdminTaskStreamTagsMutation`, `usePatchAdminTaskDueMutation`, `useUpdateAdminTaskMetaMutation`, `useUpdateAdminTaskStatusMutation`, `useInviteTaskCalendarParticipants` (см. ось H / gap).
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/tasks/{taskId}`
  - `GET /v1/admin/tasks/{taskId}/transitions?limit=50`
  - `GET /v1/admin/tasks/{taskId}/calendar-context`
  - `GET /v1/admin/tasks/{taskId}/comments` · `POST /v1/admin/tasks/{taskId}/comments`
  - `PATCH /v1/admin/tasks/{taskId}` — статус (`status`, `transition_reason`), мета (`blocked`, `blocked_reason`, `checklist_done`, `rank`), `assignee_ids`, `due_at`, `stream_id`, `tag_ids`
  - `GET /v1/admin/task-streams` · `GET /v1/admin/task-tags`
  - `GET /v1/admin/admins` (справочник для исполнителей и ссылок `PersonNameLink`)

## RBAC / entitlements / edition

- **fact:** Доступ к маршруту — общий контур админки (`AdminAuthGuard` + layout); отдельного ключа `adminShellSegmentEntitlementKey` для `/admin/tasks/:id` нет (в отличие от shell-сегментов).
- **fact (из `TaskDetailsView`):** гранулярные флаги по `adminSession.permissions`:
  - исполнители: `manage_tasks` или `assign_tasks`
  - поток/теги: `manage_tasks`
  - поля статуса/блокировки и часть сценариев: `manage_tasks` || `assign_tasks` || `tasks.change_status`
  - срок: `manage_tasks` или автор задачи (`task.creator_id === currentAdminId`)
- **edition:** не задействовано на этом экране (as-built).

## UI-скелет (as-built)

- `ContextBar` («Задача», действие «Назад к Kanban»).
- `TaskDetailsView`: верх — бейджи приоритета/статуса/блокировки; `Paper` с описанием и мета (срок, исполнители для read-only).
- `SimpleGrid` (2 колонки на md): слева карточки «Исполнители», «Поток и теги» (условно); справа «Срок выполнения» (Select статуса + date/time), «Статус и блокировка» (быстрые кнопки статуса, textarea причины, toggle блокировки, кнопка «Закрыть» только если передан `onClose` — на странице обычно скрыта).
- Ниже на всю ширину: карточка «Комментарии» (`ScrollArea` + `AppleEmojiOverlayTextarea`), карточка «История статусов» (до 20 записей).

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer / GlassModal:** нет (as-built).
- **Mantine `Modal` / `Menu`:** нет.
- **`Alert`:** ошибка загрузки задачи; опционально верхний баннер при `apiError` после мутаций (**fact:** текст из `ApiErrorWithCode.message` или запасные строки).
- **`Loader`:** загрузка задачи и списка комментариев.
- **gap:** `useInviteTaskCalendarParticipants(taskId, null)` вызывается, но возвращаемое значение мутации не используется — приглашение участников в календарное событие задачи с этой страницы в UI не подключено (`eventId` всегда `null`).

## Целевой UX (target vs as-built)

- *target:* единый паттерн деталей сущности (читаемый скелет, явные состояния загрузки/ошибки, предсказуемые права на поля).
- *as-built:* полнофункциональная форма в одном скролле; эмодзи в комментариях через общие компоненты; календарный invite — мёртвый хук (см. gap).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** выделенных vitest/e2e под эту страницу в репозитории не найдено (поиск по именам страницы/компонента).

## Gap scan (вторая редакция)

- Календарный invite: хук без UI и с `eventId=null` — либо удалить мёртвый вызов, либо связать с реальным событием из `calendar-context`.
- Нет `AdminDrawer` для связанных сущностей (пациент/лид и т.д.) — при расширении продукта стоит явно решить, нужен ли drawer.
