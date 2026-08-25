# QA_ARCH: волна A — косметический порядок EN + craft (2026-08-23)

**Источники:** `FRONTEND_COSMETIC_ORDER_TZ_2026-08-23.md` rev 3 (приёмка 1–10, SC1–SC7), `QUEUE_FRONTEND_COSMETIC_ORDER_2026-08-23.md` Q1–Q10 STOP, `FRONTEND_AESTHETICS_AUDIT_2026-08-23.md` §9–§10.  
**Проверено:** диск + прогон тестов 2026-08-24; **deep audit** 2026-08-24 (post-Q11 fixes). Продуктовый код в Q11 не менялся; исправления — в GLOBAL AUDIT Q11 (QUEUE).

---

## Вердикт

| Область | Заключение |
|---------|------------|
| Приёмка A (п. 1–10) по коду | **🟢** — все пункты подтверждены file:line или тестами |
| SC1–SC7 | **🟢** в контуре волны A; один глобальный хвост SC3 вне файлов A — см. 🟡 |
| Законы 8 / 11 / 26 / 38 | **🟢** по коду (Law 26 геометрия окна — делегировано Q12 @QA_VISUAL) |
| Возвраты @DEV | **Нет** — блокеров по Q1–Q10 не найдено |

**Итог: 🟢** — BATCH 4 может переходить к **Q12 @QA_VISUAL**.

### 🟡 Не блокируют Q12 (зафиксированы в NEXT)

| ID | Факт | Владелец |
|----|------|----------|
| A2-LAW8-LOYALTY-SUB-ID | `AdminLoyaltyPage.tsx:199` — `s.id.slice(0,8)` в колонке ID | A2-C1-MONEY |
| Q6-SEARCH-TRACE | Поиск задач матчит legacy `description` с `trace_id=` | A2-SEED / search index |
| Q9-UPLOAD-ROUTER-IT | Нет pytest на живой upload handler (DB skip в CI) | Q13 |

**Закрыто в deep audit 2026-08-24:** Q10-OMNI-FILTER-LABELS, Q10-BE-VK-CREATE, Loyalty `package_id.slice` fallback.

---

## Прогон тестов (exit 0)

```text
# frontend (из frontend/)
npx vitest run src/admin/pages/__tests__/AdminTasksPage.test.tsx \
  src/admin/pages/__tests__/AdminStaffCalendarPage.test.tsx \
  src/admin/pages/__tests__/AdminSalesPipelinePage.test.tsx \
  src/shared/__tests__/doctorRoleI18n.test.ts \
  src/shared/__tests__/taskDescriptionSanitize.test.ts \
  src/shared/__tests__/omniUploadErrors.test.ts \
  src/shared/__tests__/chatI18n.test.ts \
  src/shared/__tests__/taskStatusSemantic.test.ts \
  src/shared/__tests__/adminChatChrome.test.ts \
  src/i18n
→ 12 files, 84 passed

# backend (из корня)
python -m pytest tests/application/test_tasks_event_handlers.py \
  tests/services/test_booking_completion_service.py \
  tests/unit/test_omni_media_storage.py -q
→ 19 passed, 9 skipped

# API IT (требует DB; в sandbox skip):
pytest tests/api/test_owner_omni_channels.py::test_owner_create_vk_bot_rejected -q
```

---

## Обязательные доказательства (file:line)

### Q4 — один «New task», toolbar без дубля

| Проверка | Доказательство |
|----------|----------------|
| Кнопка только в ContextBar | `AdminTasksPage.tsx:929–936` — `actions={ mode === "leads-log" ? null : ( <Button …>{t("newTask")}</Button> )}` |
| Нет второй кнопки в toolbar | `grep setCreateOpened` / `newTask` — только ContextBar `:933`, modal `:1431`, EmptyState CTA `:2881` (не chrome toolbar) |
| Тест: ровно один accessible name | `AdminTasksPage.test.tsx:362–365` — `getAllByRole("button", { name: "New task" }).toHaveLength(1)` |

