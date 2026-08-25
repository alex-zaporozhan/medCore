# Следующие шаги вне волны A (исполняемые, не «потом»)

> **Дата:** 2026-08-23 (прогресс 2026-08-24) · **Зачем:** всё вне scope Q1–Q8 либо в NEXT с owner, либо делается в Q9–Q13.  
> **Прогресс волны A (2026-08-24):** Q1–Q13 **закрыты** (BATCH 4 ✅). Deep audit Q13: grep 9 файлов + `test:wave-a`. Следующие шаги — A2-* в этом файле.  
> **Этот файл:** промпты **вне** текущих Qn и **после** Q13 (A2-*). Не дублировать работу Q9–Q13 здесь.  
> **После rev 3:** волна A **не** обещает RU→EN уже лежащих system-task titles (A2-SEED) и **не** использует `input type="time"` как фикс календаря.

Связь: [`FRONTEND_COSMETIC_ORDER_TZ_2026-08-23.md`](./FRONTEND_COSMETIC_ORDER_TZ_2026-08-23.md) · очередь A: [`QUEUE_FRONTEND_COSMETIC_ORDER_2026-08-23.md`](./QUEUE_FRONTEND_COSMETIC_ORDER_2026-08-23.md)

---

## Карта долгов

| ID | Что | Почему не в A | Owner | Если не сделать |
|----|-----|---------------|-------|-----------------|
| A2-LAW8-LOYALTY-SUB-ID | `AdminLoyaltyPage.tsx` колонка ID: `s.id.slice(0,8)` | вне Q2; package column slice убран 2026-08-24 | @DEV A2-C1-MONEY | Law 8: hex id в таблице абонементов |
| A2-C1 | Остальные admin pages с кириллицей в JSX | Law 1, объём | @DEV батчами ниже | EN-демо дырявое за P0-URL |
| A2-SEED | Системные задачи уже в БД на RU; showcase `+700910` на Austin | A чинит только новые ряды + UUID sanitize | @DEV + human re-seed | Скрин no-show останется RU |
| A2-AI | `ai_task_manager_service.py` RU titles | отдельный сервис, не P0 URL | @DEV | AI-предложенные задачи на RU |
| A2-GREP | CI grep кириллицы в admin chrome | LPA L5; не блокировать A | @ARCH/@DEV | класс C1 вернётся |
| A2-DOCROLE | DoctorEntityDrawer / Doctors page RU | не в списке URL | @DEV | «Врачи» на EN |
| CAL-MULTIDAY | Timed-событие через полночь: UI клеит **дату старта** + время конца; дата конца из исходного `ends_at` теряется | Q1 сознательно однодневный виджет D4 | @ARCH/@DEV после A | edit многодневного события сожмёт его в один день |
| CAL-OVERLAP-UX | Submit overlap = hard stop (ключ `errors.overlap`); D4: inputs не disabled. Согласовано с `_assert_calendar_event_no_overlap` | не баг | — | менять только по ADR |
| Q10-OMNI-FILTER-LABELS | ~~Inbox MultiSelect: label = сырой `TELEGRAM_BOT`~~ | **Закрыто 2026-08-24:** `AdminOmniChatPage.tsx:789` → `omniChannelTypeLabel(ch)` | — | — |
| Q10-CHANNELS-E2E | Нет Playwright на `/admin/omni-channels` create без VK | Q10 E2E = omni-chat filter | @QA Q13/e2e | регресс create VK только unit/i18n |
| Q10-OAUTH-RESULT-VK | `OAuthResultPage` показывает «VK» при `?oauth=vk` callback | Q10 C = скрыть CTA, не callback page | @DEV A2-C1 | редкий deep-link после скрытия кнопки |
| Q10-BE-VK-CREATE | ~~API owner channels мог принять `type=VK_BOT` без UI~~ | **Закрыто 2026-08-24:** `owner_omni_channels.py` → `omni_channel_type_not_creatable` + `test_owner_create_vk_bot_rejected` | — | — |
| Q12–Q13 | ~~Остаток волны A~~ | **Закрыто 2026-08-24** — Q12 visual + Q13 test report | — | — |
| Q13-STAFF-CHAT-TEST | Нет `AdminStaffChatPage.test.tsx` | Q4 закрыт grep-гейтом; page test — A2 | @DEV опционально | регресс i18n staff chat |
| Q13-PATIENT-GEOMETRY | ~~Нет vitest geometry PatientEntityDrawer~~ | **Закрыто Q12** — `PatientEntityDrawer.geometry.test.tsx` (3 tests) | — | — |
| Q13-BOOKING-DRAWER-TEST | Нет vitest на `BookingEntityDrawer` | Q13 минимум — grep; booking drawer geometry — A2 | @DEV после A | Law 8 tabs booking |
| Q2-MENU-STUB | Menu print/copy/delete в PatientEntityDrawer — только i18n, без onClick | Q2 требовал подписи, не API удаления/печати | @DEV после A или вместе с карточной печатью | кнопки выглядят рабочими и ничего не делают |
| Q2-NPS | Колонка NPS в таблице визитов всегда «—» | нет поля в Booking DTO | @ARCH + @DEV когда API отдаст score | пустая колонка в EN-демо |
| Q2-PKG-NAME | Карточка абонемента: `t(package)` без имени пакета | `CustomerSubscription` без display name | @ARCH additive DTO + @DEV | все абонементы выглядят одинаково |
| Q2-RTL | ~~PatientEntityDrawer @360 tab-row не измерен~~ | **Закрыто Q12** — `PatientEntityDrawer.geometry.test.tsx`; полный RTL pixel — Q13-PLAYWRIGHT-PIXEL |
| Q3-CONSUMABLE-NAME | Вкладка расходников booking drawer: UUID `product_id` → «—»; в `ServiceConsumable` нет display name | Q3 не расширяет inventory DTO | @ARCH additive name/join + @DEV | таблица материалов без человекочитаемых имён |
| Q3-RTL | BookingEntityDrawer @360/RTL | harness нет; Q12 scope = patient | Q13-PLAYWRIGHT-PIXEL / A2 | геометрия вкладок на узком/RTL не измерена |
| Q3-DISPLAY-ROLE-OTHER | `display_role` ещё в DoctorEntityDrawer / Doctors / AdminBookingsPage / public wizard | вне владения Q3; `directory.json` не трогали | @DEV в A2-DOCROLE / A2-C1-BOOK / PWA | EN-демо вне schedule create и booking drawer может показать сырой/RU `display_role` |
| Q4-RTL | AdminStaffChatPage @360/RTL | harness нет; Q12 scope = patient + omni tokens | Q13-PLAYWRIGHT-PIXEL | wrap колонок на 360 не измерен в браузере |
| Q4-BUBBLE | Плотность пузырей staff chat не сверяли с omni эталоном | Q4 явно: не редизайн пузырей / не трогать adminChatChrome | @DESIGN/@DEV отдельным промптом | визуальный долг, не регресс i18n |
| Q5-KANBAN-COL-ERR | Ошибка `useCrmKanbanStageLeadsInfinite` на колонке — ключ `pipeline.loadColumnsFailed` на диске, UI per-column нет | Q5 = i18n chrome, не error-surface канбана | @DEV после A или с CRM hardening | колонка молча пустая при 5xx |
| Q5-RTL | AdminSalesPipelinePage @360/RTL | harness нет | Q13-PLAYWRIGHT-PIXEL | горизонтальный скролл/колонки на 360 не измерены |
| Q6-RTL | AdminTasksPage @360/RTL | harness нет | Q13-PLAYWRIGHT-PIXEL | геометрия колонок/очереди на 360 не измерена |
| Q6-TASK-DETAILS-TEST | `TaskDetailsView` sanitize/copy — unit tests только на shared helper, не на компонент | Q6 scope = page test + owned files минимум | @DEV после A | регресс copy UI без component test |
| Q6-STREAM-ACCENT | `StreamPageShell` после F не использует `accentColor` (dead prop) | сознательно: hairline вместо gradient | @DESIGN/@DEV при stream RESKIN | accent stream не визуализируется в shell |
| Q6-SEARCH-TRACE | Поиск задач матчит сырой `description` с `trace_id=` | не UI modal; вне H | @DEV с Q7 BE sanitize | оператор ищет по машинному хвосту |
| Q7-PAPERLESS-RU-BODY | `PAPERLESS_REQUIRED_FORMS_MISSING` при `patient_id is None` — description на RU | Q7 scope = убрать concat + ERP EN; ветка без пациента вне A1 | @DEV в A2-C1 или forms i18n | EN-демо при завершении без patient_id |
| Q7-LOYALTY-RU-BODY | `LOYALTY_ERP_INCONSISTENT_OBLIGATION` description остаётся RU | A1: title-коды не русифицировать, только убрать concat | @DEV с multi-lang system tasks ADR | несогласованность ERP/Loyalty — RU body |
| Q9-WEBM-VIDEO | `.webm`+`octet-stream` sniff → `audio/webm` (voice bias); явный `video/webm` не трогаем | осознанный контракт Q9/TZ SC2 | — | редкий video upload как octet-stream классифицируется как voice |
| Q9-UPLOAD-ROUTER-IT | Нет pytest на живой `send_admin_omni_message_upload` | Q9 scope = unit sniff/allowlist | IT при DB | FE `client-api-errors.test.ts` + unit MIME |
| Q8-RTL | AdminOmniChatPage thread @360/RTL | D2 code contract; pixel harness нет | Q13-PLAYWRIGHT-PIXEL | геометрия пузырей на узком/RTL не измерена pixel-to-pixel |
| B-CONCEPT | VISUAL_CONCEPT + MOTION + landing RESKIN | Law 28 нет концепта | @CREATOR/@MOTION/@DESIGN | лендинг остаётся тихим SaaS |
| B-LOCALE | `clinic.locale` → шаблоны system tasks | нужен ADR | @ARCH | RU-клиника видит EN system copy после A |
| B-CCY | Символ денег от региона клиники, не ₽ hardcoded | roadmap L3 уже решил «не от UI» | @ARCH | Austin демо с ₽ |
| PWA | `/app` `/c/:slug` patient i18n | вне списка | отдельная волна | — |

