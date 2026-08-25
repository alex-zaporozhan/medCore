# ТЗ: косметический порядок EN + точечный craft (волна A)

> **Дата:** 2026-08-23 · **Ревизия:** 4 (2026-08-24: D4 time draft + popover wheel post-audit)  
> **Статус:** волна A **закрыта** 2026-08-24 (Q1–Q13). Долги — `FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md`. Post-A: ввод времени календаря доведён (не `type=time`, не nested Modal).  
> **Диагноз:** [`FRONTEND_AESTHETICS_AUDIT_2026-08-23.md`](./FRONTEND_AESTHETICS_AUDIT_2026-08-23.md) §9–§10  
> **Промпты:** [`QUEUE_FRONTEND_COSMETIC_ORDER_2026-08-23.md`](./QUEUE_FRONTEND_COSMETIC_ORDER_2026-08-23.md)  
> **Вне A:** [`FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md`](./FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md)  
> **Не делать:** git commit/push (Law 40) · правки `roles/` · RESKIN лендинга · DROP колонок VK · привязка маски телефона к `ui.locale` · реализация кода до вставки очереди владельцем

---

## Цель волны A

Международное EN-демо **запрошенных URL**: chrome следует `ui.locale`, без UUID в операторском тексте, без прыгающих модалок, без сломанного ввода времени, без пестрого канбана, с читаемым omni-тредом, с рабочим voice (webm), без VK как предлагаемой интеграции.

Не цель A: весь оставшийся admin C1, лендинг-жест, multi-currency, `clinic.locale` для system tasks, SQL remap уже лежащих RU-задач. Это NEXT.

---

## Что получит владелец после A (ожидаемый результат)

| URL | Станет | Не станет (не баг A) |
|-----|--------|----------------------|
| `/admin/calendar` | Chrome EN; время набирается цифрами; edit не сбрасывает дату | Тела событий / имена — data |
| `/admin/schedule` медкарта | Вкладки EN; высота окна при смене таба ±0; абонемент без hex | ₽ и +7 |
| New booking | Роль EN через `specialist_role`; placeholder имени Jane Doe | Телефон всё ещё `+7...` |
| `/admin/leads-log` | Заголовок `Leads (log)` | — |
| `/admin/staff-chat` | Team chat / Members | Тела сообщений |
| `/admin/sales` | Весь chrome EN, включая AI-блок и статусы фильтра | Имена стадий/лидов; ₽ |
| `/admin/tasks` | Одна кнопка New task; тихие карточки; `trace_id=` вырезан из description в UI | **Заголовки уже созданных system-задач останутся RU** до A2-SEED |
| `/admin/omni-chat` | Короткие пузыри у края; voice webm не падает на octet-stream | Исторический VK_BOT в inbox как generic icon |
| Channels / patient OAuth | Нельзя создать VK; Sign in with VK скрыт; типы EN | Колонка `vk_id` в БД жива |
| `/` `/signup` | Без изменений в A | Statement-лендинг = NEXT concept |

---

## Глобальный контекст (читать всем)

1. Default UI locale = **en**. Словари: `frontend/src/i18n/locales/{en,ru}/`.  
2. C1: **не создавать новые ns**. Нет ключа → добавить **пару** en+ru в существующий JSON по тому же path. Писать JSON может только владелец файла из таблицы ниже.  
3. C2: title задачи, ФИО, кастомная роль, имена стадий/лидов — data. Enum `specialist_role` — `i18n.t("doctorDrawer.roles.<role>", { ns: "directory" })`.  
4. REGISTER admin = **instrument / THE FLOOR**. Один метод сепарации поверхности.  
5. Ошибки: существующий `_err(code, message)` → `HTTPException(detail={"code","message"})`. Коды omni — **lowercase** `omni_*`. FE: `ApiErrorWithCode.code` (в `parseFastApiErrorBody` уже есть `code = d.code ?? json.code`).  
6. Origin 3010/5175/5176 не шарят `localStorage.ui.locale`.  
7. **Запрет layout-shift:** hover/focus/press не меняют высоту. Новых анимаций высоты нет. `@MOTION` в A не вызывается (нет MICRO_SPEC — сознательный отказ).  
8. Хелперы i18n вне React: образец `frontend/src/shared/chatI18n.ts` (`i18n.t`, **не** `useTranslation` внутри обычной функции — это crash).  
9. `dayjs.locale(...)` на module scope **запрещён** (`ADMIN_I18N_EN_ROADMAP`).

