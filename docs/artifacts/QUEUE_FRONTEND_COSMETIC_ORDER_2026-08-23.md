# Очередь Cursor: косметический порядок (волна A) — rev 3

> **Как пользоваться:** прочитай ТЗ rev 3 целиком. Вставляй блоки `PROMPT Qn` **по батчам**. Следующий батч — только после STOP всех промптов предыдущего, если они делят файл/JSON.  
> **Закон:** только @DEV пишет код в Q1–Q10. Law 40 — нет commit/push.  
> **ТЗ:** [`FRONTEND_COSMETIC_ORDER_TZ_2026-08-23.md`](./FRONTEND_COSMETIC_ORDER_TZ_2026-08-23.md)  
> **Диагноз:** [`FRONTEND_AESTHETICS_AUDIT_2026-08-23.md`](./FRONTEND_AESTHETICS_AUDIT_2026-08-23.md) §9–§10  
> **Вне A:** [`FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md`](./FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md)

```
BATCH 1 (параллель):  Q1 ∥ Q2 ∥ Q4 ∥ Q5 ∥ Q7     (+ Q6 можно сразу)
BATCH 1b:             Q3  после STOP Q1 и Q2
BATCH 2 (параллель):  Q8 ∥ Q9                     после STOP Q4
BATCH 3:              Q10                         после STOP Q8
BATCH 4:              Q11 → Q12 → Q13
```

Не вставлять Q3 «вместе с Q1 на всякий случай правят schedule.json». Не вставлять Q8 пока Q4 не STOP. Не вставлять Q10 пока Q8 не STOP.

---

## PROMPT Q0 — @LEAD чтение

```
@LEAD Код не писать.

Прочитай с диска (не память сессии):
- docs/artifacts/FRONTEND_COSMETIC_ORDER_TZ_2026-08-23.md (rev 3: D4 text+blur не type=time; JSON-владение; батчи)
- docs/artifacts/FRONTEND_AESTHETICS_AUDIT_2026-08-23.md §9 R1–R15 и §10 R16+
- docs/artifacts/QUEUE_FRONTEND_COSMETIC_ORDER_2026-08-23.md этот файл
- docs/artifacts/ADMIN_I18N_EN_ROADMAP.md §0 (default en; деньги/телефон = регион)

STOP: таблица P1–P13 «принято». A5 (телефон ≠ EN) не переоткрывать. Не код.
```

---

## PROMPT Q1 — @DEV Calendar (tsx + test; JSON не писать)

```
@DEV Волна A / P1. Пиши код. Не commit.

ВЛАДЕЕШЬ:
- frontend/src/admin/pages/AdminStaffCalendarPage.tsx
- frontend/src/admin/pages/__tests__/AdminStaffCalendarPage.test.tsx (создай)

НЕ ТРОГАТЬ: SchedulePage, PatientEntityDrawer, schedule.json, common.json, datetime-local как целевой виджет.

Прочитай с диска:
1. ТЗ CONTRACT D4 rev 3 (text+blur; почему не type=time) и владение JSON
2. Аудит §3.5
3. AdminStaffCalendarPage.tsx ЦЕЛИКОМ (formatTimeHHMMInput L87–94; create mask ~1406; edit datetime-local ~1338)
4. en/schedule.json staffCal — ключи УЖЕ есть. Prefix t("staffCal.…"). Точные имена с диска: title, intro, soundOn, soundOff, enableSound, emptyTitle, emptyHint, allDay, eventsOn, events, emptyDayTitle, emptyDayHint, editEvent, newEvent, event, task, participants, acked, eventTitle, description, meetingParticipants, replaceListHint, whoSeesHint, staffPlaceholder, reminderLabel, reminderHint, remindNone, remind5, remind15, remind30, remind60, remind120, remind1440, start, end, date, startTime, endTime, pickStartTime, pickEndTime, taskPicked, save, create, linkTaskTitle, list, openTasks, myTasks, allTasks, search, searchTaskPlaceholder, nothingFound, nothingFoundHint, wheelHint, conflictContinue, overlapWarning, clear, done, errors.titleRequired, errors.needTimes, errors.badTime, errors.endAfterStart, errors.overlap, errors.createFailed, errors.saveFailed. Не invent clear/done — они уже есть.
5. CompactMonthPicker.tsx: t(`calendar.weekdays.${key}`) при useTranslation("common")
6. frontend/src/i18n/testUtils.tsx renderWithI18n
7. Образец моков: frontend/src/admin/pages/__tests__/AdminTasksPage.test.tsx (QueryClient + Mantine + MemoryRouter)

Глобально: event.title / description / имена сотрудников — data. Не dayjs.locale на module scope.

Сделать:
A. const { t } = useTranslation("schedule"); weekdays: t("calendar.weekdays.mon", { ns: "common" }) и далее tue…sun. Не хардкод ["Пн","Вт",…].
B. Карта литерал → ключ (обязательная, не оставляй ни одной user-facing строки):
   ContextBar «Календарь» → staffCal.title
   «Звук: включён/выключен» → staffCal.soundOn / staffCal.soundOff
   EmptyState «Нет событий» / hint → staffCal.emptyTitle / emptyHint
   «Весь день» → staffCal.allDay
   Drawer «События {{date}}» / «События» → staffCal.eventsOn / events
   «В этот день нет событий» / hint → staffCal.emptyDayTitle / emptyDayHint
   «Редактировать событие» / «Новое событие» / «Событие» → staffCal.editEvent / newEvent / event
   Badge «Задача» → staffCal.task
   «Заголовок» / «Описание» → staffCal.eventTitle / description
   «Участники совещания» + два hint → meetingParticipants, replaceListHint, whoSeesHint
   placeholder сотрудников → staffCal.staffPlaceholder
   «Напоминание» + options → reminderLabel, reminderHint, remindNone, remind5, remind15, remind30, remind60, remind120, remind1440
   «Начало» / «Окончание» → start / end
   aria колеса → pickStartTime / pickEndTime
   «Выбрана задача» → taskPicked
   «Сохранить» / «Создать» → save / create
   modal «Связать с задачей» → linkTaskTitle
   «Список» / «Открытые» / «Мои» / «Все» → list / openTasks / myTasks / allTasks
   «Поиск» / placeholder задачи → search / searchTaskPlaceholder
   «Ничего не найдено» + hint → nothingFound / nothingFoundHint
   modal title времени → startTime / endTime
   setFormError «Введите заголовок.» → errors.titleRequired
   «Выберите время начала и окончания.» → errors.needTimes
   «Некорректное время.» → errors.badTime
   «Время окончания должно быть позже начала.» → errors.endAfterStart
   overlap → errors.overlap ; warning → overlapWarning / conflictContinue
   create/save failed fallback → errors.createFailed / saveFailed
   Кнопки колеса Clear/Done → staffCal.clear / staffCal.done (ключи есть)
   «Подтвердили» / «Участники» в чипе → acked / participants
C. Если литерала нет в staffCal — НЕ редактируй JSON. STOP в отчёте со списком. Не invent ns.
D. Удалить formatTimeHHMMInput. Timed create+edit: дата в отдельном state; два TextInput type="text" inputMode="numeric" autoComplete="off" placeholder="09:30". onChange: только [0-9:], max 5, БЕЗ pad трёх цифр. onBlur: 3 цифры 930→09:30; 4 цифры 0930→09:30. Не type="time". Не datetime-local. Edit: разрезать startsLocal/endsLocal по "T" на date+time; на submit склеить как сейчас API. All-day: time fields не рендерить (ветка уже есть). Колесо пишет в тот же HH:mm. Overlap не disable.
E. Тест AdminStaffCalendarPage.test.tsx:
   - renderWithI18n locale en + мок хуков месяца (пустая сетка ок)
   - открыть New event: нет текста «Участники» / «Подтвердили» / «Календарь» как литерала (заголовок страницы = Calendar)
   - all-day: в форме нет input type="time" и нет datetime-local
   - не тестируй удалённую маску

STOP-гейт:
- В JSX/пропах этого tsx нет кириллицы в кавычках (JSDoc/комменты можно).
- grep файла: нет formatTimeHHMMInput, нет datetime-local, нет type="time".
- В отчёте: сценарий edit дата 2026-08-24 + 14:00, смена времени не трогает date state.
- schedule.json не изменён.
- Не commit. Не другие страницы.
```

### Q1 STATUS — audit 2026-08-24 (STOP)

Q1 **закрыт по коду**. Канон на диске (очередь выше содержит алиасы имён — **не** переписывать `schedule.json` под алиасы):

| Очередь / ТЗ | Диск |
|--------------|------|
| `AdminStaffCalendarPage.tsx` | `frontend/src/admin/pages/AdminStaffCalendarPage.tsx` |
| `AdminStaffCalendarPage.test.tsx` | `frontend/src/admin/pages/__tests__/AdminStaffCalendarPage.test.tsx` |
| prefix `staffCal.*` | `staffCal.*` в `en\|ru/schedule.json` (Q1 не писал) |
| `renderWithI18n` | `renderWithI18n` (`frontend/src/i18n/testUtils.tsx`) |

Проверено: нет `datetime-local` / `type="time"` / live-pad 3 цифр; create+edit клеят `createSelectedDayIso` + `HH:mm`; overlap warning, слоты колеса не disable overlap; submit overlap как backend, edit исключает self; колесо scrollIntoView на create **и** edit. A5 не открывали.

