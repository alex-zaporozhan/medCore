# Анамнез и диагноз: эстетика + EN-chrome админки

> **Дата:** 2026-08-23 · **Режим:** только диагностика (код не менялся)  
> **Роли:** @LEAD · @ARCH · @QA_ARCH · @QA · @FRONTEND · @MOTION · @DESIGN · @QA_VISUAL  
> **Каноны:** `roles/VISUAL_CRAFT_CANON.md` (instrument) · `roles/EDITORIAL_CRAFT_CANON.md` (statement) · `roles/INTERFACE_CRAFT_CANON.md` · `roles/LAYOUT_INVARIANTS.md` · `roles/QA_VISUAL_AESTHETE_SENSOR.md` · `docs/artifacts/ADMIN_I18N_EN_ROADMAP.md`  
> **Лечение (ТЗ):** [`FRONTEND_COSMETIC_ORDER_TZ_2026-08-23.md`](./FRONTEND_COSMETIC_ORDER_TZ_2026-08-23.md)  
> **Очередь промптов:** [`QUEUE_FRONTEND_COSMETIC_ORDER_2026-08-23.md`](./QUEUE_FRONTEND_COSMETIC_ORDER_2026-08-23.md)  
> **Приоритет истины:** код на диске + скриншоты владельца. Roadmap A0–A12 объявлял chrome «закрытым» — **диск это опровергает** (Law 12).

---

## 0. Вердикт одной фразой

Админка уже имеет **полные EN-словари**. Симптом «EN выбран, а на экране RU» почти везде — **страница не вызывает `t()`**, а не «нет перевода». Параллельно: Law 8 (UUID в теле задачи), прыгающая медкарта, сломанный ввод времени, «пестрящий» канбан, раздутые пузыри omni-чата, падение voice-upload, и VK как канал (юридический риск для международной аудитории).

**₽ — не баг языка.** Регион клиники (roadmap L3). Не переводить в `$` из-за `ui.locale=en`.

**+7 — тоже регион, не locale.** Переключатель EN/RU **не** меняет маску телефона. (В черновике ТЗ A5 это было нарушено — отозвано в ревью §9.) Placeholder «Ivan Ivanov» в `en/schedule.json` — ошибка **копии EN-словаря**, не архитектуры региона.

---

## 0.1 LPA (Law 24)

⊕ **L5 Automation:** класс дефекта один — «JSON есть, JSX литерал». Гейт grep кириллицы в `admin/**/*.tsx` (кроме тестов/комментариев) снимает этот класс с будущих волн.

⊕ **L1 Technology:** не писать новые словари и не редизайнить канбан с нуля. Wire существующих ключей + **text time + blur-normalize** (не `type="time"`: на Chrome/Windows это сегментированный picker и не чинит «нельзя набрать цифры») + тишина chrome по VISUAL_CRAFT §1.

Линзы L2/L3/L4/L6 молчат как отдельные выстрелы (Kanban оставляем; VK прячем, схему не ломаем).

---

## 0.2 Метод и перепроверка

| Источник | Что дало |
|----------|----------|
| Скриншоты владельца (landing → finance) | Симптомы: RU leftover, Trace ID, dual New task, прыжки модалки, gaps в чате, voice fail |
| Параллельный разбор кода (календарь / tasks / patient+omni+sales / landing+staff) | Корневые причины с file:line |
| Точечная перепроверка @LEAD по диску | Подтверждено: `formatTimeHHMMInput`, `titleOverride="Лиды (лог)"`, вкладки медкарты, `display_role` бэка = «Врач», MIME allowlist, dual CTA |

**Класс дефекта (не путать):**

| Класс | Что это | Лечится |
|-------|---------|---------|
| **C1 chrome i18n** | Литерал в JSX при готовом ключе | `useTranslation` + `t()` |
| **C2 seed/API copy** | Текст сущности (title задачи, `display_role`) | Шаблоны/маппинг enum, не «перевод UI» |
| **C3 craft/geometry** | Пестрота, gaps, прыжок высоты | Токены, фиксированный viewport |
| **C4 functional** | Ввод времени, upload audio | Контрол / MIME / ошибка |
| **C5 product/legal** | VK как интеграция | Скрыть создание; колонки не дропать |
| **N/A region** | ₽, маска телефона | Не привязывать к `ui.locale` |