---

## Владение файлами (антигонка) — TSX/PY

Один файл — один пишущий промпт, пока он не STOP.

| Файл | Пишет | Остальные |
|------|-------|-----------|
| `AdminStaffCalendarPage.tsx` | **Q1** | никто |
| `frontend/src/admin/pages/__tests__/AdminStaffCalendarPage.test.tsx` (новый) | **Q1** | |
| `PatientEntityDrawer.tsx` | **Q2** | Q3 только читает как сосед |
| `entityDrawerChrome.tsx` | **никто в A** | Q2 копирует число 440 локально |
| `BookingEntityDrawer.tsx` | **Q3** | |
| `SchedulePage.tsx` | **Q3** | только create form: `displayRole`, `phonePlaceholder` |
| `AdminLeadsLogPage.tsx` | **Q3** | |
| `frontend/src/shared/doctorRoleI18n.ts` (новый) | **Q3** | |
| `AdminStaffChatPage.tsx` | **Q4** | |
| `AdminSalesPipelinePage.tsx` | **Q5** | |
| `AdminTasksPage.tsx` + `TaskDetailsView.tsx` + `taskStatusSemantic.ts` + `__tests__/AdminTasksPage.test.tsx` | **Q6** | Q10 **не** трогает Tasks |
| `tasks_event_handlers.py` + `booking_completion_service.py` + pytest (создать, если нет) | **Q7** | не `ai_task_manager_service.py` |
| `AdminOmniChatPage.tsx` + `adminChatChrome.ts` | **Q8** | Q10: **только** функция иконки канала (~L75–L84), не JSX пузырей |
| `omni_media_storage.py` + upload-ветка `admin_omni_chat.py` + unit MIME | **Q9** | не FE |
| `AdminOmniChannelsPage.tsx` + `PatientPhoneAuthPanel.tsx` + `e2e/admin-omni-chat.spec.ts` | **Q10** | `chatI18n.ts` — **не** выкидывать `VK_BOT` из historical label switch |

---

## Владение JSON (rev 3 — это и была дыра)

Два агента в одном `*.json` = silent overwrite. Даже «только свой subtree» в параллели запрещён.

| Файл | Пишет | Что трогать |
|------|-------|-------------|
| `en\|ru/schedule.json` | **Q3** | `fullNamePlaceholder`; добавить корневой `phonePlaceholder` (`"+7..."` в **обоих** locale). Q1 **не пишет** этот файл: `staffCal.*` уже полный. Нет ключа у Q1 → STOP со списком, не invent. |
| `en\|ru/directory.json` | **Q2** | только `patientDrawer.*` (+ `patientDrawer.add` если нет ключа для кнопки «Добавить» в family modal). Q3 **не пишет** directory.json (`doctorDrawer.roles.*` уже есть). |
| `en\|ru/chat.json` | **Q4 → Q8 → Q10** строго по очереди | Q4: не писать JSON, если `staff.*` хватает (хватает). Load-fail → `t("errors.loadFailed", { ns: "common" })`. Q8: `errors.fileTypeDenied`, `fileEmpty`, `fileSvgForbidden`. Q10: `omniChannels.intro` (убрать слово VK из EN+RU). |
| `en\|ru/crm.json` | **Q5** | `pipeline.aiToolUnavailable` если нет; остальное `pipeline.*` / `errors.*` / корневой `status.*` уже есть |
| `en\|ru/tasks.json` | **Q6** | `list.boardTitle`; `view.copySupportId` |
| `en\|ru/common.json` | **никто в A** | weekdays уже есть |

---

## Батчи (единственная разрешённая параллель)

```
BATCH 1 (∥):  Q1 ∥ Q2 ∥ Q4 ∥ Q5 ∥ Q7
              Q6 можно ∥ с BATCH 1 (другие файлы)
BATCH 1b:     Q3  — после Q1 STOP (Q1 не пишет JSON, но один человек/агент не должен
              держать schedule.json открытым). Q3 ∥ Q2 запрещён только если Q2 ещё пишет
              directory.json; по контракту Q3 directory не трогает → Q3 ∥ Q2 допустим
              ПОСЛЕ того как Q2 закончил JSON. Практическое правило: Q3 после STOP Q1 и Q2.
BATCH 2 (∥):  Q8 ∥ Q9     — разные деревья (FE vs BE). Q4 уже STOP.
BATCH 3:      Q10         — после STOP Q8 (OmniChatPage + chat.json)
BATCH 4:      Q11 → Q12 → Q13
```