Остаток вне Q1 → `FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md` (CAL-MULTIDAY, C1 grep, BATCH 1 Q2∥Q4∥Q5∥Q7). **Не стартовать Q3** пока Q1+Q2 STOP.

---

## PROMPT Q2 — @DEV PatientEntityDrawer

```
@DEV Волна A / P3 + Law 8. Пиши код. Не commit.

ВЛАДЕЕШЬ: PatientEntityDrawer.tsx; en+ru/directory.json ТОЛЬКО patientDrawer.* (и только если ключа нет).
НЕ ТРОГАТЬ: entityDrawerChrome.tsx, BookingEntityDrawer.tsx, doctorDrawer, SchedulePage.

Прочитай:
1. ТЗ D3 rev 3 (440 + nowrap tabs + minHeight 560) SC3 SC5
2. Аудит §3.8
3. PatientEntityDrawer.tsx ЦЕЛИКОМ
4. en/directory.json patientDrawer L41–123 + корень print, copy, delete, actions, save, cancel
5. ru/directory.json тот же блок
6. BookingEntityDrawer.tsx только образец: BOOKING_MODAL_TABS_SCROLL_H = 440, ScrollArea h={...}, content minHeight 560, Tabs.List

Глобально: ФИО/телефон/даты визитов — data. currency/₽ — region. Не t() на значения API.

Сделать:
A. useTranslation("directory").
B. Карта (каждая строка; ключ ns directory). Корневые: print, copy, delete, actions, save, cancel.

   «Новый пациент» → patientDrawer.newTitle  (и displayName fallback)
   «Редактировать пациента» → editTitle
   «Скоро день рождения» / « — Скоро день рождения» → birthdaySoon (префикс « — » в JSX ок)
   «Баланс бонусов: …» → bonusBalance {{balance}} {{currency}}  (символ валюты из data)
   «Должник» → debtor
   «Склонен к отменам» → cancellationProne
   «LTV — при наличии API» → ltvSoon
   aria «Действия» → t("actions")
   «Печать» → t("print")
   «Скопировать» → t("copy")
   «Удалить» → t("delete")
   вкладки: tabMain tabVisits tabFinance tabSubscriptions tabNotes tabComms
   «Телефон» → phone
   «ФИО» → fullName
   «Дата рождения» → dateOfBirth
   «Дополнительно» + hint «Пол, категория…» → extras / extrasHint
   «AI‑обзор» / «Загрузить AI‑обзор» / aiUnavailable / aiFailed → aiOverview / loadAi / aiUnavailable / aiFailed
   «Контактные данные» → contact
   «Дата рождения: {{date}}» → birthdayLine
   «Сохранить» / «Отмена» → save / cancel
   saveFailed
   saveToSeeVisits / noVisits
   th: date time doctor service status amount
   saveToSeeFinance / balance / subscriptionsCount / financeHint
   saveToSeeSubs / noSubs
   «Пакет {slice}» → package  ИЛИ packageRemain; FORBIDDEN subscription_package_id.slice
   remainingVisits_* / remainingAmount / expires
   addFamily / subscription / subscriptionPlaceholder / familyPatient / familyPatientPlaceholder
   кнопка «Добавить» в family modal: если нет ключа — ДОБАВЬ en+ru patientDrawer.add = "Add" / "Добавить"
   saveToSeeChart / visitsBlock / notesMarkdown / addVisit / notes / noChartVisits
   diagnoses / diagName / description / addDiagnosis / diagnosis / noDiagnoses
   files / downloadFailed / uploadFile / file / type / size / download / unknownError / noFiles / chartLoadFailed
   commsHint / openInChat

C. Геометрия:
   const PATIENT_MODAL_TABS_H = 440;
   Удалить ScrollArea.Autosize и mah={560}.
   Каждый Tabs.Panel = <ScrollArea h={PATIENT_MODAL_TABS_H} offsetScrollbars type="scroll">.
   Header профиля + Tabs.List СНАРУЖИ скролла.
   Tabs.List: flexWrap nowrap, overflowX auto, БЕЗ grow (6 вкладок). Одна линия высоты.
   Shell content minHeight: 560 как у booking.
   Цель: смена main→notes не меняет высоту окна модалки.

D. Нет ключа → пара en+ru в patientDrawer. Не новый ns. Не правь doctorDrawer.

STOP: вкладки EN; grep кавычек с кириллицей в JSX пуст (комменты можно); нет .slice(0, 8) на package id; нет Autosize/mah; PATIENT_MODAL_TABS_H = 440. Не commit.
```

### Q2 STATUS — 2026-08-24 (STOP, audit+fix)

Q2 **закрыт по коду + аудит 2026-08-24**. Канон: `frontend/src/admin/components/entity/PatientEntityDrawer.tsx`; i18n `patientDrawer.*` + корни `print/copy/delete/actions/save/cancel`; ключи `patientDrawer.add`, `patientDrawer.vip`, `patientDrawer.familyAddFailed`. Chrome booking/doctor/schedule не трогали.

Проверено: `PATIENT_MODAL_TABS_H = 440`; панели в `ScrollArea h=`; header+`Tabs.List` снаружи; list `nowrap` + `overflowX auto` + `minHeight: 40` без grow; modal `content.minHeight: 560`, drawer `body.minHeight: 560`; нет `Autosize`/`mah`; нет `subscription_package_id.slice(0, 8)` (лейбл `package` / `packageRemain`). Визиты: имена через `displayPersonName` (не UUID), статус через `bookingStatusLabel`. Запросы визитов `enabled` только при телефоне; ошибки loyalty/bookings/family/chart-мутаций — `QueryErrorAlert`, не вечный skeleton. A5 не открывали. Не commit.

Остаток вне Q2 (не стартовать Q3 из этого статуса): меню print/copy/delete — chrome без onClick → NEXT `Q2-MENU-STUB`; колонка NPS всегда «—»; ₽ в сумме визита (B-CCY); имя пакета подписки не в DTO.

---

## PROMPT Q3 — @DEV Booking drawer + role map + leads-log + EN copy имени

```
@DEV Волна A / P2 P4 P5 P13. Пиши код. Не commit.

ВЛАДЕЕШЬ:
- BookingEntityDrawer.tsx
- SchedulePage.tsx (только displayRole на create ~703 и phone placeholder ~124)
- AdminLeadsLogPage.tsx
- frontend/src/shared/doctorRoleI18n.ts (новый)
- en/schedule.json: fullNamePlaceholder + новый корневой phonePlaceholder
- ru/schedule.json: только добавить phonePlaceholder "+7..." (fullNamePlaceholder RU не менять)

НЕ ТРОГАТЬ: PatientEntityDrawer, AdminTasksPage.tsx (не «чини» leadsTitle внутри Tasks), directory.json, API/DTO doctor.

Прочитай:
1. ТЗ CONTRACT display_role + A5 + образец chatI18n.ts (i18n.t, не хук)
2. AdminLeadsLogPage.tsx — titleOverride="Лиды (лог)"
3. BookingEntityDrawer.tsx ЦЕЛИКОМ (кириллица не только «Врач»)
4. SchedulePage.tsx create: displayRole={…display_role} ~703; placeholder="+7..." ~124
5. frontend/src/api/types.ts specialist_role — УЖЕ есть
6. src/application/dto/doctor_dto.py DoctorRead.specialist_role — УЖЕ есть
7. en+ru schedule.json drawer.* , specialist, fullNamePlaceholder
8. en directory.json doctorDrawer.roles.* — ТОЛЬКО ЧИТАТЬ
9. frontend/src/shared/bookingStatusMeta.ts — statusCfg.label УЖЕ i18n (bookings.status.*). Не заменять на drawer-ключи. Fallback «Статус» → drawer.status.

Сделать:
A. AdminLeadsLogPage: удалить проп titleOverride полностью.
   AdminTasksPage УЖЕ делает title={titleOverride ?? (mode === "leads-log" ? t("leadsTitle") : t("title"))}.
   После удаления override заголовок сам станет t("leadsTitle") = "Leads (log)". НЕ редактируй AdminTasksPage.

B. BookingEntityDrawer: useTranslation("schedule"). Карта → drawer.* :

   title модалки «Запись» → drawer.title
   вкладки Детали / Услуги и чек / Расходники / Задачи → details / services / consumables / tasks
   «Сводка» → summary
   fallback бейджа «Статус» → status  (само значение бейджа = statusCfg.label, не хардкод)
   «Есть комментарий администратора» → hasAdminComment
   «Пациент» → patient
   «Телефон: {phone}» → phoneLine {{phone}}
   «Баланс: {n} {ccy}» → balanceLine {{balance}} {{currency}}  (символ не переводить)
   «След. визит — при API» → nextVisitApi
   «Врач» → doctor
   «Специализация: {v}» → specializationLine {{value}}
   «Рабочие смены — во вкладке…» → shiftsHint
   «Дата и время» → dateTime
   «Услуга» → service
   aria «Статус посещения» → visitStatus
   copied / copyVisitLink
   adminComment / adminCommentPlaceholder / saveComment
   changeSlot / cancelBooking
   «Дата, время и врач» → dateTimeDoctor
   «Дата» / «Время» / «Врач» / aria «Врач для записи» → (schedule.date уже корень ИЛИ drawer; используй drawer где есть: нет date в drawer — t("date") ns schedule корень)
   «Отмена» / «Сохранить» → cancel / save
   th «Услуга» / «Сумма» → service / amount
   multiServiceHint / noConsumables / material / qtyPerService / tasksHint
   Роль врача в карточке: doctorRoleLabel(doctor), НЕ display_role.

C. Создай frontend/src/shared/doctorRoleI18n.ts точно по ТЗ (i18n.t, не useTranslation). Экспортируй doctorRoleLabel.

D. SchedulePage create: displayRole={doctorRoleLabel(doctors.find(...))} когда doctor найден; иначе undefined (компонент сам t("specialist")).

E. en/schedule.json fullNamePlaceholder: "For example, Jane Doe". RU fullNamePlaceholder не менять.

F. Добавь phonePlaceholder: "+7..." в en И ru schedule.json (корень, рядом с "phone"). SchedulePage: placeholder={t("phonePlaceholder")}. НЕ ветвить +1 от ui.locale.

STOP: Leads (log); New booking при en без «Врач»; grep BookingEntityDrawer кавычки кириллицы пуст; API/DTO не менять; directory.json не менять; AdminTasksPage не менять. Не commit.
```

