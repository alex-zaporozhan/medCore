# Admin Tasks

## Метаданные

- **Path:** `/admin/tasks`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminTasksPage` (режим по умолчанию `mode="tasks"`)
- **Файл страницы:** `frontend/src/admin/pages/AdminTasksPage.tsx` (~3500 строк)

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminTasksPage.tsx`<br>`frontend/src/shared/AppleEmojiRichText.tsx ← импорт из frontend/src/admin/pages/AdminTasksPage.tsx`<br>`frontend/src/admin/components/TaskDetailsView.tsx ← импорт из frontend/src/admin/pages/AdminTasksPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminTasksPage.tsx`<br>… +7 файлов |
| Строк (сумма по фрагментам) | 5300 |
| Хуки (эвристика, union) | `useAdminAdmins`, `useAdminClinic`, `useAdminLeadLogDetail`, `useAdminLeadLogRoutingRules`, `useAdminSession`, `useAdminTaskDetails`, `useAdminTasksList`, `useAdminTasksMyFocus`, `useBusinessLexicon`, `useClaimAdminTaskMutation`, `useClinics`, `useCreateAdminTaskMutation`, `useCreateTaskStreamMutation`, `useCreateTaskTagMutation`, `useDebouncedValue`, `useDraggable`, `useDroppable`, `useInviteTaskCalendarParticipants`, `usePatchAdminTaskAssigneesMutation`, `usePatchAdminTaskDueMutation`, `usePatchAdminTaskStreamTagsMutation`, `usePatchTaskStreamMutation`, `usePatient`, `usePatients`, `usePostTaskComment`, `useQuery`, `useReorderAdminTasksMutation`, `useReplaceAdminLeadLogRoutingRulesMutation`, `useReplaceTaskBoardColumnsMutation`, `useSensor`, `useSensors`, `useSimulateAdminLeadLogRoutingMutation`, `useTaskBoardsQuery`, `useTaskCalendarContext`, `useTaskComments`, `useTaskStreamsQuery`, `useTaskTagsQuery`, `useTaskTransitions`, `useTaskWipPolicies`, `useUpdateAdminTaskMetaMutation`, `useUpdateAdminTaskStatusMutation` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 19, Modal: 0, Menu: 36 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Kanban/операционная доска задач клиники: потоки (`task-streams`), колонки статусов и досок, карточки задач с DnD (`@dnd-kit`), фильтры, массовые операции, чат по задаче, создание задачи, настройка досок/колонок/тем потоков/тегов, детальный просмотр в модалке (`TaskDetailsView`), ссылка в staff-chat и полноэкранная страница задачи.

## Логика и данные

- **Хуки (выборочно):** `useAdminSession`, `useAdminClinic`, `useTaskStreamsQuery`, `useTaskTagsQuery`, `useTaskBoardsQuery`, `useAdminTasksList`, `useAdminTasksMyFocus`, `useAdminAdmins`, `usePatients`, мутации задач (`useCreateAdminTaskMutation`, `useClaimAdminTaskMutation`, `useUpdateAdminTaskStatusMutation`, `useReorderAdminTasksMutation`, `useBulkUpdateAdminTaskStatusMutation`, `usePatchAdminTaskStreamTagsMutation`, …), комментарии (`useTaskComments`, `usePostTaskComment`), доски (`useReplaceTaskBoardColumnsMutation`, `useCreatePersonalTaskBoardMutation`), потоки/теги (`useCreateTaskStreamMutation`, `usePatchTaskStreamMutation`, `useCreateTaskTagMutation`), WIP (`useTaskWipPolicies`), и др. из `@/hooks` / `useAdminTasks.ts`.
- **Типовые API:** семейство `/v1/admin/tasks`, `/v1/admin/tasks/reorder`, `/v1/admin/tasks/bulk/status`, `/v1/admin/task-boards`, `/v1/admin/task-streams`, `/v1/admin/task-tags`, плюс комментарии/переходы (см. `admin-task-detail.md` и `useAdminTasks.ts`).

## RBAC / entitlements / edition