---

## 1. Сводная матрица запрошенных URL

| # | URL | Регистр | Главный диагноз | Класс | Тяжесть |
|---|-----|---------|-----------------|-------|---------|
| 1 | `:3010/` | **statement** | EN chrome **полный**. Craft — тихий SaaS (Y-робость). Нет `VISUAL_CONCEPT_*` | C3 + долг Law 28 | 🟡 отдельная волна |
| 2 | `:3010/signup` | statement/form | EN chrome **полный**. Phone/Ivan **не здесь** | — | 🟢 |
| 3 | `:5175/admin` | instrument | Feed на ключах `feed`. ₽ by-design | N/A region | 🟢 косметика |
| 4 | `:5175/admin/staff-chat` | instrument | **Нет `useTranslation`**. «Участники» и десятки литералов | C1 | 🔴 |
| 5 | `:5176/admin/calendar` | instrument | **Нет `useTranslation`**, ключи `staffCal.*` готовы. Маска времени ломает ввод | C1 + C4 | 🔴 |
| 6 | `:5176/admin/tasks` | instrument | Dual New task; Trace ID в description; RU **контент** системных задач; пестрота badges | C3 + C2 + Law 8 | 🔴 |
| 7 | `:5176/admin/leads-log` | instrument | Регресс `titleOverride="Лиды (лог)"` при ключе `leadsTitle` | C1 | 🔴 |
| 8 | `:5176/admin/schedule` | instrument | Медкарта: вкладки хардкод RU; высота прыгает. «Врач» в New booking = API `display_role` | C1 + C3 + C2 | 🔴 |
| 9 | `:5176/admin/omni-chat` | instrument | Двойной Paper + meta-rail 56px; voice MIME; VK в каналах | C3 + C4 + C5 | 🔴 |
| 10 | `:5176/admin/sales` | instrument | **Нет `useTranslation`**, `crm.json` готов | C1 | 🔴 |

Порты `:3010` / `:5175` / `:5176` — **один SPA**, разный origin → **разный `localStorage.ui.locale`**. Это не два продукта.

---

## 2. Вердикты ролей (глобально)

### @LEAD

Приоритет лечения: **сначала то, что владелец назвал и что блокирует демо EN** (календарь, медкарта, leads-log, sales, staff-chat, tasks Trace ID / dual CTA, omni bubbles + audio + VK hide).  
Не в этой команде на код: полный RESKIN лендинга (нет концепта — Law 28), перевод `docs/`, смена ₽, DROP колонок VK, редизайн канбана «как Jira».

### @ARCH

1. **i18n:** ns уже зарегистрированы. Новые словари не плодить. Паттерн — wire.  
2. **`display_role`:** бэк **всегда** отдаёт RU строки (`Doctor.display_role`: «Врач» / «Мастер» / …). Это не chrome страницы — это **сломанный контракт локали**. Лечить маппингом `specialist_role` → i18n на FE (кастомное имя — data).  
3. **System tasks:** title/description зашиты RU + `trace_id=` в body, хотя колонка `tasks.trace_id` уже есть. Law 8.  
4. **Omni MIME:** `allowed_omni_upload_mime` принимает `audio/*` и `video/webm`, **не** `application/octet-stream`. Браузер часто шлёт webm как octet-stream.  
5. **VK:** `omni_channels.type` — свободная строка, не enum. Прятать UX; webhook/OAuth — выключить для международного контура; **не** DROP `patients.vk_id` без аудита данных.  
6. **₽:** регион клиники, не UI locale.

### @QA_ARCH

- Law 8: UUID `trace_id` / `event_id` в UI задачи = 🔴.  
- Law 26: медкарта без фиксированной высоты панели = 🔴 (прыжок).  
- Law 9: empty states в целом есть; канбан empty create CTA с `onClick: () => {}` — дыра.  
- Vector i18n: roadmap солгал «A3/A5/A6 закрыты» — диск: PatientEntityDrawer, StaffChat, Sales без `t()`.  
- Security surface этой волны: S7 files (upload), S8 webhooks (VK), S9 PII (карточка пациента). Нужен Security Contract в ТЗ.

### @QA