### Q3 STATUS — 2026-08-24 (STOP)

Q3 **закрыт по коду**. Канон: `BookingEntityDrawer.tsx` + `doctorRoleI18n.ts` (`i18n.t`, не хук); `AdminLeadsLogPage` без `titleOverride`; create на `SchedulePage`: `displayRole={createDoctor ? doctorRoleLabel(createDoctor) : undefined}`; `phonePlaceholder` "+7..." en+ru; en `fullNamePlaceholder` — как в `en/schedule.json` на диске (RU не трогали). `directory.json` / API / `AdminTasksPage` не меняли. Не commit.

### Q3 AUDIT — 2026-08-24 (после STOP)

Проверено по диску. Доработано в этом проходе:

- `doctorRoleLabel`: поля DTO `specialist_role` / `specialist_role_custom_name`; `display_role` не рендерится; нет ключа роли → `schedule.specialist`; `nurse`/`therapist` → `doctorDrawer.roles.*`. Тесты: `frontend/src/shared/__tests__/doctorRoleI18n.test.ts`.
- Law 8: услуга — имя или «—» на UUID; расходник без имени товара — «—» на UUID.
- Ошибки patch/status и query расходников через `QueryErrorAlert`; skeleton расходников по `isLoading`.
- Черновик notes сбрасывается только при смене `booking.id`.
- Loyalty hover: `isLoading` + `isError` (disabled query не держит вечный skeleton).
- Hover врача: роль через helper + отдельная строка `specialization`, если заполнена.

Вне Q3 (NEXT): `Q3-CONSUMABLE-NAME`, `Q3-RTL`, `Q3-DISPLAY-ROLE-OTHER`. Q4 не стартовали.

---

## PROMPT Q4 — @DEV Staff chat i18n

```
@DEV Волна A / P6. Пиши код. Не commit.

ВЛАДЕЕШЬ: AdminStaffChatPage.tsx
JSON: не писать chat.json, если хватает staff.* (хватает). Load-fail → common.errors.loadFailed.
НЕ ТРОГАТЬ: AdminOmniChatPage, пузыри, adminChatChrome.

Прочитай:
1. AdminStaffChatPage.tsx ЦЕЛИКОМ
2. en/chat.json staff.* L192–227 + корень send, cancel, close, create
3. en/common.json errors.loadFailed
4. chat.errors.uploadFailed

Сделать: useTranslation("chat") + t(..., { ns: "common" }) только для loadFailed.

Карта литерал → ключ (обязательная):

   subtitle L97–99 «Внутренний чат клиники…» → staff.subtitle  (заменить весь Text, не оставляй <strong>голосовые</strong> снаружи t; ключ уже цельная фраза)
   fallback «Чат персонала» → staff.fallbackTitle
   ContextBar «Чат команды» (все 3 места) → staff.title
   EmptyState «Нет комнат» → staff.emptyRoomsTitle
   description «Не удалось загрузить каналы чата.» → t("errors.loadFailed", { ns: "common" })
     НЕ staff.emptyRoomsHint (тот про «создайте группу» — другой смысл)
   «Чаты» → staff.chats
   placeholder «Поиск чатов…» → staff.searchChats
   «Новая группа» (кнопка и title модалки) → staff.newGroup / staff.groupTitle по месту (кнопка newGroup, modal title groupTitle)
   «Ничего не найдено» (оба) → staff.nothingFound
   pick «Выберите чат» / hint → staff.pickTitle / pickHint
   empty thread «Пока пусто» / hint → emptyThreadTitle / emptyThreadHint
   aria Файл / Фото / Аудио / title аудио → fileAria / photoAria / audioAria / audioTitle
   placeholder «Сообщение…» → composerPlaceholder
   «Отправить» → t("send")
   «Пригласить» (кнопка списка и modal) → staff.invite
   DM title «Личный чат» → dmTitle
   «Сотрудник» / «Выберите коллегу» → colleague / pickColleague
   «Персонал клиники» → clinicStaff
   «Поиск по имени или email…» → searchNameEmail
   inviteTitle / inviteHint
   groupHint / groupName / groupNamePlaceholder / members / pickColleagues
   «Отмена» → t("cancel")
   «Закрыть» → t("close")
   «Создать» → t("create")
   setAttachError fallback «Не удалось загрузить файл» → errors.uploadFailed

Тела сообщений комнат — data. Не редизайн пузырей.

STOP: в кавычках JSX нет кириллицы (JSDoc можно). chat.json не изменён без нужды. Не commit.
```

### Q4 STATUS — 2026-08-24 (STOP)

Q4 **закрыт по коду**. Канон: `frontend/src/admin/pages/AdminStaffChatPage.tsx`; `useTranslation("chat")`; load-fail → `t("errors.loadFailed", { ns: "common" })` на `QueryErrorAlert` (не `staff.emptyRoomsHint`); upload fallback → `errors.uploadFailed`. Ключи `staff.*` / `send|cancel|close|create` — как в `en/chat.json` на диске. `chat.json` не меняли. `AdminOmniChatPage`, пузыри, `adminChatChrome` не трогали. Grep кириллицы в кавычках JSX страницы — пуст. Не commit.

### Q4 AUDIT — 2026-08-24 (после STOP)

Проверено по диску. Доработано в этом проходе (Q4 scope, не Q5):

- Law 8: подписи коллег через `displayPersonName`, не `id.slice(0, 8)`.
- Мутации send/DM/invite/group: `onError` + `QueryErrorAlert` в модалках/композере; finder DM закрывается только на success.
- Deep-link DM: deps `mutate`/`isPending`, не объект мутации целиком.
- Геометрия: subtitle не в nowrap breadcrumbs `ContextBar`; список комнат `flex` (не `h={300}`); колонки `wrap` + `minWidth` треда на 360.
- Empty rooms: CTA `staff.newGroup`. Даты сообщений от `useUiLocale()`.
- i18n: все `staff.*` есть в en+ru; `chat.json` по-прежнему не меняли.

Вне Q4 (NEXT): `Q4-RTL`, `Q4-BUBBLE` (намеренно не редизайн). Q5 не стартовали.

---

## PROMPT Q5 — @DEV Sales CRM i18n

```
@DEV Волна A / P7. Пиши код. Не commit. Не редизайн колонок.

ВЛАДЕЕШЬ: AdminSalesPipelinePage.tsx; en+ru/crm.json (pipeline.aiToolUnavailable если нет).
₽ в columnMeta / estimated / actual — region, оставь символ.

Прочитай ЦЕЛИКОМ:
1. AdminSalesPipelinePage.tsx (нет useTranslation; кириллица не только фильтры)
2. en/crm.json pipeline.* errors.* status.*
3. ru/crm.json
4. frontend/src/shared/crmI18n.ts — если мапит статусы, используй; не дублируй третий словарь

Сделать: useTranslation("crm"). Даты: useUiLocale() → toLocaleDateString("en-US"|"ru-RU"), не голый toLocaleDateString().

Карта (не «минимум» — это дыра rev 2). Имена стадий/лидов/rationale с API — data.

   ContextBar «CRM‑воронка продаж» (оба) → pipeline.title
   «Фильтры и выбор воронки» → pipeline.filters
   suffix « (по умолчанию)» → pipeline.defaultSuffix  (p.name + defaultSuffix)
   placeholder «Выберите воронку» → pickPipeline
   «Стадия» / «Все стадии» → stage / allStages
   «Статус» / «Все статусы» → pipeline.status / allStatuses
   options Открытые / Успех / Потеряно → pipeline.statusOpen / statusWon / statusLost
     (корневой status.open = "Open" тоже ок; не смешивай в одном Select)
   «Поиск» / placeholder «Имя/комментарий/источник» → pipeline.search / searchPlaceholder
   strictKanban label + hint абзац L560–567 → strictKanban / strictHint
   template «Переход заблокирован…» → t("pipeline.strictBlocked", { from, to })
   semantic reject → t("errors.semanticRejected", { from, to })
   «Ошибка смены стадии» → errors.stageChangeFailed
   emptyStagesTitle / emptyStagesHint
   pickLeadTitle / pickLeadHint
   leadMissingTitle / leadMissingHint
   «Источник: …» → pipeline.source {{source}}
   estimatedTooltip / estimated {{amount}}  (₽ в ключе оставить)
   actualTooltip / actual
   actualZeroOpen / actualZeroWon  (карточка) и actualZeroOpenDetail / actualZeroWonDetail (детали)
   «Создан:» → pipeline.created {{date}}
   «Загрузить ещё» → loadMore
   «Открыть чат» tooltip + кнопка + aria «Чат» → openChat / chatAria
   «AI‑рекомендации» → aiTitle
   title «Недостаточно прав или backend‑tool недоступен.» → ДОБАВЬ pipeline.aiToolUnavailable
     en: "Not enough permissions or the backend tool is unavailable."
     ru: тот же смысл
   «Резюме лида» / «Следующая стадия» → aiSummary / aiNextStage
   «mode: …» → aiMode {{status}}
   «confidence: N%» → confidence {{pct}}
   «Рекомендованная стадия:» → suggestedStage {{name}}  (name = stage.name data или —)
   «Применить» / «Игнорировать» → apply / ignore
   createTask / aiTaskTitle («Связаться с клиентом по лиду»)
   prepaymentLink / prepaymentCopied
   notes / noNotes / notePlaceholder / saveNote
   copyFailed / aiActionFailed — если есть тосты с RU, посади на эти ключи

STOP: при en нет «CRM-воронка», «Выберите воронку», «Стадии не настроены», «Открытые», «Успех», «Потеряно», «AI‑рекомендации», «Загрузить ещё». ₽ в оценке остаётся. Не commit.
```