---

## PROMPT A2-SEED — системные задачи и телефоны демо

```
@DEV После волны A. Код + скрипт. Не commit.

Цель: существующие system tasks (no-show/cancel) в showcase DB — EN title/description без trace_id= в body. Не массовый UPDATE прод-данных без фильтра showcase clinic.

Прочитай: src/scripts/showcase_en_demo_window.py, seed_presentation_showcase.py (phone_prefix +700910), tasks_event_handlers.py (уже EN после Q7).

Сделать:
1. Идемпотентный remap: clinic showcase (Brightside Austin) — UPDATE tasks SET title/description по source in (system) где description ILIKE '%no-show%' или известные RU шаблоны → EN шаблоны Q7. Обрезать хвост trace_id=/event_id=.
2. Не трогать пользовательские задачи (source != system).
3. Телефоны +700910 на Austin — DECLARE с владельцем: либо оставить как demo-pool, либо prefix +1512 в следующем seed. Не делать вслепую, если ломает e2e по +7.

STOP: SELECT по showcase clinic не возвращает «Обработать no-show». Отчёт SQL. Не commit.
```

---

## PROMPT A2-AI — AI proposed tasks EN

```
@DEV После A. Файл: src/application/services/ai_task_manager_service.py (~272, 291, 309 RU titles).

Сделать: EN titles/descriptions тех же смыслов (no-show cluster, ERP errors, stale CRM leads). Тесты, которые ждут кириллицу — обновить.

Не менять логику scoring. Не commit.
```