Стратегия после кода (не сейчас): unit на `formatTimeHHMMInput` / native time; i18nDefaultEn grep-расширение «нет кириллицы в JSX chrome перечисленных файлов»; e2e calendar EN labels; omni upload `.webm`; leads-log heading `Leads (log)`.

### @FRONTEND

REGISTER по страницам: admin = **instrument / THE FLOOR** (`VISUAL_CRAFT` §11). Не изобретать вторую палитру. Один Button primitive. Omni: один пузырь, timestamp внутри, не отдельный «шкафчик» 56px. Канбан: один метод сепарации карточки (тон **или** hairline, не tint+border+shadow).

### @MOTION

Landing: MODE CONCEPT **заблокирован** отсутствием `docs/artifacts/VISUAL_CONCEPT_*` — это волна B, не A.  
Операционка: MODE MICRO — календарь (фокус time input, без layout-shift), omni (появление пузыря opacity/transform only), медкарта (табы не меняют геометрию окна).

### @DESIGN — зафиксированные решения (не варианты)

| Экран | Решение | Референс |
|-------|---------|----------|
| Tasks | **Оставить Kanban.** Один New task. Column meta: count всегда; LIMIT/SLA/aging только если лимит задан или count>0. Карточка: **hairline only**, без tint/shadow/status-bar/status-badge (статус = колонка). Priority — текст xs, не второй rail. Stream — без gradient. | Linear board + Notion quiet |
| Omni thread | Пузыри **к краям** (in start / out end). Один контейнер; meta 11px **внутри**. Убрать spacer 28px и колонку 56px. Outgoing: `--primary-alpha-12`. Gap списка 8px. max-width ~68% колонки, не центрировать 420px. | Telegram / Intercom |
| Patient modal | `ScrollArea h={440}` как booking. Запрещён `Autosize mah`. Law 8: не slice UUID пакета. | Stripe customer drawer |
| Calendar time | Create **и** edit: дата + `type=time` 24h. All-day: без time. `datetime-local` не использовать. Маску удалить. | Google Calendar |
| Landing | Не косметить «ещё карточками». Волна B: concept → MOTION → RESKIN. | Editorial, не Linear |

I1–I12: полная таблица в ТЗ rev 2 (не «остальное N/A» без списка).

### @QA_VISUAL

Таблицы A–H по страницам — §4. Без 🟢 пока не закрыты 🔴 Law 26 (медкарта) и D1 (канбан hue-спам).

---

## 3. Постраничный диагноз

### 3.1 `/` Landing — statement

**Verified:** `MarketingLandingPage.tsx` использует `marketing.*`. Кириллицы в user-facing JSX нет.  
**Craft:** hero «текст слева + mockup справа», bento-карточки, серый SaaS-градиент → EDITORIAL Y (робость): страница выглядит как settings с большой кнопкой.  
**VISUAL_CONCEPT:** файла в `docs/` **нет**. Law 28: менять statement-эстетику без концепта = импровизация.  
**Лечение сейчас:** не трогать в волне A. Волна B — отдельное решение владельца.

### 3.2 `/signup`

**Verified:** chrome на `marketing` + checkout. Полей phone / Ivan **нет**.  
Скриншот «+7 / Ivan Ivanov / Врач» — это **New booking** на schedule (`SchedulePage.tsx:124` placeholder `+7...`; `en/schedule.json` `fullNamePlaceholder` = Ivan Ivanov; label «Врач» = `display_role` с бэка).  
**Лечение signup:** нет. Placeholders schedule — волна A (C2/region copy).

### 3.3 `/admin` Feed

**Verified:** `useTranslation("feed")`. Кириллица в JSDoc. ₽ в revenue — region.  
**Craft:** instrument density нормальна. Dual CTA нет.  
**Лечение:** вне P0.

### 3.4 `/admin/staff-chat`

**Verified:** в файле **нет** `useTranslation`. `label="Участники"` (~693). Ключ `chat.staff.members` = `"Members"` уже есть. Десятки литералов («Чат команды», «Новая группа», …).  
Пузыри staff проще omni (токены `adminChatIncoming/OutgoingBubbleStyle`) — это **лучше** omni, не наоборот. Не подтягивать staff к раздутому omni; omni подтянуть к плотности staff, с аккуратным sent-tint.  
**Лечение:** C1 wire `chat.staff.*`.