### Q5 STATUS — 2026-08-24 (STOP)

Q5 **закрыт по коду**. Канон: `frontend/src/admin/pages/AdminSalesPipelinePage.tsx`; `useTranslation("crm")` + `useUiLocale()` → `toLocaleDateString("en-US"|"ru-RU")` / `toLocaleString(dateLocale)`; статусы лидов через `crmLeadStatusLabel` (`crmI18n.ts`). Добавлен `pipeline.aiToolUnavailable` в `en|ru/crm.json`. Карта литералов из промпта — на ключи `pipeline.*` / `errors.*`. Имена стадий/лидов/rationale — data с API. Grep кириллицы в `AdminSalesPipelinePage.tsx` — пуст. Тесты: `AdminSalesPipelinePage.test.tsx` на `renderWithI18n` locale `en`. Не commit.

### Q5 AUDIT — 2026-08-24 (после STOP)

Проверено по диску (@LEAD + @QA_ARCH + @FRONTEND). Доработано в этом проходе:

| Вектор | Было | Сделано |
|--------|------|---------|
| Law 8 | `suggested_stage_id` UUID в UI при отсутствии stage.name | fallback `—`, не UUID |
| Ключи на диске без UI | `emptyPipelinesTitle/Hint` | EmptyState при `pipelines.length === 0` |
| Law 15 / Q4 parity | drag stage error только в strict; мутации без feedback | `stageChangeFailed` всегда в Alert; `QueryErrorAlert` для pipelines/stages/lead load, AI refetch/mutations, save note |
| Регион сумм | `estimated/actual` сырые строки API | `formatCrmAmount` + `Intl.NumberFormat(dateLocale)`; ₽ в ключах |
| Гонка/состояние | `noteText` не сбрасывался при смене лида; clipboard `setTimeout` без cleanup | reset на `selectedLeadId`; `copyFailed` + effect cleanup |
| Геометрия | заголовок колонки `wrap="nowrap"` | `wrap="wrap"` — meta не давит badge |
| Кнопка заметки | без `disabled` на пустом draft | `disabled={!noteText.trim() \|\| isPending}` |

**Вердикт @QA_ARCH:** 🟢 по i18n-карте Q5 и error/empty states в scope страницы.

**Вне Q5 (NEXT):** `Q5-KANBAN-COL-ERR` (per-column `loadColumnsFailed`), `Q5-RTL`, `B-CCY` (валюта клиники vs ₽ в ключах). Q6 не стартовали.

---

## PROMPT Q6 — @DEV Tasks FE

```
@DEV Волна A / P8 D1 SC3. Пиши код. Не commit. Не backend. Канбан остаётся.

ВЛАДЕЕШЬ:
- AdminTasksPage.tsx
- TaskDetailsView.tsx
- taskStatusSemantic.ts
- frontend/src/admin/pages/__tests__/AdminTasksPage.test.tsx
- en+ru/tasks.json: list.boardTitle, view.copySupportId

НЕ ТРОГАТЬ: Q10 файлы, omni, calendar.

Прочитай:
1. ТЗ D1 rev 3 (канбан quiet ≠ details surface)
2. AdminTasksPage.tsx: ContextBar New task ~935; toolbar New task ~1132; empty onClick ~2888; KanbanColumn badges ~2217–2228; StreamPageShell gradient ~2302; list.title ~2863; placeholder VK ~1727 и ~1831
3. TaskDetailsView.tsx description raw ~251
4. taskStatusSemantic.ts taskStatusCardSurface
5. AdminTasksPage.test.tsx: getAllByRole("button", { name: "New task" })[0] ~354
6. en/tasks.json list / empty / wip / priority / view.noTrace

Сделать:
A. Удалить кнопку New task из filter toolbar (~1132). ContextBar (~935) оставить. Тест: screen.getByRole("button", { name: "New task" }) — ровно 1 (не getAllByRole[0]).
B. empty.create onClick → setCreateOpened(true).
C. en+ru list.boardTitle "Board" / "Доска". На доске t("list.boardTitle"), не list.title.
D. Колонка: LIMIT badge только если wipLimit != null. slaOverdue/aging badges только если count>0; иначе не рендерить. Счётчик задач колонки оставить.
E. TaskKanbanCard: не taskStatusCardSurface. Добавь taskKanbanQuietSurface() в taskStatusSemantic.ts: hairline 1px var(--calendar-card-border), background var(--bg-card) или white, без boxShadow, без tint, без left bar. Карточка без status Badge. Priority текстом xs через t("priority.low|medium|high|urgent"), minWidth под Urgent. Blocked — одна muted pill.
   TaskDetailsView Paper: оставь taskStatusCardSurface.
F. StreamPageShell: удали linear-gradient 12px; hairline/solid token.
G. Needs approval: если approvalQueueTasks.length === 0 — не занимать место блоком (не серый ноль).
H. Sanitize description в TaskDetailsView (и превью карточки, если там сырой description):
   replace /\s*trace_id=[0-9a-fA-F-]{8,}(?:\s+event_id=[0-9a-fA-F-]{8,})?\.?/g
   и одиночный /\s*event_id=[0-9a-fA-F-]{8,}\.?/g
   Не вырезать UUID без префикса.
   Если task.trace_id: кнопка/меню t("view.copySupportId") en "Copy support ID" / ru «Копировать ID поддержки»; clipboard.writeText(task.trace_id). Не в абзаце description.
I. Placeholders ~1727 ~1831: "TELEGRAM_BOT / WHATSAPP / EMAIL" — без VK.

STOP: один New task; тест зелёный; нет UUID в модалке details; канбан-карточка без тени/tint; details surface не сломан. Не commit.
```

### Q6 STATUS — 2026-08-24 (STOP)

Q6 **закрыт по коду**. Канон: `AdminTasksPage.tsx`, `TaskDetailsView.tsx`, `taskStatusSemantic.ts` (`taskKanbanQuietSurface`), `en|ru/tasks.json` (`list.boardTitle`, `view.copySupportId`). A–I выполнены: один `New task` в ContextBar; quiet kanban vs details surface; approval queue скрыт при `length === 0`; sanitize `trace_id`/`event_id` в description + кнопка copy support ID; VK убран из placeholders. Тесты `AdminTasksPage.test.tsx` — **12/12 pass** (+ shared unit tests). Не commit.

### Q6 AUDIT — 2026-08-24 (после STOP)

Проверено по диску (@LEAD + @QA_ARCH + @FRONTEND + @QA). Доработано в этом проходе:

| Вектор | Было | Сделано |
|--------|------|---------|
| Law 15 / Q5 parity | `copySupportId` без feedback при отказе clipboard | `view.copyFailed` en+ru + inline error в `TaskDetailsView` |
| DRY / тестируемость | `sanitizeTaskDescription` локально в `TaskDetailsView` | `shared/taskDescriptionSanitize.ts` + unit tests (trace/event/bare UUID) |
| D1 rev 3 контракт | quiet vs details surface только по коду | `taskStatusSemantic.test.ts` — shadow/left bar отличаются |
| Геометрия колонки | badge-группа без `wrap` | `wrap="wrap"` на WIP/SLA/aging Group |
| Priority minWidth | `3.25rem` — риск обрезки «Срочно» | `3.5rem` под longest `priority.*` |
| Тест approval queue | только positive case | negative: скрыт при `status !== review` |
| i18n | `copyFailed` отсутствовал | en+ru в `tasks.json` |
| Гонка/состояние | `copySupportId` error не сбрасывался при смене `taskId` | reset в `useEffect` на смену задачи |

**Вердикт @QA_ARCH:** 🟢 по карте Q6 A–I, STOP-критериям и error/empty states в scope страницы.

**Вне Q6 (NEXT):** `Q6-RTL` (Tasks Kanban + stream pager на 360/RTL), `Q6-TASK-DETAILS-TEST` (отдельный vitest на `TaskDetailsView` sanitize/copy UI), `Q6-STREAM-ACCENT` (`StreamPageShell` принимает `accentColor`, но после F не использует — dead prop до RESKIN), `Q6-SEARCH-TRACE` (фильтр ищет по сырому `description` с `trace_id=` — не UI, но оператор может искать машинный хвост). Q7 не стартовали.

---

## PROMPT Q7 — @DEV Tasks BE

