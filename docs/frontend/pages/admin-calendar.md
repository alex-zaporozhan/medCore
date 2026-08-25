# Admin Calendar

## Метаданные

- **Path:** `/admin/calendar` (+ query: `?task_id=…&open_create=1` для префилла из задачи)
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminStaffCalendarPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminStaffCalendarPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminStaffCalendarPage.tsx`<br>`frontend/src/hooks/useStaffCollab.ts ← импорт из frontend/src/admin/pages/AdminStaffCalendarPage.tsx`<br>`frontend/src/hooks/useAdminTaskDetails.ts ← импорт из frontend/src/admin/pages/AdminStaffCalendarPage.tsx`<br>`frontend/src/hooks/useAdminTasks.ts ← импорт из frontend/src/admin/pages/AdminStaffCalendarPage.tsx`<br>… +1 файлов |
| Строк (сумма по фрагментам) | 3631 |
| Хуки (эвристика, union) (показаны первые 60 из 70) | `useAckStaffCalendarInvitation`, `useAckStaffFeedPost`, `useAddStaffFeedComment`, `useAdminAdmins`, `useAdminSession`, `useAdminTaskDetails`, `useAdminTasks`, `useAdminTasksAi`, `useAdminTasksList`, `useAdminTasksMyFocus`, `useAdminTasksOpen`, `useBulkUpdateAdminTaskStatusMutation`, `useClaimAdminTaskMutation`, `useCreateAdminTaskMutation`, `useCreateKnowledgeDocument`, `useCreatePersonalTaskBoardMutation`, `useCreateStaffCalendarEvent`, `useCreateStaffDmRoom`, `useCreateStaffFeedPost`, `useCreateStaffGroupRoom`, `useCreateTaskStreamMutation`, `useCreateTaskTagMutation`, `useDeleteStaffFeedComment`, `useDeleteStaffFeedPost`, `useInviteStaffRoomMember`, `useInviteTaskCalendarParticipants`, `useKnowledgeDocuments`, `useMarkStaffChatRoomRead`, `useMutation`, `usePatchAdminTaskAssigneesMutation`, `usePatchAdminTaskDueMutation`, `usePatchAdminTaskStreamTagsMutation`, `usePatchTaskStreamMutation`, `usePostStaffChatMessage`, `usePostTaskComment`, `useQuery`, `useQueryClient`, `useReorderAdminTasksMutation`, `useReplaceTaskBoardColumnsMutation`, `useStaffAnnouncementPublishPolicy`, `useStaffAnnouncementPublishPolicyAudit`, `useStaffAnnouncements`, `useStaffCalendarEventDetails`, `useStaffCalendarEvents`, `useStaffCalendarMonthGrid`, `useStaffChatMessages`, `useStaffChatRooms`, `useStaffCollab`, `useStaffFeedComments`, `useStaffFeedPostAckStatus`, `useStaffFeedPosts`, `useStaffTaskChatRoom`, `useTaskBoardsQuery`, `useTaskCalendarContext`, `useTaskComments`, `useTaskStreamsQuery`, `useTaskTagsQuery`, `useTaskTransitions`, `useTaskWipPolicies`, `useToggleStaffFeedPostLike` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/admin/task-boards`, `/v1/admin/task-streams`, `/v1/admin/task-tags`, `/v1/admin/tasks`, `/v1/admin/tasks/bulk/status`, `/v1/admin/tasks/reorder`, `/v1/admin/tasks/wip-policies`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 4, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Календарь персонала клиники на месяц: сетка дней, события/напоминания, визуальное выделение непросмотренных приглашений и напоминаний, опциональный звук, создание и редактирование событий, просмотр деталей, подтверждение приглашений (`ack`), выбор участников среди активных админов. Поддержка deep-link из задачи для открытия формы создания с контекстом.

## Логика и данные

