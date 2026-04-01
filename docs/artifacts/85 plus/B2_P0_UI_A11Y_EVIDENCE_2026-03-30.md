# B2_P0_UI_A11Y_EVIDENCE_2026-03-30

> Цель: закрыть evidence-часть B2 (`DGN-P0-01..05`) для LEAD/QA/Design review.

## DGN-P0-01 Header contract

- `ContextBar` применяется на admin pages (P0 и смежные экраны).
- Проверено, что локальные альтернативы header pattern не используются в P0-контуре.

## DGN-P0-02 Table/state canonicalization

- `AdminBookingsPage`, `AdminPatientsPage`, `AdminReportsPage` приведены к `AdminDataTableToolbar` / `AdminDataTableSurface` и `ADMIN_TABLE_PROPS`.
- `AdminTasksPage` сохранен как kanban-first UX, но его служебные surface-блоки выровнены под `AdminDataTableSurface`.
- Для строгой формулировки "один table pattern" нужен финальный waiver @DESIGN на kanban nature tasks.

## DGN-P0-03 Entity drawer standard

- `BookingEntityDrawer`, `PatientEntityDrawer`, `DoctorEntityDrawer`, `ServiceEntityDrawer` используют shared chrome:
  - `EntityDrawerFieldBlock`
  - `EntityDrawerFooterBar`

## DGN-P0-04 Severity semantics

- `SEMANTIC.opsSeverity` применяется на ops-экранах:
  - `AdminTasksPage`
  - `AdminOmniChatPage`
  - `AdminEmergencyNotificationsPage`

## DGN-P0-05 Accessibility safety net (spot-check)

Checklist (manual spot):

- [x] Drawer close control имеет aria-label (`AdminDrawer` default close aria).
- [x] Chat message area имеет landmark region (`ADMIN_CHAT_MESSAGES_REGION`).
- [x] Критичные действия в чатах имеют aria-label (`Удалить сообщение`).
- [x] Обновление PWA показывается в доступном `Alert` с явной CTA-кнопкой.
- [x] Focus-visible не теряется при переходе по основным action-кнопкам (spot on P0 pages).

## Локальное тех-доказательство

- `npm run build` (frontend): PASS.
- Lints на измененных P0/P1 файлах: no new issues.

## Решение для B2

- Dev-часть B2 закрыта.
- Для полного governance DoD остается формальный sign-off:
  1) @DESIGN waiver по kanban tasks,
  2) @QA_ARCH визуальный пакет скринов before/after.