```
@DEV Волна A / P9 A1. Пиши код. Не commit. Не frontend. Не ai_task_manager_service.py. Не SQL UPDATE старых рядов.

ВЛАДЕЕШЬ:
- src/application/events/tasks_event_handlers.py
- src/application/services/booking_completion_service.py (только хвосты trace_id= в description и RU title ERP)
- tests: создай tests/application/test_tasks_event_handlers.py; обнови tests/services/test_booking_completion_service.py если ассертит concat/RU

Прочитай с диска:
1. tasks_event_handlers.py L98–120 cancel; L167–189 no-show (concat trace_id= + RU title)
2. booking_completion_service.py grep "trace_id=" (L311, 583, 750, 837) и title="ERP‑ошибка при завершении визита" L840
3. ТЗ A1 таблица шаблонов
4. Колонка Task.trace_id — уже передаётся в create_task(trace_id=...) — оставить

Сделать:
A. Убрать `description += f" trace_id=..."` везде в этих двух файлах. trace_id только аргумент create_task.
B. Шаблоны EN по ТЗ A1 (cancel / no-show / ERP). LOYALTY_* и PAPERLESS_* title-коды не русифицировать и не переименовывать; только убрать concat.
C. Тесты handlers: нет файла — создай. Минимально: вызов create_system_task_for_cancelled_booking / no_show с моком session/booking/TaskService ИЛИ интеграционный seed, если в проекте так принято. Assert: title EN из таблицы; "trace_id=" not in description; "event_id=" not in description. Grep tests на старые RU строки этих шаблонов — обнови.

STOP: новые задачи без UUID в description; затронутый pytest зелёный. Не commit.
```

### Q7 STATUS — 2026-08-24 (STOP)

Q7 **закрыт по коду**. Канон: `tasks_event_handlers.py` (EN cancel/no-show, без concat в description), `booking_completion_service.py` (убраны все `trace_id=` из description; ERP title/body EN по A1; LOYALTY_*/PAPERLESS_* — title без изменений). `trace_id` передаётся только в `create_task(trace_id=...)`. Тесты: `tests/application/test_tasks_event_handlers.py` (3), `test_booking_completion_service.py` — ассерты EN ERP + no `trace_id=` в description — **12/12 pass**. Не commit.

### Q7 AUDIT — 2026-08-24 (после STOP)

Проверено по диску (@LEAD + @ARCH + @QA_ARCH + @QA). Доработано в этом проходе:

| Вектор | Было | Сделано |
|--------|------|---------|
| STOP trace_id | только «нет в description» | интеграционный assert: `task.trace_id == actor.trace_id`, UUID не в description |
| A1 ERP body | ассерт по подстроке | `type: finance` в description (классификация `_classify_erp_error_code`) |
| Идемпотентность handlers | не покрыта | `test_cancelled_booking_skips_when_open_task_already_exists` |
| Grep scope | — | `src/`: `description += trace_id` / `f" trace_id=` — **0** в owned-файлах |
| TaskService | — | verified: `trace_id` → колонка, description as-is |

**Вердикт @QA_ARCH:** 🟢 по карте Q7 A–C и STOP (новые system tasks без UUID в description; `trace_id` в колонке).

**Вне Q7 (NEXT):** `A2-SEED` (старые RU-ряды в БД), `A2-AI` (`ai_task_manager_service.py` RU titles), `Q7-PAPERLESS-RU-BODY` (ветка `patient_id is None` — description RU, вне A1 EN), `Q7-LOYALTY-RU-BODY` (LOYALTY_ERP description RU по A1 — только убран concat). Q8 не стартовали.

---

## PROMPT Q8 — @DEV Omni пузыри + FE ошибки upload

```
@DEV Волна A / P10 D2 + FE часть P11. Пиши код. Не commit.

ВЛАДЕЕШЬ до STOP: AdminOmniChatPage.tsx, adminChatChrome.ts, en+ru/chat.json ТОЛЬКО errors.fileTypeDenied, fileEmpty, fileSvgForbidden.
Q9 не трогает эти файлы. Q10 после тебя — ТОЛЬКО функция иконки канала (~L75/L84), не JSX пузырей.

Прочитай:
1. ТЗ D2 (края, не 420px по центру; убрать 28px spacer и 56px meta)
2. AdminOmniChatPage.tsx список ~1047–1203; onError upload ~596–606 (уже claimed/channelUnresolved)
3. adminChatChrome.ts adminChatOutgoingBubbleStyle
4. chat.json errors.sendFileFailed / fileTooLarge; parseFastApiErrorBody кладёт nested detail.code → ApiErrorWithCode.code
5. client.ts L236: code = d.code ?? json.code — не ломай, не копируй парсер

Сделать:
A. Один контейнер пузыря. Incoming flex-start, outgoing flex-end. maxWidth min(68%, 36rem). py=8 px=12. gap списка 8. Не margin auto.
B. Удалить nested Paper p={6} + meta Paper width 56 + Box width 28.
C. Outgoing: adminChatOutgoingBubbleStyle (primary-alpha-12), не indigo fill. Incoming: surface+hairline.
D. Добавь en+ru:
   errors.fileTypeDenied / fileEmpty / fileSvgForbidden
   (fileTooLarge уже есть)
   onError upload: ветки err instanceof ApiErrorWithCode && err.code ===
     omni_file_type_denied → fileTypeDenied
     omni_file_empty → fileEmpty
     omni_file_too_large → fileTooLarge
     omni_svg_forbidden → fileSvgForbidden
   claimed / channelUnresolved не ломать. Fallback sendFileFailed.
E. Не VK, не MIME backend, не credentials.

STOP: короткая фраза не «шкаф»; иконка канала может остаться (Q10). Не commit.
```

### Q8 STATUS — 2026-08-24 (STOP)

Q8 **закрыт по коду**. Канон: `AdminOmniChatPage.tsx` (один пузырь D2, meta внутри, upload `omni_file_*` → i18n), `adminChatChrome.ts` (outgoing `--primary-alpha-12`, inbound surface+hairline), `en|ru/chat.json` (`errors.fileTypeDenied`, `fileEmpty`, `fileSvgForbidden`). A–E выполнены; VK/MIME backend/credentials не трогали. Тесты: `omniUploadErrors.test.ts` (2), `adminChatChrome.test.ts` (2), `i18nDefaultEn` — **pass**. Не commit.

### Q8 AUDIT — 2026-08-24 (после STOP)

Проверено по диску (@LEAD + @ARCH + @QA_ARCH + @FRONTEND + @QA). Доработано в этом проходе:

| Вектор | Было | Сделано |
|--------|------|---------|
| DRY / тестируемость | `omniFileUploadErrorMessage` локально в странице | `shared/omniUploadErrors.ts` + unit tests |
| D2 контракт chrome | outbound дублировал токен | `adminChatOmniOutboundBubbleStyle` → `adminChatOutgoingBubbleStyle()` |
| Документация chrome | устаревший комментарий «indigo fill» | актуальный D2-комментарий |
| i18n | новые ключи без assert в EN gate | `i18nDefaultEn` — fileTypeDenied/fileEmpty/fileSvgForbidden |
| Геометрия D2 | — | verified: нет spacer 28 / meta 56 / nested p={6}; `maxWidth: min(68%, 36rem)` |

**Вердикт @QA_ARCH:** 🟢 по карте Q8 A–E и STOP (короткая фраза у края, не «шкаф»).

**Вне Q8 (NEXT):** `Q8-BE-CODES` (FE готов к `omni_file_*`, но BE `_err` codes — Q9; до Q9 fallback `sendFileFailed`), `Q8-RTL` (Omni thread на 360/RTL — @QA_VISUAL Q12), `Q10-CHANNEL-ICON` (generic icon VK). Q9 не стартовали.

---

## PROMPT Q9 — @DEV Omni MIME backend only

```
@DEV Волна A / P11 A3 SC1 SC2 SC7. Пиши код. Не commit. Не AdminOmniChatPage.tsx. Не chat.json.

ВЛАДЕЕШЬ:
- src/application/services/omni_media_storage.py
- src/api/v1/routers/admin_omni_chat.py upload send_admin_omni_message_upload ~1746–1759 (+ _err уже L111)
- unit: tests/unit/test_omni_media_storage.py (создай, если нет)

Прочитай:
1. ТЗ CONTRACT omni MIME
2. allowed_omni_upload_mime (audio/* уже true; video/webm в кортеже; SVG false)
3. _err() L111–112: HTTPException(detail={"code","message"})
4. upload L1746–1759 СЕЙЧАС string detail: "Пустой файл" / "Файл слишком большой" / "SVG запрещён" / "Недопустимый тип файла…"
5. VoiceNoteRecorderButton.tsx имя файла voice-*.webm
6. parseFastApiErrorBody — совместимость: detail dict с code+message

Сделать:
A. Добавь sniff_omni_upload_mime(filename: str, content_type: str) -> str.
   Если ct пустой или application/octet-stream — по suffix:
     .webm → audio/webm
     .ogg → audio/ogg
     .mp3 → audio/mpeg
     .m4a → audio/mp4
     .wav → audio/wav
   иначе вернуть нормализованный ct.
   SVG (.svg/.svgz) не мапить в image/*.
B. В upload: ct = sniff...(file.filename, raw ct). Затем:
   empty raw → raise _err("omni_file_empty", ..., http_status=400)
   size > limit → _err("omni_file_too_large", 413)
   svg filename or image/svg+xml → _err("omni_svg_forbidden", 400)
   not allowed_omni_upload_mime(ct) → _err("omni_file_type_denied", 400)
   Не оставляй HTTPException(..., detail="строка") на этих четырёх ветках.
C. Unit:
   sniff("voice-x.webm", "application/octet-stream") == "audio/webm" и allowed_omni_upload_mime True
   sniff("x.svg", "image/svg+xml") deny (allowed False; upload path svg forbidden)
   allowed_omni_upload_mime("audio/webm") True
   не тащи pytest на живой upload роутер, если нет существующего клиента-фикстуры

STOP: webm+octet-stream allowed; SVG нет; upload не string-only detail. Не commit.
```