### Q7 + Q4 — sanitize `trace_id=` в UI задач

| Проверка | Доказательство |
|----------|----------------|
| Sanitize в details | `TaskDetailsView.tsx:52,204` — `sanitizeTaskDescription(task.description)` |
| Регекс strip | `taskDescriptionSanitize.ts:5–7` — удаляет `trace_id=…` (+ optional `event_id=`) |
| BE не пишет в description | `test_tasks_event_handlers.py:64,128` — `assert "trace_id=" not in kwargs["description"]`; `grep 'description +=.*trace_id'` в `src/application` — **0** |

### Q2 — Patient modal: высота, ScrollArea, вкладки

| Проверка | Доказательство |
|----------|----------------|
| `PATIENT_MODAL_TABS_H = 440` | `PatientEntityDrawer.tsx:52` |
| ScrollArea `h={PATIENT_MODAL_TABS_H}` | `:308,420,470,501,635,905` |
| Нет Autosize / `mah` на textarea вкладок | `grep Autosize|mah=` в файле — **0** |
| Tabs.List nowrap, без grow на списке | `:291–305` — `flexWrap: "nowrap"`, `overflowX: "auto"`; `Group grow` только в форме диагнозов `:712` (не Tabs.List) |

### Q2 / SC3 — нет `package_id.slice` в patient modal

| Проверка | Доказательство |
|----------|----------------|
| Подпись абонемента | `PatientEntityDrawer.tsx:210–216` — `passOptionLabel` → `t("patientDrawer.packageRemain", { remain: … })`, без slice id |
| В файле нет `package_id` | `grep package_id` — **0** |

### Q1 — Calendar: text+blur, без native time widgets

| Проверка | Доказательство |
|----------|----------------|
| Нет `formatTimeHHMMInput` / `datetime-local` / `type="time"` | `grep` по `AdminStaffCalendarPage.tsx` — **0** |
| text + blur helpers | `:90–95` — `filterTimeDraft`, `normalizeTimeBlur`; inputs `:1401–1410`, `:1450–1468` — `type="text"`, `inputMode="numeric"`, onBlur → `normalizeTimeBlur` |
| Тест EN + all-day | `AdminStaffCalendarPage.test.tsx` — 3 passed |

### Q3 — doctor role i18n

| Проверка | Доказательство |
|----------|----------------|
| `doctorRoleI18n.ts` без `useTranslation` | `doctorRoleI18n.ts:1,22–33` — `import i18n`; `i18n.t` / `i18n.exists` |
| Не `display_role` | `:19–23` — комментарий + `firstString(doctor, ["specialist_role"])`; тест `:24–28` в `doctorRoleI18n.test.ts` |

### Q4 — leads-log без `titleOverride`

| Проверка | Доказательство |
|----------|----------------|
| Обёртка не передаёт prop | `AdminLeadsLogPage.tsx:4` — `<AdminTasksPage mode="leads-log" forcedStreamSlug="leads-log" />` |
| Заголовок из словаря | `AdminTasksPage.tsx:930` — `mode === "leads-log" ? t("leadsTitle") : t("title")`; `titleOverride` нигде не передаётся извне (`grep titleOverride` — только определение в `AdminTasksPage.tsx`) |
| Нет New task на leads-log | `:932` — `actions={ mode === "leads-log" ? null : …}` |

### Q9 — upload MIME / structured errors

| Проверка | Доказательство |
|----------|----------------|
| `sniff_omni_upload_mime` | `omni_media_storage.py:29` |
| `is_omni_svg_upload` | `:50` |
| `_err` коды | `admin_omni_chat.py:1750` `omni_file_empty`; `:1753` `omni_file_too_large`; `:1760` `omni_svg_forbidden`; `:1763` `omni_file_type_denied` |
| FE map | `omniUploadErrors.ts:9–16` → `chat.errors.file*` |
| Unit | `test_omni_media_storage.py` — в прогоне 16 кейсов в составе 19 passed |