**Запрещено вставлять сразу:** Q8 вместе с Q4; Q10 вместе с Q8; Q3 вместе с Q1 «на всякий случай правят schedule.json».

---

## Security Contract (S-0)

Поверхности: **S7 files** · **S8 webhooks** · **S9 PII**.

| # | Правило |
|---|---------|
| SC1 | SVG deny по filename **и** MIME. Не `*/*`. |
| SC2 | Пустой/`octet-stream`: `sniff_omni_upload_mime(filename, ct)` — `.webm/.ogg/.mp3/.m4a/.wav` → `audio/…`; явный `video/webm` сохраняется. SVG sniff не «разрешает». **Реализовано Q9** (`omni_media_storage.py`). |
| SC3 | Нет сырых UUID в UI (description задачи, `package_id.slice`). `task.trace_id` — Copy support ID, не body. |
| SC4 | VK: нет create-option (FE+BE `omni_channel_type_not_creatable`), нет patient OAuth CTA. Исторические ряды read. Не DROP `vk_id`. Labels = `omniChannelTypeLabel`. |
| SC5 | Карточка пациента: chrome i18n; не внутренние id. |
| SC6 | Не логировать bytes voice. |
| SC7 | Upload 4xx через `_err("omni_file_type_denied" \| "omni_file_empty" \| "omni_file_too_large" \| "omni_svg_forbidden", message)`. **Реализовано Q9** в `admin_omni_chat.py` upload. |

`[SECURITY SURFACE: files + webhooks + PII display]`

---

## CONTRACT: calendar date/time (D4) — rev 3

**Почему rev 2 (`input type="time"`) отозван как единственный путь:** баг владельца — «нельзя набрать цифры». На Chrome/Windows `type="time"` — сегментированный picker, **не** свободный набор. Замена маски на `type="time"` формально закрыла бы datetime-local, но **не** починила бы ввод.

**Состояние диска после Q1 (2026-08-24, проверено аудитом) + post-audit 2026-08-24 (ввод времени):** цель D4 **реализована** в `frontend/src/admin/pages/AdminStaffCalendarPage.tsx`. Канонические имена на диске (очередь называет алиасы — не править JSON под алиасы):

- Хелперы: `filterTimeDraft` / `formatTimeDraft` / `normalizeTimeBlur` / `isValidHhmm` (3 цифры `930` → `09:30` **только** blur/submit, без live-pad; 2 цифры валидного часа `09` → `09:` сразу; 4 цифры `0900` → `09:00` сразу).
- Create и edit: один день `createSelectedDayIso` + два `TextInput` `type="text"` `inputMode="numeric"`; **нет** `datetime-local` / `type="time"` / `formatTimeHHMMInput`.
- Колесо: **Popover** у кнопки часов (не вторая Modal). Слоты не disable из‑за overlap и не из‑за «конец ≤ начала» — второй край сдвигается. Highlight не делает `N % 24` на черновике `930`.
- All-day: time inputs не рендерятся.
- Overlap: inputs не `disabled`; submit отказывается (как backend `_assert_calendar_event_no_overlap`, edit исключает self). Create/Save disabled пока `isReadyTimedRange` (оба края `isValidHhmm` и end > start).
- i18n prefix: `staffCal.*` в `en|ru/schedule.json` (Q1 JSON не писал; post-audit добавил `wheelHours` / `wheelMinutes`).
- Weekdays сетки: `t(\`calendar.weekdays.${key}\`, { ns: "common" })` как `CompactMonthPicker`.

**Целевое (create и edit одинаковы) — контракт, не «ещё сделать»:**

| Режим | Дата | Время |
|-------|------|-------|
| Timed | Create: CompactMonthPicker как сейчас. Edit: разрезать `startsLocal`/`endsLocal` на `YYYY-MM-DD` + `HH:mm`; дата — `type="date"` **или** тот же picker. Дата в отдельном state. | Два `TextInput` `type="text"` `inputMode="numeric"` `autoComplete="off"` `placeholder="09:30"`. **Не** `type="time"`. **Не** `datetime-local`. |
| All-day | дата есть | time inputs **не рендерить**; submit как сейчас all_day |