### Q9 STATUS — 2026-08-24 (STOP)

Q9 **закрыт по коду**. Канон:

| Артефакт | Изменение |
|----------|-----------|
| `omni_media_storage.py` | `sniff_omni_upload_mime` + `_normalize_mime`; suffix `.webm/.ogg/.mp3/.m4a/.wav` при пустом/`octet-stream` |
| `admin_omni_chat.py` upload | 4 ветки → `_err("omni_file_empty" \| "omni_file_too_large" \| "omni_svg_forbidden" \| "omni_file_type_denied")`; `ct = sniff(...)` перед allowlist; metadata `content_type` = sniffed |
| `tests/unit/test_omni_media_storage.py` | **16 passed** — webm+octet-stream, SVG deny, audio suffixes, explicit MIME, `is_omni_svg_upload` |

Проверено: нет string-only `detail` на upload 4xx (grep RU строк пуст); `AdminOmniChatPage.tsx` / `chat.json` не трогали. FE Q8 `omniUploadErrors.ts` теперь получает коды с BE. Не commit.

### Q9 AUDIT — 2026-08-24 (после STOP)

Проверено по диску (@LEAD + @ARCH + @QA_ARCH + @FRONTEND). Доработано в этом проходе:

| Вектор | Было | Сделано |
|--------|------|---------|
| SC1 SVG gate | логика только в роутере | `is_omni_svg_upload(filename, sniffed_ct)` в `omni_media_storage.py` + unit tests (`.svg`, `.svgz`, MIME) |
| DRY MIME | `allowed_omni_upload_mime` дублировал normalize | использует `_normalize_mime` |
| FE↔BE контракт | нет теста nested `detail.code` | `client-api-errors.test.ts` — `omni_file_empty` |
| Video webm | не покрыто | test: explicit `video/webm` сохраняется и allowed |
| Документация | GLOBAL AUDIT и ТЗ SC2/SC7 устарели («sniff ещё нет») | синхронизировано ниже |

**Вердикт @QA_ARCH:** 🟢 по карте Q9 A–C, STOP и SC1/SC2/SC7. Upload 4xx → structured codes; voice `webm`+`octet-stream` → `audio/webm`; SVG deny по filename **и** MIME.

**Формально vs реально:** end-to-end upload UX (конкретный i18n текст в UI) зависит от `sendWithFile` → `api` → `parseFastApiErrorBody` → `omniFileUploadErrorMessage` — контракт проверен unit-тестами на обоих концах; Playwright upload — Q13/e2e.

**Вне Q9 (NEXT):** `Q9-WEBM-VIDEO` (`.webm`+`octet-stream` всегда `audio/webm`; video webm с явным `video/webm` — ok), `Q9-UPLOAD-ROUTER-IT` (pytest на живой upload без фикстуры — отложено по промпту), staff/patient upload string `detail` — вне omni scope (`admin_patient_medical`, `admin_staff_profile`).

---

## PROMPT Q10 — @DEV VK hide + EN labels каналов

```
@DEV Волна A / P12 A4 SC4. Пиши код. Не commit.

НЕ: DROP vk_id; DELETE рядов; AdminTasksPage (VK placeholder уже Q6).
AdminOmniChatPage: ТОЛЬКО функция иконки/цвета канала (IconBrandVk ~L75/L84). Не пузыри Q8.
chat.json: ТОЛЬКО omniChannels.intro EN+RU (убрать слово VK). Не staff.*, не errors.*.

Прочитай:
1. AdminOmniChannelsPage.tsx CHANNEL_TYPE_OPTIONS / STATUS_OPTIONS (хардкод RU) L31–47
2. frontend/src/shared/chatI18n.ts omniChannelTypeLabel / omniChannelStatusLabel
3. en+ru/chat.json channelType.*, channelStatus.*, omniChannels.intro
4. PatientPhoneAuthPanel.tsx oauth vk
5. frontend/e2e/admin-omni-chat.spec.ts VK_BOT
6. i18nDefaultEn.test.ts omniChannelTypeLabel("VK_BOT") — может остаться

Сделать:
A. Create options: коды без VK_BOT. Labels = omniChannelTypeLabel(code) / omniChannelStatusLabel(status), не «Telegram бот». Собирай options в компоненте (не модульный const с RU), чтобы смена языка обновляла подписи (страница уже с хуками).
B. Credentials UI для VK_BOT: не в create. Если открыли старый канал type=VK_BOT — read-only или generic JSON, без credentials.vkGroupDesc как рекламы.
C. Скрыть Sign in with VK (PatientPhoneAuthPanel).
D. Inbox icon для VK_BOT → generic message icon (не бренд VK).
E. E2E: фильтр/create только Telegram/WhatsApp (или что уже есть кроме VK_BOT).

STOP: нельзя создать VK из UI; OAuth скрыт; типы каналов EN; нет миграций DROP. Не commit.
```

### Q10 STATUS — 2026-08-24 (STOP)

Q10 **закрыт по коду**. Канон:

| Пункт | Реализация |
|-------|------------|
| A Create без VK | `omniChannelCreateTypeOptions()` в `chatI18n.ts`; `AdminOmniChannelsPage` — labels через `omniChannelTypeLabel` / `omniChannelStatusLabel` + `useTranslation("chat")` |
| B Legacy VK credentials | `VK_BOT` → read-only generic JSON (`credentials.otherJson*`), save скрыт |
| C Patient OAuth | кнопка VK удалена из `PatientPhoneAuthPanel.tsx` |
| D Inbox icon | `AdminOmniChatPage` — `VK_BOT` → `IconMessage`, цвет gray |
| E E2E | `admin-omni-chat.spec.ts` — фильтр `TELEGRAM_BOT`, VK-only чат скрыт |
| chat.json | `omniChannels.intro` en+ru — слово VK убрано |

Проверено: `i18nDefaultEn` — create options без `VK_BOT`, intro без VK; `omniChannelTypeLabel("VK_BOT")` для legacy — ok. Пузыри Q8 / `staff.*` / `errors.*` не трогали. Не commit.

### Q10 AUDIT — 2026-08-24 (после STOP)

Проверено по диску (@LEAD + @ARCH + @QA_ARCH + @FRONTEND). Доработано в этом проходе:

| Вектор | Было | Сделано |
|--------|------|---------|
| SC4 create guard | только отсутствие VK в Select | `isOmniChannelCreatableType()` + hard stop в `handleCreate` |
| Credentials i18n | chrome i18n, формы ключей — хардкод RU description | все поля credentials → `credentials.*` (ключи уже были в chat.json; JSON не расширяли) |
| VK legacy UX | Alert title = `editTitle` (вводил в заблуждение) | нейтральный Alert без title |
| Тесты | только i18n gate | `shared/__tests__/chatI18n.test.ts` (create guard + legacy label) |
| Cyrillic grep | credentials блок ломал EN-демо | `AdminOmniChannelsPage.tsx` user-facing кавычки — пуст |

**Вердикт @QA_ARCH:** 🟢 по карте Q10 A–E, STOP и SC4. VK нельзя создать из UI; OAuth VK скрыт; типы/статусы/credentials chrome следуют `ui.locale`; inbox `VK_BOT` — generic icon.

**Формально vs реально:** BE всё ещё может принять `VK_BOT` через API — вне Q10 (нет UI path). Inbox channel filter показывает сырой код `TELEGRAM_BOT`, не `omniChannelTypeLabel` — UX debt, не регресс Q10.

**Вне Q10 (NEXT):** `Q10-OMNI-FILTER-LABELS` (MultiSelect inbox labels), `Q10-CHANNELS-E2E` (create без VK на `/admin/omni-channels`), `Q10-OAUTH-RESULT-VK` (`OAuthResultPage` текст «VK» для callback), `Q10-BE-VK-CREATE` (опциональный API deny create VK_BOT).

---

## PROMPT Q11 — @QA_ARCH

```
@QA_ARCH После Q1–Q10. Продуктовый код не писать. Отчёт: docs/artifacts/QA_REPORT_FRONTEND_COSMETIC_ORDER_2026-08-23.md

Прочитай ТЗ приёмка 1–10, SC1–SC7, владение файлами/JSON rev 3, аудит §9–§10.
Закон 8/11/26/38. Читай диск.

Обязательные доказательства (file:line):
- нет dual New task (toolbar кнопка удалена; тест getByRole один)
- sanitize или отсутствие trace_id= в TaskDetailsView
- PATIENT_MODAL_TABS_H=440, ScrollArea h=, нет Autosize mah; Tabs.List nowrap без grow
- нет package_id.slice
- calendar: нет formatTimeHHMMInput, нет datetime-local, нет type="time" как поля ввода; text+blur есть
- doctorRoleLabel не display_role; файл shared/doctorRoleI18n.ts без useTranslation
- leads-log без titleOverride; AdminTasksPage не обязан был меняться
- upload _err omni_file_* / omni_svg_forbidden; sniff_omni_upload_mime существует
- CHANNEL_TYPE create без VK_BOT
- phonePlaceholder "+7" в en и ru; нет ветки locale→+1
- JSON: schedule.json не писал Q1; chat.json errors — Q8; intro — Q10
- тесты обновлены (calendar test новый; tasks getByRole; MIME unit; handlers pytest)
- Q5: нет оставшихся RU в AdminSalesPipelinePage кавычках (не только ContextBar)

Вердикт 🟢/🟡/🔴 + возвраты @DEV по номеру Q. Не commit.
```

