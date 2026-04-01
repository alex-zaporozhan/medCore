# LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS

> **Роль:** @LEAD  
> **Назначение:** пошаговая реализация дизайн-пакета 85+ в рабочем контуре (`roadmap`, `8W tracker`, delivery gates).  
> **Основа:** `LEAD_DESIGNER_TZ_ENTERPRISE_85_PLUS.md` + результаты `@DESIGN`.  
> **Унификация палитры Swiss Slate / Ink (канон §3.6):** маршрут и список файлов — **`LEAD_DESIGN_UNIFICATION_ROUTE_SWISS_SLATE_INK.md`**.

---

## 1) Стартовый вердикт по работе @DESIGN

### Что принято

1. Полный пакет артефактов предоставлен:
   - `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md`
   - `DESIGN_SCREEN_AUDIT_MATRIX.csv`
   - `DESIGN_TOKENS_85_PLUS.json`
   - `DESIGN_COMPONENT_MAPPING.md`
   - `DESIGN_P0_P1_BACKLOG.md`
2. Покрытие экранов и модулей достаточное для enterprise-среза.
3. Есть приоритизация P0/P1/P2 и связка с component-стандартизацией.

### Что усилено @LEAD (обязательное к исполнению)

1. Нужен единый execution-playbook с фазами, owner, evidence и release gates.
2. Нужна жёсткая синхронизация design-задач с CI/release документами 85+.
3. Нужен формальный формат weekly-отчёта по дизайн-внедрению.

---

## 2) Пошаговая реализация (обязательная)

## Step 0 — Governance freeze (день 0)

1. Зафиксировать дизайн-пакет как source of truth.
2. Назначить владельцев:
   - DESIGN (визуальная система),
   - DEV FE (реализация),
   - QA_ARCH (evidence и приемка),
   - LEAD (вердикт).
3. Запретить запуск “параллельных” локальных дизайн-паттернов без ссылки на canonical docs.

**Deliverable:** короткий decision log в weekly report.

---

## Step 1 — Token adoption (день 1-2)

1. Взять канон **`DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6** (Swiss Slate / Ink) и чеклист **`LEAD_DESIGN_UNIFICATION_ROUTE_SWISS_SLATE_INK.md`** (код + документы).
2. Сопоставить `DESIGN_TOKENS_85_PLUS.json` с `frontend/src/theme.ts` и `frontend/src/index.css`.
3. Отметить конфликтующие токены:
   - цветовые роли,
   - тени/elevation,
   - spacing/radius,
   - interaction/focus.
4. Подготовить migration diff: “current -> target token”.

**Acceptance:**
- token mapping table утверждена DESIGN + DEV FE,
- нет “анонимных” hardcoded color/shadow в P0 компонентах.

---

## Step 2 — Shell and header unification (день 2-3)

1. Принудительно выровнять все admin page headers через `ContextBar`.
2. Проверить единый sticky contract в `AdminLayout`.
3. Убрать локальные header/action паттерны в P0 экранах.

**Acceptance:**
- P0 admin страницы используют только canonical header pattern,
- визуальный smoke подтверждает отсутствие layout drift.

---

## Step 3 — Table/state standardization (день 3-4)

1. Применить canonical table contract в:
   - `AdminTasksPage`,
   - `AdminReportsPage`,
   - `AdminPatientsPage`,
   - `AdminBookingsPage`.
2. Нормализовать состояния:
   - loading/empty/error/partial failure/success.
3. Утвердить единый toolbar/filter order.

**Acceptance:**
- 4 целевых экрана проходят UI regression checklist,
- QA evidence приложен (скрин + сценарий на каждое состояние).

---

## Step 4 — Drawer/modal convergence (день 4-5)

1. Выровнять entity drawers по `DESIGN_COMPONENT_MAPPING.md`.
2. Свести modal style к единому entrypoint (`mergeModalStyles` / shell contract).
3. Убрать визуальные расхождения между `AdminDrawer` и entity drawers.

**Acceptance:**
- 4 entity drawers соответствуют одному контракту,
- модальные surfaces не имеют локальных конфликтных стилей.

---

## Step 5 — Severity and ops UX alignment (день 5-6)

1. Выровнять severity semantics (`critical/warning/info`) для:
   - `AdminTasksPage`,
   - `AdminOmniChatPage`,
   - `AdminEmergencyNotificationsPage`.
2. Закрепить canonical mapping semantic tokens -> status badges/actions.

**Acceptance:**
- единый визуальный язык severity во всех 3 экранах,
- нет конфликтов в цветовой семантике.

---

## Step 6 — Accessibility gate (день 6)

1. Пройти keyboard/focus/contrast check по всем P0 экранам.
2. Зафиксировать evidence и найденные отклонения.
3. Закрыть отклонения до релизной приёмки.

**Acceptance:**
- P0 accessibility checklist закрыт,
- evidence добавлен в release pack.

---

## Step 7 — P1 implementation wave (следующий цикл)

1. CRM/pipeline visual standard.
2. Settings form contract.
3. Omni/chat convergence.
4. Finance/reports numeric readability.
5. Box/Enterprise UX integrity.

**Acceptance:**
- пункты P1 переведены в DEV задачи с PR/evidence ссылками.

---

## 3) Жёсткие правила исполнения

1. Любая UI-правка в P0/P1 экранах без ссылки на canonical артефакты = non-compliant.
2. Нельзя закрыть дизайн-задачу без evidence (`before/after`, сценарий, acceptance).
3. Нельзя выносить P0 в “потом” при релизе 85+.
4. Любой конфликт между локальным стилем и token contract решается в пользу token contract.

---

## 4) Delivery gates для дизайн-внедрения

| Gate ID | Проверка | Blocker |
|---------|----------|---------|
| D1 | Token mapping approved | без этого нельзя стартовать P0 внедрение |
| D2 | ContextBar/Admin shell unified | без этого нельзя закрыть P0 |
| D3 | 4 data-heavy screens standardized | без этого `NO-GO` для UI readiness |
| D4 | Drawers/modals converged | без этого `NO-GO` для entity UX |
| D5 | Severity semantics aligned | без этого `NO-GO` для ops UX |
| D6 | P0 accessibility evidence complete | без этого `NO-GO` релизного UX verdict |

---

## 5) Формат weekly отчёта (добавка к 8W)

| Week | Step | Done | Evidence links | Open risks | Next action |
|------|------|------|----------------|------------|-------------|
| WN | Step N | yes/no | links | list | action |

---

## 6) Final design readiness verdict

| Level | Условие | Решение |
|-------|---------|---------|
| D0 | P0 steps не закрыты | `NO-GO` |
| D1 | P0 закрыт частично, есть waiver | `GO-WAIVER` |
| D2 | P0 полностью закрыт + evidence complete | `GO` |
| D3 | D2 + P1 wave закрыт без критичных drift | `GO` (enterprise-hardened) |

---

## 7) Связанные артефакты

- `LEAD_DESIGNER_TZ_ENTERPRISE_85_PLUS.md`
- `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md`
- `DESIGN_SCREEN_AUDIT_MATRIX.csv`
- `DESIGN_TOKENS_85_PLUS.json`
- `DESIGN_COMPONENT_MAPPING.md`
- `DESIGN_P0_P1_BACKLOG.md`
- `QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER.md`
- `QA_ARCH_85_PLUS_ROADMAP.md`