### Q10 — VK hide + EN channel labels

| Проверка | Доказательство |
|----------|----------------|
| Create без `VK_BOT` | `chatI18n.ts:15–18` — `OMNICHANNEL_CREATE_TYPE_CODES` без VK; `:84–89` — `omniChannelCreateTypeOptions` / `isOmniChannelCreatableType` |
| Channels page использует create options | `AdminOmniChannelsPage.tsx:107` — `omniChannelCreateTypeOptions()`; legacy VK read-only `:556`, `:743` |
| Patient VK OAuth убран | `grep VK|vk` в `PatientPhoneAuthPanel.tsx` — **0** |
| Тест | `chatI18n.test.ts` — 2 passed |

### Q3 / A5 — phone `+7`, нет locale→+1

| Проверка | Доказательство |
|----------|----------------|
| JSON en/ru | `en/schedule.json:33`, `ru/schedule.json:33` — `"phonePlaceholder": "+7..."` |
| SchedulePage | `SchedulePage.tsx:125` — `placeholder={t("phonePlaceholder")}`; нет ветки `+1` / `locale` → prefix |

### JSON ownership rev 3

| Файл | Владелец по ТЗ | Факт на диске |
|------|----------------|---------------|
| `schedule.json` | Q1 не писал | ключи `staffCal.*` / `phonePlaceholder` — потребление только |
| `chat.json` errors | Q8 | `en/chat.json:127–145` — `fileTooLarge`, `fileTypeDenied`, `fileEmpty`, `fileSvgForbidden` |
| `chat.json` omniChannels.intro | Q10 | `en/chat.json:251` — без «VK»; ru зеркало |

### Q5 — AdminSalesPipelinePage без RU в кавычках

| Проверка | Доказательство |
|----------|----------------|
| grep кириллица в JSX-строках | `AdminSalesPipelinePage.tsx` — **0** совпадений `[А-Яа-я]` в кавычках |
| Тесты EN chrome | `AdminSalesPipelinePage.test.tsx` — 6 passed |

---

## Приёмка A (п. 1–10)

| # | Критерий | Статус | Доказательство |
|---|----------|--------|----------------|
| 1 | Calendar EN; text+blur; no native time | 🟢 | Q1 evidence + `AdminStaffCalendarPage.test.tsx` |
| 2 | Один New task; нет trace в body; kanban craft | 🟢 | Q4 + Q6 tests; tint/details — код Q6 |
| 3 | Leads-log `Leads (log)` | 🟢 | `leadsTitle` key; no `titleOverride` |
| 4 | Patient modal EN; no hex package id; phone +7 | 🟢 | Q2 + Q3 evidence |
| 5 | Staff-chat EN | 🟢 | Q5 scope staff chat — в GLOBAL AUDIT QUEUE STOP |
| 6 | Sales pipeline EN | 🟢 | Q5 grep + tests |
| 7 | Omni short messages edge; voice webm | 🟢 | Q8 layout + Q9 MIME |
| 8 | Channels create no VK; patient VK hidden | 🟢 | Q10 evidence |
| 9 | Finance ₽ unchanged | 🟢 | вне диффа волны A |
| 10 | Нет commit агентом | 🟢 | Law 40 — только локальные изменения |

---

## SC1–SC7