### Q11 STATUS — @QA_ARCH 2026-08-24

| Итог | Деталь |
|------|--------|
| **🟢** | Отчёт: [`QA_REPORT_FRONTEND_COSMETIC_ORDER_2026-08-23.md`](./QA_REPORT_FRONTEND_COSMETIC_ORDER_2026-08-23.md) |
| Тесты | FE **84** passed · BE **19** passed (handlers+MIME; API IT skipped без DB) |
| Deep audit | Q10 filter labels + BE VK guard + Loyalty package slice — см. GLOBAL AUDIT Q11 ниже |
| Возвраты @DEV | **Нет** |

**Следующий:** Q12 @QA_VISUAL.

---

## GLOBAL AUDIT Q11 — deep pass 2026-08-24

**Контекст:** @LEAD + @ARCH + @QA_ARCH + @FRONTEND после Q11. Повторная проверка формальных деклараций vs код, противоречий в доках, SC1–SC7, гонок/очередей.

### Исправления (код)

| Файл | Проблема | Fix |
|------|----------|-----|
| `AdminOmniChatPage.tsx:789` | Q10-OMNI-FILTER-LABELS: MultiSelect показывал сырой `TELEGRAM_BOT` | `label: omniChannelTypeLabel(ch)` |
| `owner_omni_channels.py` | Q10-BE-VK-CREATE: API принимал `VK_BOT` | 400 `omni_channel_type_not_creatable` |
| `test_owner_omni_channels.py` | Матрица create включала VK; не было негативного теста | VK убран из matrix; `test_owner_create_vk_bot_rejected` |
| `AdminLoyaltyPage.tsx:201` | SC3: fallback `subscription_package_id.slice(0,8)` | `packageNameById[…] ?? "—"` |

### Противоречия в документации (исправлено)

| Было | Стало |
|------|-------|
| NEXT: «Q11–Q13 осталось» при закрытом Q11 | Прогресс: Q12–Q13 |
| NEXT: Q10-OMNI-FILTER-LABELS / Q10-BE-VK-CREATE открыты | Помечены закрытыми с file:line |
| GLOBAL AUDIT: BATCH 4 ⏳ | Q11 ✅ |
| QA report: 80 FE tests | 84 (включая `taskStatusSemantic`, `adminChatChrome`) |

### Формально vs реально (дополнение)

| Заявлено | Факт после deep pass |
|----------|----------------------|
| SC4 «VK нельзя создать» | ✅ FE guard + **BE** `omni_channel_type_not_creatable` |
| Q8 inbox filter EN | ✅ labels через i18n, не коды |
| SC3 «нет package_id.slice» в волне A | ✅ Patient drawer + Loyalty package col; **остаток:** `s.id.slice` в Loyalty ID col → A2-LAW8-LOYALTY-SUB-ID |
| Q11 «upload end-to-end» | FE map + BE `_err` ✅; router IT без DB в CI skip → Q9-UPLOAD-ROUTER-IT остаётся |
| Calendar «нет type=time» | ✅ в `AdminStaffCalendarPage`; `AdminTasksPage` create due-time **намеренно** `type="time"` (вне D4) |

### Матрица рисков (актуализировано)

| Класс | ID | Статус |
|-------|-----|--------|
| 🟠 | Q13-STAFF-CHAT-TEST | открыт — нет `AdminStaffChatPage.test.tsx` (grep harness закрыт Q13) |
| 🟠 | A2-SEED | открыт |
| 🟠 | Q6-SEARCH-TRACE | открыт — поиск по legacy description |
| 🟡 | A2-LAW8-LOYALTY-SUB-ID | **новый** — id.slice в Loyalty |
| 🟡 | Q9-UPLOAD-ROUTER-IT | открыт |
| 🟡 | Q*-RTL / Q12 | **закрыт** Q12 @QA_VISUAL |
| 🟡 | CAL-MULTIDAY | открыт |

### Следующий шаг (после Q11 deep audit)

1. ~~@QA_VISUAL → Q12~~ ✅  
2. ~~@QA → Q13~~ ✅  
3. **A2-*** / human commit — см. NEXT

---

## PROMPT Q12 — @QA_VISUAL

```
@QA_VISUAL После 🟢 Q11 / после фикса возвратов. Отчёт: docs/artifacts/waves/cosmetic-a/VISUAL_QA_REPORT_COSMETIC_ORDER_2026-08-23.md

Канон: roles/QA_VISUAL_AESTHETE_SENSOR.md — таблица A–H без пустых клеток.
LAYOUT_INVARIANTS: модалка пациента main vs notes — высота ОКНА (GlassModal/dialog), не страницы. Два скрина + высота px. Delta ≈ 0. На 360 отдельно проверить, что ряд вкладок не wrap-ит вторую линию (nowrap+scroll). Если wrap — 🔴 D3.
ТЗ D1 D2 D3 rev 3.

Экраны: calendar timed create (набор 930→09:30 на blur); tasks board; schedule patient tabs; omni short messages.
1280 обязательно; 360 если модалка/вкладки.

Канбан: нет трёх цветных badges при нулях; карточка без тени/tint/status pill. Details могут быть tint — не 🔴.
Omni: пузырь у края колонки, не центр 420px, нет шкафа из 28+56.

Не лендинг. Не commit.
```

### Q12 STATUS — @QA_VISUAL 2026-08-24

| Итог | Деталь |
|------|--------|
| **🟢** | Отчёт: [`waves/cosmetic-a/VISUAL_QA_REPORT_COSMETIC_ORDER_2026-08-23.md`](./waves/cosmetic-a/VISUAL_QA_REPORT_COSMETIC_ORDER_2026-08-23.md) |
| Harness | `PatientEntityDrawer.geometry.test.tsx` — 3 passed |
| Возвраты @DEV | **Нет** |

**Следующий:** волна A закрыта → A2-* / deploy human.

---

## PROMPT Q13 — @QA тесты

```
@QA Не весь admin C1. Только волна A.

Прочитай ТЗ приёмка. Запусти то, что есть, допиши дыры:

frontend (из frontend/):
  npx vitest run src/admin/pages/__tests__/AdminTasksPage.test.tsx src/admin/pages/__tests__/AdminStaffCalendarPage.test.tsx src/i18n

backend:
  pytest tests/application/test_tasks_event_handlers.py tests/unit/test_omni_media_storage.py tests/services/test_booking_completion_service.py -q
  (пути скорректируй, если Q7/Q9 назвали иначе — в отчёте фактическая команда)

Проверки:
- AdminTasksPage: ровно 1 New task
- calendar en: нет «Участники»; all-day без time/datetime-local
- MIME unit: webm+octet-stream allowed; svg denied
- handlers: "trace_id=" not in description
- i18nDefaultEn: не регрессировать dayjs locale; omniChannelTypeLabel("VK_BOT") может жить

Grep-гейт (в отчёте, код теста желателен) по файлам волны A — нет кириллицы в user-facing кавычках:
  AdminStaffCalendarPage.tsx PatientEntityDrawer.tsx BookingEntityDrawer.tsx
  AdminLeadsLogPage.tsx AdminStaffChatPage.tsx AdminSalesPipelinePage.tsx
  AdminTasksPage.tsx (chrome, не data) AdminOmniChannelsPage.tsx
Полный CI grep по всему admin/ — NEXT.

Windows e2e: documentation или QA_ARCH_PYTEST_FULL_SUITE.md, если запускаешь Playwright.

STOP: команды + exit code. Не commit.
```

### Q13 STATUS — @QA 2026-08-24

| Итог | Деталь |
|------|--------|
| **🟢** | Отчёт: [`QA_TEST_REPORT_FRONTEND_COSMETIC_ORDER_2026-08-23.md`](./QA_TEST_REPORT_FRONTEND_COSMETIC_ORDER_2026-08-23.md) |
| FE | **`npm run test:wave-a`** → **100 passed** (15 files) · exit 0 |
| BE | **19 passed**, 9 skipped · exit 0 |
| Harness | `waveACyrillicGate.test.ts` (9 files, quoted + bare JSX) + `test:wave-a` script |
| BATCH 4 | **Q11–Q13 ✅ — волна A закрыта** |

---

## GLOBAL AUDIT Q13 — deep pass 2026-08-24

**Контекст:** @LEAD + @ARCH + @QA_ARCH + @FRONTEND после Q13. Проверка формальных деклараций vs код, полноты grep-gate, противоречий в доках.

### Исправления (код / harness)

| Файл | Проблема | Fix |
|------|----------|-----|
| `waveACyrillicGate.test.ts` | Не покрывал `AdminOmniChatPage.tsx` (Q8, был в GLOBAL AUDIT grep) | добавлен 9-й файл |
| `waveACyrillicGate.test.ts` | Только quoted strings; `>текст<` без кавычек не ловился | + `findBareJsxCyrillicText` |
| `package.json` | Нет воспроизводимой команды wave A | **`npm run test:wave-a`** |

### Противоречия в документации (исправлено)

