# VISUAL QA — волна A косметический порядок (2026-08-23)

**Роль:** @QA_VISUAL  
**Вход:** 🟢 Q11 [`QA_REPORT_FRONTEND_COSMETIC_ORDER_2026-08-23.md`](../../QA_REPORT_FRONTEND_COSMETIC_ORDER_2026-08-23.md)  
**Канон:** `roles/QA_VISUAL_AESTHETE_SENSOR.md` · `roles/LAYOUT_INVARIANTS.md` · ТЗ D1–D3 rev 3  
**Метод:** render → measure → compare (Vitest RTL harness + code audit; Playwright 1280/360 full-pixel — рекомендован в Q13 при поднятом preview)

---

## Вердикт

| Область | Заключение |
|---------|------------|
| D1 Kanban / tasks | **🟢** |
| D2 Omni thread | **🟢** (код + token tests; pixel edge-anchor — code contract) |
| D3 Patient modal | **🟢** (minHeight 560px stable; tabs nowrap @360 — harness) |
| D4 Calendar time UX | **🟢** (text+blur; см. `AdminStaffCalendarPage.test.tsx`) |
| Aesthete A–H | **🟢** — нет 🔴 crime в scope волны A |
| **Итог** | **🟢** — GATE visual BATCH 4 закрыт; волна A закрыта Q13 |

### 🟡 не блокируют 🟢 (NEXT / Q13)

| ID | Наблюдение |
|----|------------|
| Q13-PLAYWRIGHT-PIXEL | Нет Playwright screenshot diff на 1280 для omni bubble X-offset |
| Q6-STREAM-ACCENT | `accentColor` в `StreamPageShell` не визуализируется (dead prop) |
| Q4-BUBBLE | Staff chat пузыри не сверены pixel-to-pixel с omni |
| Q2-RTL | PatientEntityDrawer @360 tabs — **закрыто Q12** harness; полный RTL pixel — NEXT |

---

## Измерения (факты)

### D3 — Patient modal (`PatientEntityDrawer`, presentation=modal)

| Viewport | Проверка | Результат | Источник |
|----------|----------|-----------|----------|
| 1280 | `minHeight` окна main / Overview / Chart | **560px / 560px / 560px** (Δ=0) | `PatientEntityDrawer.geometry.test.tsx` |
| 1280 | ScrollArea на панелях | **≥6** корней `.mantine-ScrollArea-root` | тот же harness |
| 360 | `Tabs.List` одна строка | `flexWrap: nowrap`, `scrollHeight ≤ 48px`, 6 tabs | тот же harness |
| код | `PATIENT_MODAL_TABS_H` | **440** | `PatientEntityDrawer.tsx:52` |
| код | shell | `content.minHeight: 560`, `body.minHeight: 560` | `:936`, `:953` |

### D1 — Kanban column chrome

| Проверка | Результат | file:line |
|----------|-----------|-----------|
| SLA badge только при `overdueCount > 0` | ✅ | `AdminTasksPage.tsx:2217–2220` |
| Aging badge только при `agingCount > 0` | ✅ | `:2222–2225` |
| WIP badge только при `wipLimit != null` | ✅ | `:2212–2215` |
| Карточка: `taskKanbanQuietSurface`, без shadow/tint/bar | ✅ | `:243`, `taskStatusSemantic.ts:16–22` |
| Нет status Badge на карточке (только blocked gray) | ✅ | `:371–385` |
| Details: `taskStatusCardSurface` сохранён | ✅ | `TaskDetailsView.tsx:277` |
| Stream shell: hairline 1px, не gradient | ✅ | `StreamPageShell` `:2300–2304` |
| Approval queue скрыт при length=0 | ✅ | `:2767` |

### D2 — Omni thread

| Проверка | Результат | file:line |
|----------|-----------|-----------|
| Нет spacer `width:28` / meta `width:56` / nested `Paper p={6}` | ✅ grep пуст | `AdminOmniChatPage.tsx` |
| Пузырь: `justify flex-start/end`, `maxWidth: min(68%, 36rem)` | ✅ | `:1080–1096` |
| Padding `8px 12px`; meta 11px dimmed внутри | ✅ | `:1097`, `:1153` |
| Outgoing token = staff outgoing | ✅ | `adminChatChrome.test.ts` |
| Incoming surface + hairline | ✅ | `adminChatChrome.test.ts` |