### 3.5 `/admin/calendar`

**Verified:** `AdminStaffCalendarPage.tsx` **не** импортирует `react-i18next`. Ключи `schedule.staffCal` — 87/87 en/ru, включая `participants` / `acked`.  
Литералы «Участники:» (~1245), «Подтвердили:» (~1257), «Календарь», intro, «Сегодня», «Новое событие», дни `Пн…Вс`, ошибки формы — весь chrome.  
**Время:** `formatTimeHHMMInput` (~87–94): 3 цифры → pad `0` → `123` становится `01:23`; backspace с `12:30` через `12:3` снова `01:23`. Create = masked text; edit = `datetime-local`. Минуты колеса только ×5.  
**Не причина:** module-scope `dayjs.locale("ru")` (снято).  
**Лечение:** C1 wire + C4 native `type="time"` оба режима.

### 3.6 `/admin/tasks` Kanban

**Verified dual CTA:** ContextBar ~935 и toolbar ~1131 — оба `t("newTask")` → `setCreateOpened(true)`. Тест кликает `[0]`.  
**Trace ID:** бэк дописывает в description (`tasks_event_handlers.py:102–103, 171–172`) при живой колонке `trace_id`. FE рендерит `{task.description}` (`TaskDetailsView`). Канбан-карточка description **не** показывает. Law 8.  
**RU в EN:** chrome задач на ключах. Тело «Обработать no-show…» — **системный шаблон на русском**. Это C2, не забытый `t()`.  
**Пестрота:** колонка всегда LIMIT + SLA OVERDUE + IN PROGRESS 48H+ + count; карточка status+priority+blocked + tint+border+shadow (X1, три сепарации); stream gradient; второй New task; баннер Needs approval.  
**Kanban vs table:** статус — главный глагол клиники → **доска уместна**. Перегружена chrome, не выбором паттерна.  
**Пустой create:** `onClick: () => {}` на empty CTA.  
**Лечение:** один CTA; тихий chrome; FE-strip diagnostics + бэк перестать писать UUID в body; EN-шаблоны system tasks.

### 3.7 `/admin/leads-log`

**Verified:** `AdminLeadsLogPage.tsx` передаёт `titleOverride="Лиды (лог)"`. `AdminTasksPage` делает `titleOverride ?? t("leadsTitle")`. EN ключ = `"Leads (log)"`. Roadmap прямо запрещал возвращать RU override — **регресс**.  
**Лечение:** удалить prop (одна строка).

### 3.8 `/admin/schedule` + медкарта

**Verified вкладки:** `PatientEntityDrawer.tsx:266–271` хардкод RU. **Нет** `useTranslation`. Ключи `directory.patientDrawer.tabMain`… уже EN (`Overview`, `Visits`, …). Поля «Телефон», «ФИО», «LTV — при наличии API», «Загрузить AI-обзор». Uppercase в chrome визуально даёт «ТЕЛЕФОН».  
**Прыжок:** `GlassModal` body `maxHeight: min(78vh, 720px)` без фиксированной высоты панели. Контент notes >> comms → окно меняет высоту. `BookingEntityDrawer` уже имеет `BOOKING_MODAL_TABS_SCROLL_H = 440` — копировать паттерн.  
**New booking «Врач»:** `SchedulePage` create **уже** на `t()`. Label роли = `displayRole ?? t("specialist")`. Бэк `Doctor.display_role` **всегда** «Врач» для `specialist_role=doctor`. Поэтому EN UI показывает RU.  
**+7 / Ivan:** `placeholder="+7..."` захардкожен (регион). `fullNamePlaceholder` в **en** словаре = «Ivan Ivanov» — поправить копию словаря на Jane Doe, **не** ветвить маску телефона от locale. Showcase Austin с телефонами `+700910*` — долг сида (NEXT), не P0.  
**BookingEntityDrawer:** тоже без `t()`, литерал «Врач» (~266, 438, 443) при готовых `schedule.drawer.*`.

### 3.9 `/admin/omni-chat`

