# DESIGN_P0_P1_BACKLOG

## P0 (release-facing, mandatory)

### DGN-P0-01 — Unified Admin Header Contract
- **Scope:** все admin pages.
- **Task:** перевести заголовки страниц на `ContextBar` контракт с единым sticky поведением.
- **Acceptance:** нет локальных альтернатив page-header pattern.
- **Owner:** DESIGN + DEV FE.

### DGN-P0-02 — Data Table Canonicalization
- **Scope:** `AdminTasksPage`, `AdminReportsPage`, `AdminPatientsPage`, `AdminBookingsPage`.
- **Task:** унифицировать toolbar, row density, empty/loading/error states.
- **Acceptance:** все 4 экрана используют один table pattern.
- **Owner:** DESIGN + DEV FE.

### DGN-P0-03 — Entity Drawer Standard
- **Scope:** `BookingEntityDrawer`, `PatientEntityDrawer`, `DoctorEntityDrawer`, `ServiceEntityDrawer`.
- **Task:** единая структура секций, действий и status-badges.
- **Acceptance:** 4 drawer-компонента соответствуют shared contract.
- **Owner:** DESIGN + DEV FE.

### DGN-P0-04 — Severity Semantics in Ops Screens
- **Scope:** `AdminTasksPage`, `AdminOmniChatPage`, `AdminEmergencyNotificationsPage`.
- **Task:** выровнять `critical/warning/info` визуальную модель.
- **Acceptance:** severity semantics совпадают между модулями.
- **Owner:** DESIGN + QA_ARCH.

### DGN-P0-05 — Accessibility Safety Net
- **Scope:** все P0-экраны.
- **Task:** keyboard path + focus visibility + contrast quick audit.
- **Acceptance:** минимальный WCAG 2.1 AA check evidence приложен.
- **Owner:** DESIGN + QA.

---

## P1 (next cycle, productivity and consistency)

### DGN-P1-01 — CRM/Pipeline Visual Standard
- **Scope:** `AdminSalesPipelinePage`, `AdminMarketingPage`, `AdminRetentionPage`.
- **Task:** унифицировать card hierarchy, stage visuals, filter rhythm.
- **Acceptance:** единый pipeline + analytics визуальный контракт.

### DGN-P1-02 — Settings Form Contract
- **Scope:** `AdminSettingsPage`, `AdminIntegrationsPage`, `AdminPaymentGatewayPage`, `AdminAiSettingsPage`, `AdminOmniAiSettingsPage`.
- **Task:** единый form layout, helper/error feedback, action footer.
- **Acceptance:** consistency по spacing, controls и state model.

### DGN-P1-03 — Omni and Chat Convergence
- **Scope:** `AdminOmniChatPage`, `AdminChatPage`, `AdminStaffChatPage`, app `ChatPage`.
- **Task:** единый pattern для message blocks, metadata, escalation actions.
- **Acceptance:** chat surfaces следуют единой token/state модели.

### DGN-P1-04 — Finance/Reports Numeric Readability
- **Scope:** `AdminFinancePage`, `AdminReportsPage`, `AdminAiReportsPage`.
- **Task:** стандартизировать numeric typography, summary cards и table scanning.
- **Acceptance:** consistent tabular numeric presentation.

### DGN-P1-05 — Box/Enterprise UX Integrity
- **Scope:** edition-sensitive admin pages.
- **Task:** убрать dead links и недоопределённые lock states в Box.
- **Acceptance:** для ограниченных функций есть явное UX-объяснение, без ложных affordances.

---

## Delivery discipline

- Каждый пункт должен иметь:
  - ссылку на дизайн-макет/спеку,
  - ссылку на PR/реализацию,
  - QA evidence (скрин + сценарий),
  - итоговый статус `done/partial/block`.