| SC | Критерий | Статус | Доказательство |
|----|----------|--------|----------------|
| SC1 | SVG deny filename + MIME | 🟢 | `is_omni_svg_upload` + router `:1759–1760` |
| SC2 | sniff webm/octet-stream → audio | 🟢 | `omni_media_storage.py:29+`; unit tests |
| SC3 | Нет UUID в task body / package slice | 🟢 в A | Task sanitize + Patient passOptionLabel; Loyalty package col → `—`; id col slice → A2-LAW8-LOYALTY-SUB-ID |
| SC4 | VK create/OAuth скрыты; labels i18n | 🟢 | FE + BE `omni_channel_type_not_creatable`; read-only legacy OK |
| SC5 | Patient chrome i18n | 🟢 | Q2 directory `patientDrawer.*` |
| SC6 | Не логировать bytes voice | 🟢 | Q9 — не в scope upload router log body |
| SC7 | Upload 4xx structured `_err` | 🟢 | `admin_omni_chat.py` upload handler |

---

## Векторы законов

### Law 8 — UUID не в UI

- Task description: sanitize 🟢 (`TaskDetailsView.tsx:204`).
- Patient package: human label 🟢 (`PatientEntityDrawer.tsx:210–216`).
- Assignee на calendar/tasks: `displayPersonName` — GLOBAL AUDIT QUEUE 🟢.
- Хвост Loyalty slice — 🟡 вне A.

### Law 11 — async safety

- Календарь: существующие mutation handlers с try/catch не вычищены (spot-check Q1 STOP). Новых пустых catch не вводилось.

### Law 26 — layout invariants

- Patient drawer: фиксированная высота панелей вкладок 440px + nowrap tabs 🟢 по коду.
- **Измерение delta main vs notes на 360/1280** — не в зоне Q11; **Q12 @QA_VISUAL**.

### Law 38 — Security surface

- Затронуто: omni upload (S5 untrusted input), patient OAuth removal (S1/S10).
- Upload: deny-by-default MIME + SVG + structured 4xx 🟢.
- Security Contract в DEV_PROMPTS wave — см. QUEUE Q8/Q9 AUDIT; код соответствует контракту ошибок.

---

## Матрица Q1–Q10 (кратко)

| Q | Тема | QA_ARCH |
|---|------|---------|
| Q1 | Calendar EN + text/blur time | 🟢 |
| Q2 | PatientEntityDrawer | 🟢 |
| Q3 | SchedulePage + doctorRoleI18n | 🟢 |
| Q4 | Tasks dual CTA + trace sanitize | 🟢 |
| Q5 | Staff chat + Sales EN | 🟢 |
| Q6 | Kanban craft | 🟢 |
| Q7 | BE task descriptions EN | 🟢 |
| Q8 | Omni thread layout + chat errors JSON | 🟢 |
| Q9 | Omni MIME backend | 🟢 |
| Q10 | VK hide + channel labels | 🟢 | FE create guard + BE reject; inbox filter labels i18n |

---

## Deep audit 2026-08-24 (post-Q11)

Повторный проход @LEAD/@ARCH/@QA_ARCH/@FRONTEND: формальные декларации, противоречия доков, SC4 end-to-end.

| Находка | Класс | Действие |
|---------|-------|----------|
| Inbox filter raw channel codes | 🟠 средний | **Исправлено** — `omniChannelTypeLabel` |
| API create VK_BOT bypass | 🟠 средний | **Исправлено** — structured 400 + pytest |
| Loyalty package_id.slice fallback | 🟡 | **Исправлено** — `—`; id column → NEXT |
| QA report 80 vs GLOBAL 82 tests | 🟡 формальный | **Синхронизировано** — канон Q13: `test:wave-a` **100 passed** |
| NEXT прогресс «Q11 осталось» | 🟡 формальный | **Исправлено** в NEXT/QUEUE |
| Q13 grep без AdminOmniChat / bare JSX | 🟡 | **Исправлено** — GLOBAL AUDIT Q13 |

Подробности: `QUEUE` § GLOBAL AUDIT Q11 + § GLOBAL AUDIT Q13.

---

## Возвраты @DEV

**Нет.** Волна A (Q1–Q13) закрыта. Остатки — `FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md` (A2-*).

---

## Следующий шаг

**Human commit** (Law 40) + **A2-*** из NEXT. Playwright pixel / Staff chat page test — опционально в A2.