**Gaps:** внешний `Paper p={6}` + внутренний `Paper p="sm"` + отдельный meta `Paper` width 56 (~1078–1178). Плюс `Stack gap="xs" p="md"`. Короткое «Perfect. Thank you.» живёт в шкафу.  
**Voice:** `VoiceNoteRecorderButton` → `voice-*.webm`. Upload: MIME с multipart; если `application/octet-stream` → 400 «Недопустимый тип файла». FE мапит любую ошибку в `errors.sendFileFailed`. `audio/*` в allowlist **есть** — ломается **дефолт octet-stream**, не запрет audio.  
**VK:** пользователь не видел иконку в inbox (демо без VK-чатов) — канал **есть**: `CHANNEL_TYPE_OPTIONS` включает `VK_BOT`, credentials UI, OAuth patient `vk`, webhook gateway. Для международной аудитории — скрыть создание и login-кнопку; существующие ряды читать.  
**Лечение:** один пузырь; sniff `.webm` → `audio/webm`; показать `code` ошибки; убрать VK из create/OAuth UI.

### 3.10 `/admin/sales`

**Verified:** `ContextBar title="CRM‑воронка продаж"` (~503, 511). Нет `useTranslation`. `en/crm.json` `pipeline.title` = `"Sales pipeline"`. Фильтры, empty states, заметки — литералы.  
**Лечение:** C1 wire `crm`.

### 3.11 `/admin/finance` (со скрина, вне нумерованного списка)

Chrome на `money.finance`. Символ **₽** — N/A region. Не чинить как i18n.

---

## 4. Продолжение списка (не запрошенные URL, тот же класс C1)

Кириллица в `frontend/src/admin/pages/*.tsx` (в т.ч. JSDoc). Приоритет по плотности user-facing:

| Плотность | Страницы | Заметка |
|-----------|----------|---------|
| Высокая | Commerce, Administrators, OmniChannels, Recall, Loyalty, Forms, Marketing, Waitlist, Bookings, PaymentGateway, EmergencyNotifications, Retention, Discounts, DoctorSchedule, Prepayment | Скорее всего те же «ключи есть / wire нет» |
| Средняя | Embed, AiSettings, OmniVault, RightsPolicies, Styling, Clinics, Knowledge, Services, Doctors, Channels | Directory ns частично готов |
| Низкая / хвост | Settings, OmniAi, DataExport, Agreements | |
| Почти чисто | Dashboard, Reports, Tasks chrome (контент — C2) | |

Полный EN-проход всех страниц = **волна A2** после P0 владельца. Не смешивать с P0 в одном промпте (Law 1).

---

## 5. Aesthete verdict (каталог A–H)

Правило: пустая клетка запрещена. 🔴 блокирует визуальный 🟢.

### Landing `/`

| Блок | Итог |
|------|------|
| A Ритм | 🟠 A4 карточки одного веса подряд |
| B Состояния | 🟢 (не аудировали hover числом — код; скрин rest) |
| C Типо | 🟡 C3/Y: display не statement-scale |
| D Цвет | 🟢 низкая chroma, instrument palette на statement |
| E Композиция | 🟠 E4 всё одинаково важно; E5 ряд клонов-карточек |
| F Семантика | 🟢 CTA Sign in / Get started на месте |
| G Экраны | 🟡 P1 равные секции; hero не «держит» statement-жест |
| H Детекторы | Y1–Y4/Y7 робость; X12 карточки-клоны. **Волна B** |

### Signup

| Блок | Итог |
|------|------|
| A–G | 🟢 форма на существующем паттерне |
| H | ⚪ N/A statement-жест; это checkout |

### `/admin` Feed

| Блок | Итог |
|------|------|
| A | 🟢 |
| B | 🟢 |
| C | 🟢 chrome |
| D | 🟢 |
| E | 🟢 instrument |
| F | 🟢 |
| G | ⚪ N/A лендинг-секции |
| H | 🟢 FLOOR |

### Staff-chat

| Блок | Итог |
|------|------|
| A | 🟠 список карточек с большим padding (как omni inbox) |
| B | 🟢 |
| C | 🟢 |
| D | 🟢 quieter чем omni thread |
| E | 🟠 E2 пустой центр до выбора |
| F | 🟢 |
| G | ⚪ |
| H | ST плотность; i18n 🔴 не визуал |

### Calendar

