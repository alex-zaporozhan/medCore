# Admin Leads Log

## Метаданные

- **Path:** `/admin/leads-log`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminLeadsLogPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminLeadsLogPage.tsx` (тонкая обёртка)
- **Фактическая реализация:** `AdminTasksPage` с `mode="leads-log"`, `forcedStreamSlug="leads-log"`, `titleOverride="Лиды (лог)"`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminLeadsLogPage.tsx`<br>`frontend/src/admin/pages/AdminTasksPage.tsx ← импорт из frontend/src/admin/pages/AdminLeadsLogPage.tsx` |
| Строк (сумма по фрагментам) | 3557 |
| Хуки (эвристика, union) | `useAdminAdmins`, `useAdminClinic`, `useAdminLeadLogDetail`, `useAdminLeadLogRoutingRules`, `useAdminSession`, `useAdminTasksList`, `useAdminTasksMyFocus`, `useClaimAdminTaskMutation`, `useCreateAdminTaskMutation`, `useCreateTaskStreamMutation`, `useCreateTaskTagMutation`, `useDebouncedValue`, `useDraggable`, `useDroppable`, `usePatchAdminTaskStreamTagsMutation`, `usePatchTaskStreamMutation`, `usePatients`, `usePostTaskComment`, `useReorderAdminTasksMutation`, `useReplaceAdminLeadLogRoutingRulesMutation`, `useReplaceTaskBoardColumnsMutation`, `useSensor`, `useSensors`, `useSimulateAdminLeadLogRoutingMutation`, `useTaskBoardsQuery`, `useTaskComments`, `useTaskStreamsQuery`, `useTaskTagsQuery`, `useTaskWipPolicies`, `useUpdateAdminTaskStatusMutation` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 19, Modal: 0, Menu: 36 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Тот же каркас, что и раздел задач, но зафиксированный на потоке **`leads-log`**: просмотр и работа с задачами/лидами за выбранный **день завершения** (`completedDayIso`), заголовок контекста «Лиды (лог)», без переключателя потоков (pager отключён при `forcedStreamSlug`). В детальной модалке при связи с логом подгружается **`useAdminLeadLogDetail`** по `trace_id` задачи; доступно управление правилами маршрутизации лидов (модалка + API).

## Логика и данные

- **Общее с Kanban:** см. **`admin-tasks.md`** — список задач через `useAdminTasksList` с параметрами `completed_from` / `completed_to` на выбранный день (UTC-границы в коде), потоки/теги, модалки `GlassModal`, `TaskDetailsView`, комментарии и т.д.
- **Специфика leads-log:**
  - `useAdminLeadLogDetail(logId)` при `mode === "leads-log"` и извлечённом id из `trace_id` задачи.
  - `useAdminLeadLogRoutingRules`, `useSimulateAdminLeadLogRoutingMutation`, `useReplaceAdminLeadLogRoutingRulesMutation`.
- **Типовые API (дополнительно к задачам):**
  - `GET /v1/admin/lead-logs/{logId}`
  - `GET /v1/admin/leads-log/routing-rules`
  - `POST /v1/admin/leads-log/routing-rules/simulate`
  - `PUT /v1/admin/leads-log/routing-rules` (тело `{ rules }`)

## RBAC / entitlements / edition

- **fact:** Сегмент `leads-log` **не** отдельно перечислен в `SEGMENT_ENTITLEMENT` — ключ SaaS как у соседних пунктов без маппинга не навешивается из `adminShellSegmentEntitlementKey`.
- **fact:** `leads.log.manage` в `useAdminSession` — флаг для сценариев управления маршрутизацией (as-built в `AdminTasksPage`).

## UI-скелет (as-built)

- Полностью наследуется от `AdminTasksPage` с перечисленными props: заголовок, фильтр по дню завершения, Kanban/модалки того же файла.

### Evidence / QA (скриншоты)

- URL **`/admin/leads-log`**, заголовок **«Лиды (лог)»**; панель фильтров с днём (**«День …»**), исполнителем, сроками и **«Фильтры»**.
- Секция **«Аудит перемещений»** в пустой сессии: текст вроде **«Пока нет перемещений в этой сессии»** — ожидаемо до действий с лидами/задачами за выбранный контекст.

## Инвентарь поверхностей UI (ось H)

- **Идентично по паттернам `admin-tasks`:** множество **`GlassModal`**, детали через **`TaskDetailsView`** в модалке, без **`AdminDrawer`** на корневом уровне страницы.
- **Дополнительно:** блок деталей лида (контакт, исход, ссылка на omni-chat, транскрипт) внутри модалки детализации; отдельная модалка настройки **`routingDraft`** / simulate / save.

## Целевой UX (target vs as-built)

- *target:* оператор видит закрытые лиды за день и может корректировать маршрутизацию.
- *as-built:* смешение с полным task UI — осознанный компромисс по коду (один компонент, два режима).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** тестов обёртки и режима `leads-log` не найдено.

## Gap scan (вторая редакция)

- Дублирование ответственности с `admin-tasks` усложняет паспортизацию — при рефакторинге вынести leads-log в подкомпоненты или отдельный файл с общим ядром.