- **Хуки:** `useStaffCalendarMonthGrid`, `useCreateStaffCalendarEvent`, `useUpdateStaffCalendarEvent`, `useStaffCalendarEventDetails`, `useAckStaffCalendarInvitation`, `useAdminSession`, `useAdminAdmins`, при deep-link — `useAdminTaskDetails`, `useAdminTasksList` / `useAdminTasksMyFocus` / `useAdminTasksOpen` (подбор задач для UI).
- **Границы месяца:** локальные `YYYY-MM-DDTHH:mm:ss` без сдвига UTC (комментарий в коде).
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/staff/calendar/month?from=…&to=…`
  - `GET /v1/admin/staff/calendar/events?…` (при необходимости списков)
  - `GET /v1/admin/staff/calendar/events/{eventId}`
  - `POST /v1/admin/staff/calendar/events`
  - `PATCH /v1/admin/staff/calendar/events/{eventId}` (в т.ч. замена `participant_admin_ids` целиком)
  - `POST /v1/admin/staff/calendar/events/{eventId}/invitations/ack`
  - `GET /v1/admin/tasks/{taskId}` (deep-link)
- **Локальное хранилище:** `staff_cal_sound_enabled` в `localStorage` для переключателя звука.

## RBAC / entitlements / edition

- **fact:** Сегмент `calendar` отсутствует в `SEGMENT_ENTITLEMENT` — отдельного SaaS-ключа в `adminShellSegmentEntitlementKey` нет.
- **fact (permissions):** `invite_staff_calendar_participants`, `manage_staff_collab`, `view_tasks` — управляют приглашениями участников, редактированием календаря и видимостью контекста задач соответственно (`useAdminSession`).

## UI-скелет (as-built)

- `ContextBar`, переключатель месяца (`CompactMonthPicker`), индикаторы напоминаний/непрочитанного, переключатель звука.
- Табличная/сеточная разметка недель (Пн–Вс), клики по дню открывают обзор дня.
- Чипы событий с палитрой `--staff-cal-*` из `index.css` (LEAD-комментарий в коде).

### Evidence / QA (скриншоты)

- URL **`/admin/calendar`**. В `ContextBar` техническое пояснение: совещания и напоминания (в т.ч. фоновая доставка через **Celery**), связь с задачей Kanban, приглашение нескольких участников (типично руководитель/старший админ), сохранение правок через **PATCH**; индикатор **«Звук: включён»** / выкл.
- Навигация: **«Сегодня»**, стрелки месяца, кнопка **«Новое событие»**; на сетке — чипы времени и названий, метка **«нов»** для непросмотренного.
- Модалка **«События {дата}»**: **«Быстрое действие»** → **«+ Добавить событие»**; для дня без событий — текст пустого состояния и блок **«Быстрый выбор часа»** (сетка слотов 00:00–22:00).
- Модалка **«Новое событие»**: **Заголовок**, **Описание**, **Участники совещания** (мультивыбор админов), **Весь день**, **Напоминание** (напр. «За 15 минут»), дата/время начала-конца, календарь в правой колонке, кнопка **«Связать с задачей»**, **«Отмена»** / **«Создать»**; у приглашённого события бейдж **«Новое для меня»**.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer / GlassModal:** нет.
- **Mantine `Modal`:** несколько экземпляров (обзор дня — стейт `dayDrawerDate`, несмотря на имя; create/edit/details; связь с задачей). Все разносят `CALENDAR_MODAL_NAV_SAFE`: `lockScroll: false`, overlay/inner с `left: var(--app-shell-navbar-offset)` и `inner.width: auto` + `justify-content: center` (не `paddingLeft` на full-viewport inner — иначе широкая EN-форма прилипает к сайдбару). Create/edit `size="56rem"`.
- Deep-link `open_create=1` снимается через `setSearchParams(..., { replace: true })`, без лишнего шага в history (Back не открывает форму снова).
- **Состояния:** `create` | `edit` | `details` с общим `submitModal` / `closeModal`; submit no-op при `isPending`; пересечение интервалов — предупреждение в форме + отказ save + `pg_advisory_xact_lock` на клинику перед count в `_assert_calendar_event_no_overlap`.
- **`Loader` / `PageSkeleton` / `EmptyState`:** по месту загрузки сетки и пустых состояний.

## Целевой UX (target vs as-built)

- *target:* командный календарь с явными приглашениями и напоминаниями, без лишнего шума.
- *as-built:* богатый интерактив (звук, flash, несколько модалок); крупный файл — высокая связность состояния.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- `frontend/src/admin/pages/__tests__/AdminStaffCalendarPage.test.tsx` — EN chrome, ввод времени, `document.body` без `pointer-events: none` при открытой форме; inner модалки с inset `left` (не `paddingLeft`) и `justify-content: center`.
- `frontend/src/shared/ui/__tests__/shellPanelStyles.test.ts` — `ADMIN_NAV_SAFE_MODAL_PROPS`, overlay inset, `SHELL_MODAL_NAV_INNER_STYLE` (без `paddingLeft`).

## Gap scan (вторая редакция)

- Переменная `dayDrawerDate` открывает **Modal**, не drawer — при унификации админских панелей возможен рефактор на `AdminDrawer`.
- Сложность файла (~1800+ строк) — кандидат на декомпозицию и/или e2e на happy-path (создать событие, ack приглашение).