| Блок | Итог |
|------|------|
| A | 🟢 сетка дней |
| B | 🔴 C4 ввод времени = «поле врёт»; B2 если overlap disable путает с broken input |
| C | 🟢 |
| D | 🟢 `--staff-cal-*` спокойнее канбана |
| E | 🟢 |
| F | 🟢 |
| G | ⚪ |
| H | 🔴 chrome RU (не A–G, но блокер демо) |

### Tasks Kanban

| Блок | Итог |
|------|------|
| A | 🟠 A1 dual primary разной size (sm vs xs) |
| B | 🟢 |
| C | 🟠 C4 bold/badge инфляция |
| D | **🔴 D1** orange+green+blue+pink badges сразу; X4 |
| E | 🟠 E4 нет героя; всё орёт |
| F | 🔴 F2 два New task; F4 WIP на каждой колонке всегда |
| G | 🟠 stream+approval+board = три «экрана» до работы |
| H | X1 три сепарации карточки; ST4 chrome всегда виден |

### Leads-log

| Блок | Итог |
|------|------|
| A–G | 🟢 пустой Move audit (empty OK) |
| H | 🔴 C1 title RU |

### Schedule + patient modal

| Блок | Итог |
|------|------|
| A сетка | 🟢 equal columns |
| B | 🟢 |
| C | 🟢 страница; модалка C1 uppercase labels |
| D | 🟢 status left-rail |
| E | 🟢 |
| F | 🟢 |
| G | ⚪ страница; **модалка 🔴 Law 26** высота |
| H | 🔴 вкладки RU; B4/V1 прыжок окна = геометрия |

### Omni-chat

| Блок | Итог |
|------|------|
| A | **🔴 A2/A4** пузыри разной «коробки»; гигантский gap |
| B | 🟠 ошибка файла есть, но generic |
| C | 🟢 |
| D | 🟠 indigo outbound + blue OPEN + gray IN PROGRESS — терпимо если thread тише |
| E | 🟠 E2 огромный gutter вокруг пузырей |
| F | 🟢 inbox / thread / tickets |
| G | ⚪ |
| H | E6 плотность не под чат; X1 nested Paper+border+shadow |

### Sales

| Блок | Итог |
|------|------|
| A–G | 🟢 empty funnel geometrically quiet |
| H | 🔴 C1 страница RU |

---

## 6. Связь фронт ↔ бэк (что нельзя «починить только CSS»)

| Симптом | Слой | Контракт |
|---------|------|----------|
| Trace ID в задаче | BE пишет в description + FE показывает | Перестать concat; FE sanitize; колонка остаётся |
| RU no-show task | BE hardcoded templates | Locale-aware или EN-default шаблоны |
| «Врач» в EN | BE `display_role` RU | FE map enum; не ждать двуязычный бэк в P0 |
| Voice fail | BE MIME + FE toast | Sniff extension; structured `code` |
| VK | FE options + BE webhook + OAuth | Hide + disable; no DROP |
| Stream name «Продажи» | API/seed data | Showcase EN overlay (уже частично); не t() произвольных имён |

---

## 7. Что сознательно не чиним в волне A

- Символ ₽ и YooKassa как провайдер.  
- Полный RESKIN лендинга без VISUAL_CONCEPT.  
- Перевод тел сообщений чата и ФИО.  
- Канбан → таблица как замена.  
- DROP `vk_id` / удаление исторических `VK_BOT` рядов.  
- Пациентский PWA (`/app`, `/c/:slug`) — вне списка владельца.  
- `docs/` и closed `roles/`.

---

## 8. Completeness ledger (spot-check Law 41)