---

## PROMPT A2-C1-DIR — directory chrome (Doctors, Services, Clinics, Waitlist, drawers)

```
@DEV C1 wire. Не новые ns. Не commit.

Файлы (читай каждый с диска, grep [А-Яа-яЁё] в кавычках JSX):
- AdminDoctorsPage.tsx, DoctorEntityDrawer.tsx
- AdminServicesPage.tsx, ServiceEntityDrawer.tsx
- AdminClinicsPage.tsx
- AdminWaitlistPage.tsx
Ключи: frontend/src/i18n/locales/en/directory.json (doctors.*, doctorDrawer.*, services.*, clinics если есть)

Паттерн: useTranslation("directory"); литерал → существующий ключ; нет ключа → en+ru пара.
display_role: использовать doctorRoleLabel из волны A (shared/doctorRoleI18n.ts), не сырой API.

STOP: grep кавычек кириллицы в этих файлах пуст. Не commit.
```

---

## PROMPT A2-C1-BOOK — bookings / waitlist-adjacent / doctor schedule

```
@DEV C1. ns schedule + bookings.

Файлы: AdminBookingsPage.tsx, AdminDoctorSchedulePage.tsx, ScheduleCalendar.tsx / ScheduleCalendarGrid.tsx если литералы chrome (не имена пациентов).

Ключи: en/schedule.json, en/bookings.json.
Не переводить статусы минуя bookingStatusLabel.

STOP: нет «Врач» как label при en. Не commit.
```

---

## PROMPT A2-C1-MONEY — commerce, loyalty, discounts, prepayment, finance leftovers

```
@DEV C1. ns money. ₽ не заменять на $.

Файлы: AdminCommercePage.tsx, AdminLoyaltyPage.tsx, AdminDiscountsPage.tsx, AdminPrepaymentPage.tsx, плюс хвосты AdminFinancePage если ещё литералы (символ ₽ оставить).

Ключи: en/money.json. Нет ключа — пара en+ru.

STOP: chrome EN, ₽ на месте. Не commit.
```