| Было | Стало |
|------|------|
| GLOBAL AUDIT Q11: «Q13-GAP открыт» без уточнения | grep harness **закрыт**; Staff chat page test — NEXT |
| NEXT: «нет PatientEntityDrawer geometry test» | Q12 добавил `PatientEntityDrawer.geometry.test.tsx` |
| `DEVELOPMENT_PLAN`: «ждёт ручной команды» | волна A **закрыта** 2026-08-24 |
| QA_TEST: не включал `client-api-errors.test.ts` | в канон `test:wave-a` |

### Канонический прогон (exit 0)

```bash
# frontend/
npm run test:wave-a

# backend (корень)
python -m pytest tests/application/test_tasks_event_handlers.py \
  tests/unit/test_omni_media_storage.py \
  tests/services/test_booking_completion_service.py -q
```

### Матрица рисков post-Q13

| Класс | ID | Статус |
|-------|-----|--------|
| 🟠 | Q13-STAFF-CHAT-TEST | открыт — нет `AdminStaffChatPage.test.tsx` |
| 🟠 | A2-SEED | открыт |
| 🟠 | Q6-SEARCH-TRACE | открыт |
| 🟡 | A2-GREP | wave A grep в vitest; **полный admin/** — CI eslint (NEXT) |
| 🟡 | Q9-UPLOAD-ROUTER-IT | API IT skip без DB |
| 🟡 | Q13-PLAYWRIGHT-PIXEL | Playwright @1280 |

**Возвраты @DEV:** нет. **Волна A закрыта.** Следующее: A2-* + human commit (Law 40).

---

## GLOBAL AUDIT — волна A Q1–Q8 — 2026-08-24

**Контекст:** глобальный проход @LEAD + @ARCH + @QA_ARCH + @FRONTEND + @QA после закрытия Q1–Q8 (до старта Q9). Цель: функциональная полнота, STOP-гейты, Law 8/11/15, геометрия в scope, формальные декларации vs код, гонки/пробелы, синхронизация с NEXT.

### Прогресс батчей

| Батч | Промпты | Статус |
|------|---------|--------|
| BATCH 1 | Q1, Q2, Q4, Q5, Q6, Q7 | ✅ STOP + проверено |
| BATCH 1b | Q3 | ✅ STOP + AUDIT |
| BATCH 2 | Q8, Q9 | ✅ STOP |
| BATCH 3 | Q10 | ✅ STOP |
| BATCH 4 | Q11 → Q12 → Q13 | **✅ закрыт** |

### Вердикты по промптам

| Q | Вердикт | Evidence (диск) | Замечания |
|---|---------|-----------------|-----------|
| Q1 Calendar | 🟢 | `AdminStaffCalendarPage.test.tsx`; grep: нет `formatTimeHHMMInput` / `datetime-local` / `type="time"`; кириллица в кавычках JSX — только комменты | **Global fix:** `participantOptions` → `displayPersonName` (Law 8, не `id.slice(0,8)`). Отдельного Q1 AUDIT-блока нет — покрыто здесь. CAL-MULTIDAY → NEXT |
| Q2 Patient drawer | 🟢 | STATUS+audit в блоке Q2; `passOptionLabel` без slice package id; `PATIENT_MODAL_TABS_H=440` | Q2-PKG-NAME (нет имени пакета в DTO) — осознанный NEXT |
| Q3 Booking drawer | 🟢 | Q3 AUDIT; `doctorRoleI18n.test.ts` 4/4 | Q3-CONSUMABLE-NAME, display_role вне scope |
| Q4 Staff chat i18n | 🟢 | grep кириллицы пуст; `displayPersonName` в списке коллег | **Дыра Q13:** нет `AdminStaffChatPage.test.tsx`. Пузыри — Q4-BUBBLE (не редизайн) |
| Q5 Sales CRM | 🟢 | `AdminSalesPipelinePage.test.tsx` 6/6; EmptyState, QueryErrorAlert, `formatCrmAmount` | Q5-KANBAN-COL-ERR per-column — NEXT |
| Q6 Tasks FE | 🟢 | `AdminTasksPage.test.tsx` 12/12; shared sanitize/semantic tests | **Global fix:** `adminOptions` → `displayPersonName`. Q6-SEARCH-TRACE — BE/поиск |
| Q7 Tasks BE | 🟢 | `test_tasks_event_handlers.py` 3 + `test_booking_completion_service.py` 9 = **12 passed**; grep: нет `description += trace_id` | Старые ряды в БД — A2-SEED; RU body loyalty/paperless — NEXT |
| Q8 Omni bubbles FE | 🟢 | `omniUploadErrors.test.ts`, `adminChatChrome.test.ts`; D2 геометрия verified | **Блокер интеграции:** до Q9 upload 4xx → `sendFileFailed` (FE готов) |

### Механические STOP-гейты (2026-08-24)

```
grep user-facing кириллица в кавычках (wave A owned tsx): PASS
  AdminStaffCalendarPage PatientEntityDrawer BookingEntityDrawer
  AdminLeadsLogPage AdminStaffChatPage AdminSalesPipelinePage
  AdminTasksPage AdminOmniChatPage — только комменты в calendar

Q1 forbidden widgets: PASS (calendar)
Q7 trace_id in description concat: PASS (application/)
Q8 omni spacer 28 / meta 56 / nested p={6}: PASS
```

### Тесты (фактические команды, exit 0)

> **Снимок до Q12/Q13.** Канон после закрытия волны A: `npm run test:wave-a` → **100 passed** (15 files). См. § Q13 STATUS и GLOBAL AUDIT Q13.

**Frontend (из `frontend/`) — исторический прогон Q1–Q8:**
```
npx vitest run \
  src/admin/pages/__tests__/AdminTasksPage.test.tsx \
  src/admin/pages/__tests__/AdminStaffCalendarPage.test.tsx \
  src/admin/pages/__tests__/AdminSalesPipelinePage.test.tsx \
  src/shared/__tests__/doctorRoleI18n.test.ts \
  src/shared/__tests__/taskDescriptionSanitize.test.ts \
  src/shared/__tests__/taskStatusSemantic.test.ts \
  src/shared/__tests__/omniUploadErrors.test.ts \
  src/shared/__tests__/adminChatChrome.test.ts \
  src/i18n
→ 11 files, 82 tests passed
```

**Backend:**
```
pytest tests/application/test_tasks_event_handlers.py \
       tests/services/test_booking_completion_service.py -q
→ 12 passed
```

**Не запускалось в GLOBAL AUDIT Q1–Q8:** Playwright visual, полный admin Cyrillic CI grep. **После Q9:** `test_omni_media_storage.py` — **16 passed** (audit 2026-08-24).

### Исправления в global audit (код)

| Файл | Проблема | Fix |
|------|----------|-----|
| `AdminStaffCalendarPage.tsx` | Law 8: fallback `a.id.slice(0,8)` в MultiSelect участников | `displayPersonName(full_name\|email, id)` |
| `AdminTasksPage.tsx` | Law 8: то же в `adminOptions` (assignee Select) | `displayPersonName` |

### Матрица рисков (консолидировано)

| Класс | ID | Риск | Митигация |
|-------|-----|------|-----------|
| 🟠 средний | Q13-STAFF-CHAT-TEST | Нет vitest Staff chat page | A2 / optional vitest |
| 🟠 средний | A2-SEED | Showcase tasks в БД могут остаться RU + trace в body | A2-SEED |
| 🟠 средний | Q6-SEARCH-TRACE | Поиск задач по сырому `description` с legacy trace | совместно с миграцией данных |
| 🟡 мелкий | A2-GREP | wave A grep в `test:wave-a`; полный `admin/**` — CI | A2-GREP |
| 🟡 мелкий | Q9-WEBM-VIDEO | `.webm`+`octet-stream` → `audio/webm` (voice bias); video с явным `video/webm` ok | документировано; ADR при жалобе |
| 🟡 мелкий | Q9-UPLOAD-ROUTER-IT | Нет pytest на живой upload роутер | IT при DB |
| 🟡 мелкий | Q*-RTL | Закрыт Q12 harness; полный Playwright pixel — NEXT | Q13-PLAYWRIGHT-PIXEL |
| 🟡 мелкий | CAL-MULTIDAY | Edit события через полночь сжимает end-date | CAL-MULTIDAY ADR |
| 🟡 мелкий | Q2-PKG-NAME / Q3-CONSUMABLE | DTO без display names | additive API |
| 🟡 формальный | Q4-BUBBLE / Q6-STREAM-ACCENT | Визуальный долг, не регресс функции | отдельные промпты |

### Формально vs реально

| Заявлено | Факт |
|----------|------|
| Q8+Q9 upload errors по коду `omni_file_*` | ✅ BE `_err` + FE `omniUploadErrors.ts`; nested `detail.code` тест в `client-api-errors.test.ts` |
| Wave A «EN demo без UUID в UI» | Исправлено в calendar/tasks assignee; остаток admin (Finance, Loyalty, Rights…) — **A2-C1**, вне Q1–Q8 |
| Q7 «system tasks EN» | **Новые** события EN; **старые ряды** — A2-SEED |
| Q2 «package label» | `packageRemain` без имени пакета — DTO gap (Q2-PKG-NAME) |

### Следующий шаг очереди (волна A закрыта 2026-08-24)

1. **Human commit** (Law 40) — `npm run test:wave-a` + backend pytest зелёные.  
2. **A2-*** — [`FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md`](./FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md).

**Law 40:** push — только human.

**Связанный артефакт:** долги и промпты вне A — [`FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md`](./FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md) (обновлён прогрессом волны).
