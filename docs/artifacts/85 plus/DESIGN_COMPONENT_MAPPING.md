# DESIGN_COMPONENT_MAPPING

## Цель

Свести все текущие UI-паттерны к каноническим компонентам, чтобы убрать style drift и ускорить внедрение 85+ концепции.

---

## 1) Shell and page structure

| Current | Canonical | Rule |
|--------|-----------|------|
| Локальные заголовки страниц | `ContextBar` | Все admin pages используют единый sticky header pattern |
| Разрозненные top action rows | `ContextBar.actions` | Единая зона действий справа, без ad-hoc гридов |
| Локальные page wrappers | `AdminLayout` contracts | Запрет на локальные layout fork внутри страниц |

---

## 2) Overlays and entity details

| Current | Canonical | Rule |
|--------|-----------|------|
| `GlassModal` + локальные стили | `GlassModal` через `mergeModalStyles` + token contract | Один стиль entrypoint для modal surfaces |
| Разные `Drawer` реализации | `AdminDrawer` + `mergeDrawerStyles` | Единый header/body/footer/action контракт |
| `BookingEntityDrawer`/`PatientEntityDrawer`/`DoctorEntityDrawer`/`ServiceEntityDrawer` | Entity Drawer Standard v1 | Структура: summary -> sections -> actions |

---

## 3) Data-heavy components

| Current | Canonical | Rule |
|--------|-----------|------|
| Разные toolbar над таблицами | Data Table Toolbar v1 | Фильтры/поиск/действия в фиксированном порядке |
| Разные состояния пустых таблиц | Empty State Pattern v1 | Заголовок + причина + CTA |
| Разные loading placeholders | Skeleton Standard v1 | Унифицированный размер/плотность скелетонов |
| Разные error блоки | Inline Error Block v1 | Один визуальный паттерн + retry |

---

## 4) Forms and controls

| Current | Canonical | Rule |
|--------|-----------|------|
| Локальные вариации spacing у форм | Form Section Contract v1 | Единая вертикальная ритмика блоков |
| Разные helper/error states | Field Feedback Pattern v1 | Helper -> Error priority and color tokens |
| Разные confirm/cancel зоны | Action Footer Pattern v1 | Primary right, secondary left, danger isolated |

---

## 5) Status and semantic visuals

| Current | Canonical | Rule |
|--------|-----------|------|
| Локальные цвета статусов | Semantic Token Map | Только role-based tokens (`success/warning/danger/info/ai`) |
| Нестабильные badges | Badge Standard v1 | Filled/light variants строго по status semantics |
| Разные severity в omni/tasks | Severity Visual Contract | `critical/warning/info` единообразно по всем модулям |

---

## 6) Immediate migration order

P0 migration order:
1. Shell headers -> `ContextBar`.
2. Drawers/modals -> shared styles contract.
3. Tables in `AdminTasksPage`, `AdminReportsPage`, `AdminPatientsPage`, `AdminBookingsPage`.

P1 migration order:
1. CRM/pipeline card standards.
2. Omni/chat severity and action hierarchy.
3. Settings/forms standardization.

P2 migration order:
1. Patient-app visual alignment with shared tokens.
2. Legacy local CSS cleanup.

---

## 7) B1 token mapping for P0 contours (current -> target)

### Tables

| Current token/value | Target token | Notes |
|--------|-----------|------|
| `var(--mantine-color-gray-0)` in `Table.thead` | `color.surface.main` (`#f8fafc`) | Keep via Mantine token bridge, avoid page-level hardcoded table head colors |
| `font-variant-numeric: tabular-nums` ad-hoc in pages | `componentContracts.table.numericStyle` | Enforced globally in `index.css` / `theme.ts` |
| row borders from local styles | `neutral.200` (`#e2e8f0`) | Consolidated through table defaults and shared divider token |

### Drawer / Modal

| Current token/value | Target token | Notes |
|--------|-----------|------|
| `rgba(255,255,255,0.92)` modal surface | `--overlay-glass-surface` | Mapped to tokenized glass surface |
| `rgba(255,255,255,0.96)` drawer surface | `--drawer-glass-surface` | Mapped to tokenized drawer surface |
| raw `box-shadow` rgba values | `--shadow-soft-md` | Unified shadow contract |
| overlay dark background rgba | `--overlay-backdrop` | One source for overlay opacity/feel |

### Context bar

| Current token/value | Target token | Notes |
|--------|-----------|------|
| `glass-light` with raw rgba white | `--contextbar-surface` | Sticky context bar uses tokenized glass surface |
| local border gray shades | `neutral.200` (`--mantine-color-gray-2`) | No custom border hex in pages |