---

## PROMPT A2-C1-OPS — administrators, rights, forms, marketing, recall, retention, emergency, knowledge, rag, embed, channels, ai settings, styling, agreements, data export, payment gateway

```
@DEV Дроби на подбатчи по 3–4 файла, если дифф > разумного. Один подбатч = один промпт-клон этого с явным списком файлов.

Ключи: settings.json, rbac.json, feed/marketing как в существующих ns. rbacRightsPoliciesPageCopy.ts — перевести через rbac.json (уже есть presetLabelDoctor).

AdminOmniChannelsPage после Q10 уже на omniChannelTypeLabel — не откатывать VK hide.

STOP подбатча: grep кириллицы в заявленных файлах. Не commit.
```

Рекомендуемый порядок подбатчей (копировать, подставляя файлы):

1. `AdminAdministratorsPage.tsx`, `AdminRightsPoliciesPage.tsx`, `rbacRightsPoliciesPageCopy.ts`  
2. `AdminFormsPage.tsx`, `AdminMarketingPage.tsx`, `AdminRecallPage.tsx`  
3. `AdminRetentionPage.tsx`, `AdminEmergencyNotificationsPage.tsx`, `AdminKnowledgePage.tsx`  
4. `AdminRagKbPage.tsx`, `AdminEmbedPage.tsx`, `AdminChannelsPage.tsx`  
5. `AdminAiSettingsPage.tsx`, `AdminOmniAiSettingsPage.tsx`, `AdminStylingPage.tsx`  
6. `AdminAgreementsPage.tsx`, `AdminDataExportPage.tsx`, `AdminPaymentGatewayPage.tsx`, `AdminStaffCabinetPage.tsx`

---

## PROMPT A2-GREP — предохранитель класса C1

```
@ARCH затем @DEV. Не волна A.

Добавить frontend unit или eslint-правило: в frontend/src/admin/**/*.{ts,tsx} запрещены кириллические литералы в JSX text / prop strings, allowlist: *.test.*, комментарии, файлы из NEXT-исключений (нет).

**Уже есть:** `waveACyrillicGate.test.ts` (9 файлов волны A) + `npm run test:wave-a`. A2-GREP = расширение на весь `admin/**` + CI job.

Не трогать patient PWA. Не commit без зелёного vitest.
```

---

## PROMPT B-CONCEPT — лендинг statement (Law 28)

```
@CREATOR затем @MOTION CONCEPT затем @DESIGN SPEC. Код не писать в этом промпте.

Прочитай: roles/VISUAL_CONCEPT_PROTOCOL.md, roles/CONCEPT_DNA_LIBRARY.md, roles/EDITORIAL_CRAFT_CANON.md Y1–Y12, roles/HERO_ARCHETYPES.md, текущий MarketingLandingPage.tsx.

Сделать артефакты:
- docs/artifacts/VISUAL_CONCEPT_DENTAL.md (мир, TASTE GATE C1–C10)
- docs/artifacts/MOTION_SPEC_LANDING_DENTAL.md
- docs/artifacts/DESIGN_SPEC_LANDING_RESKIN.md (Swap Map: скелет секций остаётся или перечисляется явно)

Не «добавить ещё карточек». Один жест. Референс editorial, не Linear.
STOP: концепт утверждён владельцем. @DEV RESKIN — отдельный промпт после.
```

---

## PROMPT B-LOCALE — clinic.locale для system copy

```
@ARCH только ADR + spine. Не код, пока нет номера ADR.

Вопрос: system task templates и display_role — от ui.locale оператора или от clinic.locale?
Конфликт с EN-default продукта и RU-клиникой.

Выход: ADR. Пока нет ADR — после волны A шаблоны EN (уже принято).
Не DROP. Не commit.
```

---

## PROMPT B-CCY — символ валюты

```
@ARCH. Сейчас ₽ в FE (finance, crm.json columnMeta, dashboard). Roadmap L3: регион клиники.

Нужно поле clinic.currency / money_display на API, затем один хелпер formatMoney. Не ветвить от ui.locale.

STOP: ADR или явное «остаётся ₽ до multi-currency». Не скрытый $.
```

---

## Что сознательно закрыто «не делаем», чтобы не висело серым

| Не делать | Причина |
|-----------|---------|
| Канбан → таблица | D1: доска уместна |
| DROP patients.vk_id | данные OAuth |
| Перевод тел чата / ФИО | C2 data |
| Правка `roles/` канонов | Law 16, нет запроса |
| Git commit агентом | Law 40 |