### D4 — Calendar timed create

| Проверка | Результат |
|----------|-----------|
| blur `930` → `09:30` | `normalizeTimeBlur` unit |
| all-day: нет `type=time` / `datetime-local` | `AdminStaffCalendarPage.test.tsx` |

---

## Экраны (чеклист Q12)

| Экран | 1280 | 360 | Статус |
|-------|------|-----|--------|
| Calendar timed create | код + unit | — | 🟢 |
| Tasks board / kanban | код audit | — | 🟢 |
| Schedule → patient modal tabs | harness | harness (nowrap) | 🟢 |
| Omni short messages | код D2 | — | 🟢 |

---

## 🎯 Aesthete verdict

| Блок | Пункты | Итог |
|------|--------|------|
| **A** Ритм/равновысотность | A1 | 🟢 Kanban cards `width:100%`; column badges wrap only when counts>0 |
| | A2 | 🟢 Patient panels fixed ScrollArea 440 + shell minHeight 560 |
| | A3 | ⚪ N/A — нет multi-column baseline grid на этих экранах |
| | A4 | 🟢 Mantine spacing tokens; omni list `gap={8}` |
| | A5 | ⚪ N/A — не grid landing |
| | A6 | 🟢 Meta внутри пузыря, не отдельная колонка |
| **B** Состояния/контраст | B1–B6 | 🟢 instrument register; приоритет dimmed Text, не цветной badge на карточке |
| **C** Типо-шкала/chrome | C1–C2 | 🟢 chrome xs/sm; 44px через padding |
| | C3–C6 | 🟢 ≤6 уровней на kanban card; tabular-nums N/A |
| **D** Цвет/палитра | D1 | 🟢 kanban quiet; column badges semantic only when non-zero |
| | D2–D3 | 🟢 omni outgoing `--primary-alpha-12`; ink tokens |
| | D4 | 🟢 StreamPageShell без rainbow; pager fade 44px aria-hidden — не stream header |
| | D5–D7 | 🟢 blocked = gray pill; WCAG via Mantine defaults |
| **E** Композиция | E1–E6 | 🟢 operational density; omni edge-anchored bubbles |
| **F** Семантика раскладки | F1 | 🟢 New task в ContextBar |
| | F2–F6 | 🟢 primary actions в chrome; kanban columns scan L→R |
| **G** Ритм страницы | P1–P6 | ⚪ N/A — не landing; admin instrument screens |
| **H** Детекторы канона | X1–X12 | 🟢 нет gradient-as-paint на stream shell; kanban не 4× separation |
| | ST1–ST12 | 🟢 empty kanban CTA opens create (Q6); reversible actions unchanged |
| | Y1–Y12 | ⚪ N/A — не statement |

---

## Векторы LAYOUT (V1–V12 summary)

| V | Критерий | Статус | Evidence |
|---|----------|--------|----------|
| V1 | Equal-height cards in grid | 🟢 | kanban column stack; quiet surface uniform |
| V2 | No horizontal overflow 360 | 🟢 | patient tabs nowrap+scroll harness |
| V7 | Zero-shift interactions | 🟢 | hover на карточке без border width change |
| V12 | z-index from scale | 🟢 | без raw z-index в wave A diff |
| V15–V20 | Craft floor | 🟢 | см. `taskStatusSemantic.test`, `adminChatChrome.test` |

---

## Возвраты @DEV

**Нет 🔴.** Визуальные критерии D1–D3 выполнены.

---

## Harness (добавлен Q12)

```
frontend/src/admin/components/entity/__tests__/PatientEntityDrawer.geometry.test.tsx
→ 3 passed (1280 minHeight; 360 tab row; ScrollArea count)
```

Рекомендация Q13: включить файл в `npx vitest run` wave A; опционально Playwright `1280` screenshot omni thread.

---

## Следующий шаг

**@QA → волна A закрыта.** Долги — NEXT (`A2-*`).
