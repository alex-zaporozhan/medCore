# QA TEST — волна A косметический порядок (Q13)

**Роль:** @QA  
**Вход:** 🟢 Q11 [`QA_REPORT_FRONTEND_COSMETIC_ORDER_2026-08-23.md`](./QA_REPORT_FRONTEND_COSMETIC_ORDER_2026-08-23.md) · 🟢 Q12 [`waves/cosmetic-a/VISUAL_QA_REPORT_COSMETIC_ORDER_2026-08-23.md`](./waves/cosmetic-a/VISUAL_QA_REPORT_COSMETIC_ORDER_2026-08-23.md)  
**Дата прогона:** 2026-08-24

---

## Вердикт: 🟢

Волна A **закрыта по тестам и grep-gate**. Возвратов @DEV нет. Playwright e2e не запускался (вне минимального STOP Q13).

---

## Команды и exit code

### Frontend (из `frontend/`)

```bash
npm run test:wave-a
```

Эквивалент вручную:

```bash
npx vitest run \
  src/admin/pages/__tests__/AdminTasksPage.test.tsx \
  src/admin/pages/__tests__/AdminStaffCalendarPage.test.tsx \
  src/admin/pages/__tests__/AdminSalesPipelinePage.test.tsx \
  src/admin/components/entity/__tests__/PatientEntityDrawer.geometry.test.tsx \
  src/shared/__tests__/doctorRoleI18n.test.ts \
  src/shared/__tests__/taskDescriptionSanitize.test.ts \
  src/shared/__tests__/taskStatusSemantic.test.ts \
  src/shared/__tests__/omniUploadErrors.test.ts \
  src/shared/__tests__/adminChatChrome.test.ts \
  src/shared/__tests__/chatI18n.test.ts \
  src/admin/__tests__/waveACyrillicGate.test.ts \
  src/api/__tests__/client-api-errors.test.ts \
  src/i18n
```

**Результат (deep audit Q13):** `15 files, 100 passed` · **exit 0**

### Backend (из корня репозитория)

```bash
python -m pytest \
  tests/application/test_tasks_event_handlers.py \
  tests/unit/test_omni_media_storage.py \
  tests/services/test_booking_completion_service.py -q
```

**Результат:** `19 passed, 9 skipped` · **exit 0**

### API IT (опционально, требует DB)

```bash
python -m pytest tests/api/test_owner_omni_channels.py::test_owner_create_vk_bot_rejected -q
```

**Результат в sandbox:** `skipped` (нет test DB) — не блокирует Q13; тест на диске после deep audit Q11.

---

## Чеклист приёмки (Q13)

| Проверка | Статус | Evidence |
|----------|--------|----------|
| AdminTasksPage: ровно 1 «New task» | 🟢 | `AdminTasksPage.test.tsx:362–365` |
| Calendar EN: нет «Участники»; all-day без time/datetime-local | 🟢 | `AdminStaffCalendarPage.test.tsx` (3 tests) |
| MIME: webm+octet-stream → audio/webm; SVG denied | 🟢 | `test_omni_media_storage.py:12–14, 25–36, 76–79` |
| handlers: `"trace_id="` not in description | 🟢 | `test_tasks_event_handlers.py:64,128` |
| i18nDefaultEn: dayjs locale не ru; VK_BOT label ok, create excluded | 🟢 | `i18nDefaultEn.test.ts:163–165, 402–412` |
| Grep-gate wave A: нет кириллицы в literals + bare JSX | 🟢 | `waveACyrillicGate.test.ts` (9 files) |
| API client: nested `detail.code` | 🟢 | `client-api-errors.test.ts` (Q9) |

---

## Grep-gate (механический)

| Файл | Ручной rg | Автотест |
|------|-----------|----------|
| `AdminStaffCalendarPage.tsx` | только комменты/JSDoc | 🟢 |
| `PatientEntityDrawer.tsx` | 0 | 🟢 |
| `BookingEntityDrawer.tsx` | 0 | 🟢 |
| `AdminLeadsLogPage.tsx` | 0 | 🟢 |
| `AdminStaffChatPage.tsx` | 0 | 🟢 |
| `AdminSalesPipelinePage.tsx` | 0 | 🟢 |
| `AdminTasksPage.tsx` | 0 | 🟢 |
| `AdminOmniChannelsPage.tsx` | 0 | 🟢 |
| `AdminOmniChatPage.tsx` | 0 | 🟢 |

**Harness:** `frontend/src/admin/__tests__/waveACyrillicGate.test.ts` — strip comments + quoted literals + bare JSX text (`>…<`).

Полный CI grep по `admin/**` — **NEXT** (`A2-GREP`).

---

## Добавлено в Q13

| Артефакт | Назначение |
|----------|------------|
| `waveACyrillicGate.test.ts` | Регрессия C1: 9 файлов, quoted + bare JSX |
| `package.json` → `test:wave-a` | Канонический прогон wave A |
| `client-api-errors.test.ts` | Включён в `test:wave-a` (Q9 contract) |

---

## GLOBAL AUDIT Q13 (deep pass)

| Находка | Действие |
|---------|----------|
| `AdminOmniChatPage` не в grep-gate | добавлен в harness |
| Только quoted literals | + bare JSX text scan |
| Нет `npm run test:wave-a` | скрипт в `package.json` |
| `client-api-errors` вне канона | в `test:wave-a` |
| NEXT: «нет PatientEntityDrawer test» | устарело — Q12 geometry test есть |

**Открытые риски:** `Q13-STAFF-CHAT-TEST`, `A2-GREP` (полный admin/), `Q9-UPLOAD-ROUTER-IT`, `Q13-PLAYWRIGHT-PIXEL` — см. NEXT.

---

## Не в scope Q13 (зафиксировано)

| ID | Что |
|----|-----|
| Q13-STAFF-CHAT-TEST | Нет `AdminStaffChatPage.test.tsx` — NEXT |
| Q13-PLAYWRIGHT-PIXEL | Playwright visual @1280 — NEXT / CI со стеком |
| Q9-UPLOAD-ROUTER-IT | Pytest на живой upload handler — NEXT при DB |
| A2-GREP | eslint/CI по всему `admin/` |

---

## BATCH 4 — итог

| Промпт | Вердикт |
|--------|---------|
| Q11 @QA_ARCH | 🟢 |
| Q12 @QA_VISUAL | 🟢 |
| Q13 @QA | 🟢 |

**Волна A (Q1–Q13) закрыта.** Долги — [`FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md`](./FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md).

**Law 40:** commit/push — только human.