Правила набора (обязательные):

1. Удалить `formatTimeHHMMInput`.  
2. `onChange`: только `[0-9:]`, max 5; **без** live-pad трёх цифр. После валидного часа `00–23` сразу двоеточие (`09` → `09:`). Четыре цифры с валидным часом сразу `HH:mm` (`0900` → `09:00`).  
3. `onBlur`: 3 цифры `930` → `09:30`; 4 цифры `0930` → `09:30`; минуты `>59` при валидном часе → `59`; пусто ок до submit. Невалид на submit → `t("staffCal.errors.badTime")`, дату не трогать. Create/Save не активны, пока оба края не `isValidHhmm`.  
4. Колесо часов — Popover у кнопки часов, пишет в тот же `HH:mm` state. Не nested Modal. Слоты не disable «фантомной занятостью».
5. Overlap: warning, inputs не `disabled`.  
6. Submit: склеить `date + time` через dayjs **тем же** путём, что сейчас API ждёт. Не менять timezone/API.  
7. `dayjs.locale` не вызывать. Weekdays сетки: `t("calendar.weekdays.mon", { ns: "common" })` как `CompactMonthPicker` (`t(\`calendar.weekdays.${key}\`)` при ns `common`).

---

## CONTRACT: display_role (A2)

**Не** добавлять поле в API — `DoctorRead.specialist_role` и `frontend/src/api/types.ts` уже есть.

Файл `frontend/src/shared/doctorRoleI18n.ts` (Q3). Образец: `frontend/src/shared/chatI18n.ts` (`i18n.t`, не хук).

```
export function doctorRoleLabel(doctor: {
  specialist_role?: string | null;
  specialist_role_custom_name?: string | null;
}): string {
  const custom = (doctor.specialist_role_custom_name ?? "").trim();
  if (doctor.specialist_role === "other" && custom) return custom;
  const role = doctor.specialist_role ?? "";
  if (role && role !== "other") {
    return i18n.t(`doctorDrawer.roles.${role}`, { ns: "directory" });
  }
  return i18n.t("specialist", { ns: "schedule" });
}
```

Никогда не рендерить `doctor.display_role`. Не `useTranslation` внутри этой функции.

Потребители A: `SchedulePage` create (`displayRole={doctorRoleLabel(doctor)}` вместо `display_role`) и `BookingEntityDrawer` (строка врача / specialization line — роль через хелпер, не API `display_role`).

---

## CONTRACT: omni MIME (A3) — после Q9 (2026-08-24)

1. `allowed_omni_upload_mime(ct)` — `audio/*`, images (не SVG), docs, `video/webm`; SVG false.  
2. `sniff_omni_upload_mime(filename, content_type)` + `is_omni_svg_upload(filename, sniffed_ct)` в `omni_media_storage.py`. Пустой/`octet-stream` → suffix map; `.webm` → `audio/webm` (voice). Явный `video/webm` не перезаписывается.  
3. Upload (`admin_omni_chat.py`): пустой / 413 / SVG / тип → `_err(...)`, не string detail. Metadata `content_type` = sniffed.  
4. FE Q8 `onError`: `err.code` → i18n (`omniUploadErrors.ts`). `omni_chat_already_claimed` / `omni_reply_channel_unresolved` не ломать.

---

## Решения @DESIGN (исполнять)

### D1 Kanban

- Один New task: ContextBar (~935). Toolbar (~1132) — **удалить кнопку**, не прятать CSS. EmptyState `onClick: () => {}` (~2888) → `setCreateOpened(true)`.  
- На доске заголовок: новый ключ `list.boardTitle` EN `"Board"` / RU `"Доска"`. `list.title` («Task list») не использовать на канбане.  
- Колонка (~2217): LIMIT badge только если `wipLimit != null`. SLA/aging **только если count > 0**; иначе не рендерить badge (не серый «0»). Счётчик колонки (число задач) оставить.  
- **Карточка канбана (`TaskKanbanCard`):** не вызывать `taskStatusCardSurface` (border+shadow+tint+bar = 4 сепарации). Добавить в `taskStatusSemantic.ts` `taskKanbanQuietSurface(): CSSProperties` = hairline `1px var(--calendar-card-border)`, фон `--bg-card` / white, **без** boxShadow, **без** status tint, **без** left bar. Status Badge с карточки снять. Priority: `Text size="xs" c="dimmed"` через существующие `t("priority.*")`, `min-width` под самое длинное (`Urgent` / `urgent`). Blocked: одна muted pill.  
- **`TaskDetailsView`:** `taskStatusCardSurface` **оставить** (детали — место статуса). Не «вычищать» details тем же тихим стилем.  
- Stream header: убрать `linear-gradient` в `StreamPageShell` (~2302–2306); hairline 1px или 12px solid token, не радуга.  
- Needs approval (~2778): при `approvalQueueTasks.length === 0` блок не занимать вертикаль (не коллапс с нулём).  
- Description: sanitize только префиксы `trace_id=` / `event_id=` (см. QUEUE Q6). Пункт меню/кнопка `t("view.copySupportId")` если `task.trace_id`.  
- Placeholder routing «VK / EMAIL» (~1727, ~1831) → без VK.