| # | Утверждение | Состояние | Доказательство |
|---|-------------|-----------|----------------|
| 1 | Календарь не на `t()` | DECIDED | нет import react-i18next |
| 2 | Ключи staffCal существуют | DECIDED | `en/schedule.json` participants/acked |
| 3 | Маска времени ломает 3 цифры | DECIDED | `formatTimeHHMMInput` L87–94 |
| 4 | Dual New task | DECIDED | L935 и L1131 |
| 5 | Trace в description | DECIDED | `tasks_event_handlers.py` concat |
| 6 | Leads title override | DECIDED | `AdminLeadsLogPage.tsx` |
| 7 | Медкарта вкладки RU | DECIDED | PatientEntityDrawer L266–271 |
| 8 | display_role всегда RU | DECIDED | `doctor.py:46–58` |
| 9 | Omni nested Paper | DECIDED | AdminOmniChatPage ~1078 |
| 10 | VK в CHANNEL_TYPE_OPTIONS | DECIDED | AdminOmniChannelsPage L35 |
| 11 | Sales без t() | DECIDED | title литерал L511 |
| 12 | Signup без Ivan | DECIDED | SignupPage нет phone fields |
| 13 | VISUAL_CONCEPT отсутствует | DECIDED | glob 0 files |
| 14 | audio/* в allowlist | DECIDED | omni_media_storage L30–31 |
| 15 | octet-stream не в allowlist | DECIDED | allowed_omni_upload_mime |
| 16 | specialist_role уже в DoctorRead + FE types | DECIDED | doctor_dto.py L23; types.ts L57 |
| 17 | Upload helper `_err` уже есть | DECIDED | admin_omni_chat.py L111–112; upload path его не использует |
| 18 | patientDrawer keys покрывают вкладки+поля | DECIDED | directory.json L41–123 |
| 19 | doctorDrawer.roles.* | DECIDED | directory.json L196–206 |

---

## 9. Ревью пакета документации (2026-08-23, второй проход)

Пакет v1 был **завершён** (три файла + индекс). Код не писался. Этот проход закрывает дыры, из-за которых @DEV гадал бы или сломал контракт.

| ID | Класс | Что было формально / ложно | Исправление |
|----|-------|----------------------------|-------------|
| R1 | 🔴 противоречие | §0 «не менять +7» vs ТЗ A5 «EN → +1 от locale» | A5 отозван. Маска телефона ≠ ui.locale |
| R2 | 🔴 гонка | Q8+Q9+Q10 все пишут `AdminOmniChatPage.tsx` | Владелец файла Q8; Q9 только BE; Q10 — icon function |
| R3 | 🔴 гонка | Q6 и Q10 оба `AdminTasksPage` (placeholder VK) | Placeholder VK входит в Q6 |
| R4 | 🔴 сломает edit | D4 «заменить всё на type=time» при edit = `datetime-local` (дата+время) | Контракт: create/edit = дата + time; all-day без time |
| R5 | 🔴 неверный ключ | A2 `t("directory.roles.*")` | Факт: `t("doctorDrawer.roles.{{role}}")` ns `directory`. `specialist_role` уже в DTO |
| R6 | 🔴 Law 8 пропуск | `PatientEntityDrawer` режет `subscription_package_id.slice(0, 8)` в UI | Q2: не показывать UUID |
| R7 | 🔴 код ошибки | ТЗ `OMNI_FILE_TYPE_DENIED` | В роутере уже `_err(code, message)` и стиль `omni_*` lowercase |
| R8 | 🟠 формальный тест | Q1: unit на `formatTimeHHMMInput` после её удаления | Тестировать native time + all-day, не мёртвую маску |
| R9 | 🟠 D2 ухудшит gaps | `max-width: 420px` в широкой колонке = ещё больше полей по бокам | Пузыри к краям; убрать spacer 28px и meta 56px |
| R10 | 🟠 D1 vs `taskStatusCardSurface` | Карточка уже border+shadow+tint+bar (4 сепарации). «Rail для priority» конфликтует со status-bar | Карточка: hairline, без tint/shadow/status-bar; priority текстом |
| R11 | 🟠 существующие RU задачи | Q7 чинит только новые ряды; скрин владельца останется RU | NEXT: re-seed / remap; FE sanitize только UUID |
| R12 | 🟠 OmniChannels C1 | Ключи `chat.channelType.*` есть, страница хардкодит «Telegram бот» | Входит в Q10 (тот же файл, что VK hide) |
| R13 | 🟡 L5 grep-гейт | Задекларирован в LPA, нет промпта | Q13 + NEXT CI |
| R14 | 🟡 MICRO MOTION | Заявлен, артефакта нет | Не плодить фейковый SPEC: запрет layout-shift, без новой анимации |
| R15 | 🟡 I1–I12 | «остальное N/A» без таблицы | Полная таблица в ТЗ |

Следующие шаги вне волны A (исполняемые промпты, не список имён): [`FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md`](./FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md).

---

## 10. Третий проход (2026-08-23) — решения ↔ диск ↔ очередь

Код по-прежнему не писался. Проход закрывает **формальные** промпты (минимум-списки, ложный D4, гонки JSON) и фиксирует, **что владелец увидит после A**.

### 10.1 Что сломалось бы, если исполнить rev 2 as-is

| ID | Класс | На диске | Если не чинить |
|----|-------|----------|----------------|
| R16 | 🔴 UX/контракт | `formatTimeHHMMInput` live-pad 3 цифр; edit = `datetime-local`. Rev 2 велел `type="time"` | Chrome/Windows: цифры по-прежнему не набираются свободно. Баг владельца **не закрыт**, только сменён виджет |
| R17 | 🔴 C1 дыра | `AdminSalesPipelinePage.tsx`: десятки литералов сверх «минимума» (AI, статусы Открытые/Успех/Потеряно, «Загрузить ещё», toLocaleDateString) | После Q5 на EN остаётся RU — «сделали i18n» формально |
| R18 | 🔴 C1 дыра | `BookingEntityDrawer.tsx`: вкладки, Сводка, Пациент, копирование ссылки, комментарий, расходники — не только «Врач» | New booking без «Врач», карточка визита всё ещё RU |
| R19 | 🔴 C1 дыра | `PatientEntityDrawer.tsx`: меню Печать/Копировать, финансы, family modal, slice(0,8) — не только вкладки | Law 8 + кириллица в теле карточки |
| R20 | 🔴 гонка JSON | Q1 и Q3 оба могли писать `schedule.json`; Q4/Q8/Q10 — `chat.json` | Parallel batch overwrite словаря |
| R21 | 🟠 crash | `doctorRoleLabel` как хук внутри обычной функции | Invalid hook call на сетке расписания |
| R22 | 🟠 геометрия | 6 вкладок пациента + `grow` на 360 | Высота хрома прыгает несмотря на ScrollArea 440 |
| R23 | 🟠 семантика | Q6 «убери taskStatusCardSurface» без оговорки details | Канбан и карточка деталей становятся одинаково слепыми **или** @DEV оставляет мёртвый dual API |
| R24 | 🟠 приёмка vs демо | Q7 меняет только **новые** ряды | Скрин no-show останется RU до A2-SEED — не регрессия A |
| R25 | 🟠 Q3 формулировка | «title = t(leadsTitle) внутри AdminTasksPage» + «не трогай AdminTasksPage» | @DEV правит оба файла или ничего |
| R26 | 🟡 ключи | Промпт weekdays `schedule` vs диск `common.calendar.weekdays.*` | Лишние ключи или непереведённые Пн–Вс |
| R27 | 🟡 тесты | Нет `AdminStaffCalendarPage.test.tsx`; handlers pytest отсутствует | Q1/Q7 «тест зелёный» нечего запускать — надо **создать** |
| R28 | 🟡 MIME | `allowed_omni_upload_mime` есть; `sniff_*` **нет**; upload string `detail` | Voice webm+octet-stream падает; FE `err.code` пустой |

### 10.2 Что станет после A (честный результат)

Сработает: EN chrome на запрошенных URL; набор времени text+blur; стабильная высота медкарты (если nowrap вкладок); одна New task; quiet kanban; omni пузыри у края; voice sniff; нельзя создать VK; Jane Doe; +7 в EN.

Не сработает и это **не баг A:** старые system-task titles в БД; ₽; лендинг statement; остальные admin C1; `clinic.locale` для шаблонов.

### 10.3 Критерии аудита, добавленные сверх запроса

1. **Исполняемость промпта:** каждая user-facing строка файла → ключ, не «минимум».  
2. **Один писатель JSON-файла в батче.**  
3. **Контракт ввода ≠ смена input type.** Проверять модель взаимодействия (набор цифр), не HTML-атрибут.  
4. **Хелпер i18n:** `i18n.t` как `chatI18n.ts`, не хук.  
5. **Геометрия модалки = chrome + viewport табов**, не только ScrollArea.  
6. **Ожидание vs БД:** новые ряды vs seed.  
7. **Security envelope:** `_err({code,message})` ↔ `parseFastApiErrorBody` nested `detail.code`.  
8. **Не чинить locale деньгами и телефоном.**

Пакет лечения: ТЗ + очередь **rev 3**. Код — после ручной вставки очереди владельцем.