- **fact:** В `SEGMENT_ENTITLEMENT` для сегмента `tasks` задан ключ **`tasks.kanban`** — при `entitlement_enforced` и отсутствии ключа в сессии сегмент блокируется (`adminShellSegmentEntitlementKey`, `isAdminSegmentBlockedByEntitlements`).
- **fact:** Внутри UI — `manage_tasks`, `assign_tasks`, `tasks.change_status` и др. по месту (см. `TaskDetailsView` и условия на кнопках Kanban).

## UI-скелет (as-built)

- `ContextBar` с переключением потоков (стрелки / меню), фильтрами, кнопками создания и настроек.
- Область Kanban: колонки статусов, карточки `TaskKanbanCard`, DnD, боковые/нижние панели по сценарию.
- Множество вспомогательных блоков: focus, bulk, audit trail (локальный стейт), AI-маркеры и т.д. по коду.

### Stream switcher (одна доска)

На экране монтируется **один** `TasksKanbanPage` для `selectedStreamId` (`?stream=` / localStorage). Соседние потоки не рендерятся слайдами: HTML `inert` на соседней копии доски глотал клики по видимой доске («картинка»).

- Стрелки `<` `>` , точки и меню `stream-switcher` меняют `selectedStreamId`.
- Клик по карточке открывает `GlassModal` + `TaskDetailsView`. Карточка — не `role="button"` (внутри чекбокс/меню/ссылка). Заголовок — `UnstyledButton`.
- `useDraggable` только у карточек на доске; очередь согласования не вызывает хук вне контекста.
- Один `DndContext` на страницу потока: шапка потока (`stream-page-*`) — реальный droppable. Края `nav-prev` / `nav-next` принимают pointer только во время драга; drop на край сразу переключает поток.

### Evidence / QA (скриншоты)

- URL **`/admin/tasks`** (в примере query **`?stream=<uuid>`** — выбранный поток). Chrome (заголовок, **New task**, фильтры) — ns `tasks`, default EN; имена потоков — данные API.
- Верхние зоны: **All streams**, очередь **Needs approval** (пусто / счётчик), **Task list** / **Assigned to me** — ключи `tasks`.
- Колонки Kanban: подписи статусов через `taskStatusLabel` / `tasks.status.*` (если у доски нет своего `label`); метрики WIP/SLA — `tasks.wip.*`. Кастомный `column.label` с бэкенда остаётся как данные.
- Модалка создания: ключи `createForm.*` / `priority.*` / `streams.one`.
- Модалка деталей: живой UI — `TaskDetailsView` (`mode="modal"`), не мёртвый JSX в комментарии.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer на странице:** нет (детали задачи — через **`GlassModal`** + `TaskDetailsView` в `mode="modal"`).
- **Много `GlassModal`:** создание задачи, детали (`TaskDetailsView`), чат по задаче, настройки колонок досок, выбор доски, новый поток, тема потока, новый тег, bulk-операции, модалка маршрутизации лидов (см. ниже) и др. (**fact:** точный список триггеров — по поиску `GlassModal` / `opened` в файле).
- **`Menu`, `Alert`, `Tooltip`, `Modal` (Mantine):** используются точечно в Kanban и формах.
- **Связанный экран:** `/admin/tasks/:taskId` — полная страница (см. `admin-task-detail.md`).

## Целевой UX (target vs as-built)

- *target:* единая операционная доска с прозрачными правами и быстрым drill-down.
- *as-built:* очень насыщенный монолитный компонент; высокая когнитивная нагрузка, компенсируемая богатством сценариев.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- `frontend/src/admin/pages/__tests__/AdminTasksPage.test.tsx` — chrome, очередь, DnD, клик по карточке открывает dialog, одна доска на выбранный поток, drop на `stream-page-*` и на край `nav-next`.
- `frontend/src/admin/pages/__tests__/AdminTaskDetailsPage.test.tsx` (chrome полноэкранной страницы).

## Gap scan (вторая редакция)

- Декомпозиция файла на подкомпоненты и сценарные e2e снизят стоимость изменений.
- Модалка маршрутизации лидов (`routingModalOpened`) живёт в том же файле, что и Kanban — при развитии leads-log стоит явно разнести контуры.