### D2 Omni thread

- Удалить внешний nested `Paper p={6}`, meta-колонку `width: 56`, spacer `Box width: 28` (~1076–1203).  
- Один пузырь. Incoming `justifyContent: flex-start`, outgoing `flex-end`. `maxWidth: min(68%, 36rem)` — якорь к **краю** колонки, не `margin: 0 auto`.  
- `px={12}` `py={8}`. Список `gap={8}`.  
- Incoming: surface + hairline. Outgoing: `adminChatOutgoingBubbleStyle` (`--primary-alpha-12`), не indigo fill.  
- Meta (время + канал): внутри пузыря, 11px, dimmed.  
- Composer не пересобирать.

### D3 Patient modal

- Константа **локально:** `PATIENT_MODAL_TABS_H = 440` (как `BOOKING_MODAL_TABS_SCROLL_H`). Не трогать `entityDrawerChrome.tsx`.  
- Все `Tabs.Panel` внутри `ScrollArea h={PATIENT_MODAL_TABS_H} offsetScrollbars type="scroll"`. Удалить `ScrollArea.Autosize` / `mah={560}`.  
- Header профиля + `Tabs.List` **снаружи** скролла.  
- **6 вкладок ≠ 4 у booking.** На 360 `grow` + wrap **меняет высоту хрома** даже при фиксированном 440. `Tabs.List`: `flexWrap: "nowrap"`, `overflowX: "auto"`, **без** `grow`. Зарезервировать высоту ряда вкладок (как у booking list: одна линия).  
- Outer shell: как booking `content.minHeight: 560` — чтобы короткая вкладка не сжимала окно. Drawer-режим: `body.minHeight: 560` (тот же якорь высоты).  
- `Tabs.List`: ещё `minHeight: 40` (одна линия, горизонтальный scroll).  
- Визиты: `useAdminBookings(..., { enabled: Boolean(phone) })` — без телефона не тянуть весь список клиники. Имена врача/услуги через `displayPersonName` (UUID в ячейке запрещён). Статус — `bookingStatusLabel`. Ошибка query ≠ вечный skeleton.  
- Law 8: `subscription_package_id.slice(0, 8)` (~471, ~521) → `t("patientDrawer.package")` / `t("patientDrawer.packageRemain", { remain })`. Нет имени пакета — «Pass», не hex.  
- ₽ / currency — не переводить символ.

### D5 Staff vs Omni

Staff пузыри — эталон плотности. Omni идёт к ним, не наоборот.

---

## Решения @ARCH

### A1 System tasks

Новые title/description — EN. Не concat `trace_id=` / `event_id=`. Колонка `task.trace_id` жива.

Шаблоны (смысл = текущий RU):

| Место | Title | Body |
|-------|-------|------|
| cancel | Follow up on a cancelled booking | The booking was cancelled. Contact the patient to reschedule or offer the slot to others. |
| no-show | Follow up on a patient no-show | The patient did not attend. Contact them, find out why, and offer a new date and time. |
| ERP completion | ERP error on visit completion | Could not post the visit to ERP (code: {code}, type: {type}). Check cash register / payroll / inventory settings and re-post the visit. |
| LOYALTY_* / PAPERLESS_* | коды title **не** русифицировать | убрать только хвост `trace_id=` из description |

Существующие RU ряды **не** мигрировать в A (NEXT `A2-SEED`). FE sanitize прячет UUID; заголовок «Обработать no-show» на демо-БД останется до сида.

Pytest на `create_system_task_for_*` **нет** — Q7 создаёт `tests/application/test_tasks_event_handlers.py`. `tests/services/test_booking_completion_service.py` — обновить, если ассертит RU/concat.

### A5 Money / phone — **отозвано ветвление от locale**

- ₽ не трогать.  
- Маска `+7` **не** становится `+1` при EN.  
- Q3: `en/schedule.json` `fullNamePlaceholder` → `"For example, Jane Doe"`; RU не трогать. Добавить `phonePlaceholder: "+7..."` в en **и** ru; `SchedulePage` `placeholder={t("phonePlaceholder")}`.

### A4 VK

Скрыть create + OAuth (FE **и** owner API POST). `CHANNEL_TYPE_OPTIONS` без `VK_BOT`, labels = `omniChannelTypeLabel`. BE: `POST /owner/channels` → 400 `omni_channel_type_not_creatable` для `VK_BOT`. Исторический канал — read-only/generic credentials. E2E без VK_BOT create. Inbox icon VK → generic (Q10). `omniChannelTypeLabel("VK_BOT")` в тестах i18n **может** остаться.

---

## I1–I12 (экраны, которые меняем)

| # | Calendar | Tasks board | Patient modal | Omni thread |
|---|----------|-------------|---------------|-------------|
| I1 Command palette | N/A косметика | N/A | N/A | N/A |
| I2 Inline edit | N/A (форма события) | N/A статус=колонка | N/A | N/A |
| I3 Bulk | N/A | N/A эта волна | N/A | N/A |
| I4 Undo vs confirm | N/A | N/A | delete patient уже confirm | N/A |
| I5 Optimistic | N/A | не менять | N/A | N/A |
| I6 Saved views | N/A | stream в URL already I9 | N/A | N/A |
| I7 Row actions | N/A | kebab остаётся | menu остаётся | ctx menu остаётся |
| I8 Keyboard | text time focusable | N/A | tabs nowrap scroll | N/A |
| I9 Deep link | N/A | applies (stream query) | N/A | chat id already |
| I10 Non-blocking load | не менять | не менять | не менять | не менять |
| I11 Search | N/A | не менять | N/A | не менять |
| I12 Empty + CTA | не менять empty дня | **applies: create opens modal** | empty visits without CTA OK | empty thread already |

---

## Карта P1–P13

Без изменений состава. Исполнение — QUEUE rev 3 (полные карты литерал→ключ, не «минимум»).

---

## Domain Checklist (волна A)

- [ ] Law 8: нет UUID в task body UI и в подписи абонемента  
- [ ] Law 26: медкарта высота стабильна (включая ряд вкладок на 360)  
- [ ] Empty kanban CTA открывает create  
- [ ] Upload: structured `omni_*` + SVG deny  
- [ ] Кнопка disable на мутациях, которые трогаем (не расширять)  
- [ ] License: нет новых GPL deps  
- [ ] Law 11: async create/update календаря — существующие try/catch не вычищать  

---

## Приёмка A (`ui.locale=en`)

1. Calendar: chrome EN; набор `9` `3` `0` не превращается в `01:23` на третьей цифре; edit 24.08 14:00 — смена времени не сбрасывает дату; all-day без time fields. Нет `datetime-local`, нет `type="time"` как единственного поля.  
2. Tasks: ровно одна кнопка accessible name New task на `/admin/tasks`; нет `trace_id=` в description; колонки без тройки серых «0»; канбан-карточка без status pill и без тени. Details могут сохранить tint.  
3. Leads-log: `Leads (log)` (нет `titleOverride`).  
4. Patient modal: вкладки EN; main vs notes высота окна delta≈0 (измерить px); нет hex id пакета. New booking: не «Врач». Phone `+7...`. EN name Jane Doe.  
5. Staff-chat: Team chat / Members; нет «Чат команды».  
6. Sales: нет «CRM-воронка», «Выберите воронку», «Стадии не настроены», «Открытые/Успех/Потеряно», «AI‑рекомендации». ₽ в оценке оставить.  
7. Omni: короткие сообщения у края; voice `voice-*.webm` + octet-stream не generic fail.  
8. Channels create: нет VK_BOT; типы EN. Patient VK login скрыт.  
9. Finance ₽ как было.  
10. Нет commit агентом.

---

## Волна B / A2 / долги

Только в NEXT-файле. Здесь не дублировать пустыми строками без промпта.
