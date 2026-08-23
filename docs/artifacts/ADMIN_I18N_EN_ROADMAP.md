# Admin i18n — EN default, RU second

> **Дата контракта:** 2026-08-17 (ревью @LEAD / @ARCH / @QA_ARCH / @FRONTEND / @DESIGN — тот же день)  
> **Решение @LEAD:** английский — базовый язык **всей админки**. Русский — полный второй словарь. Каталог **`docs/` не переводить**. Пациентский PWA и маркетинговый лендинг — **вне этой волны**.  
> **A0–A12 приняты в коде** (A0–A7: 2026-08-17; A8–A12: 2026-08-18; у каждого батча audit в тот же день; **A12-audit** + **A12-repass** тот же день). **Волна admin chrome закрыта.** Не перезапускать A0–A12. Остаток — нумерованный «Вне очереди» (маркетинг/patient/`index.html`/SEO + HTML 4xx transport), не QUEUE A13.

**Приоритет истины:** код. Этот файл — очередь исполнения и **закрытый контракт**, не черновик.

### Маршрут (куда идти)

| Сейчас | Следующий промпт | Зачем так |
|--------|------------------|-----------|
| **A12 + A12-audit + A12-repass** | нет QUEUE — **Вне очереди** (14 пунктов) | chrome админки на ключах; 401/405/502 не вспыхивают RU на `/admin*`; маркетинг/patient/SEO — отдельный разговор |
| A0–A11 | не перезапускать | история батчей ниже; смешанный EN-nav + RU-страница **было** нормой только между батчами |

---

## Review pass (что было формально и сломалось бы)

Первый драфт очереди объявлял «каркас → экраны → shared в конце». По коду это не работает:

| Дыра | Факт в коде | Что будет, если оставить как было |
|------|-------------|-----------------------------------|
| Провайдер «вокруг админки» | `/admin/login` = `ClinicSignInPage` **вне** `AdminLayout` (`App.tsx`: login sibling к layout) | Login без `useTranslation` → crash или ключи на экране |
| Переключатель «в шелле» | Логин не видит шелл | РФ-сотрудник не может выбрать RU до входа; после F5 на login снова только default |
| `dayjs.locale("ru")` на импорте | `CompactMonthPicker.tsx` строка модуля; то же в `AdminStaffCalendarPage` | Любой импорт календаря **глобально** ставит RU, даже если страница вызвала `useUiLocale` |
| Shared-дефолты RU | `QueryErrorAlert` title по умолчанию «Не удалось загрузить данные»; `formatQueryError` RU; `BOOKING_STATUS_LABEL_RU` | A2 «готов», сетка EN, тост/статус/ошибка — RU |
| Полоса подписки в layout | `AdminOwnerSubscriptionStrip` внутри `AdminLayout` | Каждый экран A2–A8 с EN nav и русской полосой тарифа |
| RBAC-остров | `useState<UiLocale>("ru")` + свой SegmentedControl | Два источника правды; страница прав остаётся RU при глобальном EN |
| E2E логина | `frontend/e2e/smoke-routes.spec.ts` искал «Вход для сотрудников клиники» | **Закрыто A11:** EN `Clinic staff sign-in` + SignInShell title; **A11-audit:** `ui.locale=en` в init, `npm run build` зелёный (PWA 3 MiB) |
| `SignInShell` общий | Staff + founder (`PlatformFounderLoginPage`) + `PublicLoginPage` | Перевод колонки шелла меняет маркетинг/основателя без их батча |
| A10 после экранов | Empty/error chrome живёт в shared | Гейт «нет кириллицы в `admin/`» зелёный, пользователь всё равно видит RU из shared |
| Карта A9 vs A7 | В старой карте A9 числились discounts | Агент мог тронуть A7-файлы повторно |
| Гейт «комментарии на EN» vs «исключить комментарии» | Противоречие в одном файле | A12 либо океан правок комментариев, либо дырявый grep |
| `ErrorBoundary` — class | Хуки в class не работают | «перевести ErrorBoundary через `useTranslation`» без fallback-компонента = не соберётся |
| `index.html` `lang="ru"` | Первый paint всего SPA | Не менять в этой волне (маркетинг `/` ещё RU). Runtime `document.documentElement.lang` — только на `/admin*` и staff sign-in |

Ниже — **закрытые решения**. Старый смысл очереди (батчи, не 50 файлов) сохранён; зависимости между батчами исправлены.

---

## 0. Контракт i18n

| Правило | Значение |
|---------|----------|
| Библиотека | `i18next` + `react-i18next` (MIT). **Не** добавлять `i18next-browser-languagedetector` — он подерётся с default `en`. |
| Default | **`en`**. Нет ключа `ui.locale` в `localStorage` → `en`. |
| RU | locale `ru`, полный параллельный JSON того же набора ключей. Дырявый ключ в `ru` → fallback **`en`**, не литерал из JSX. |
| Хранение | `localStorage` ключ **`ui.locale`** (`en` \| `ru`). Слушать `storage` (другие вкладки). |
| Хук | `useUiLocale()` в `frontend/src/i18n/useUiLocale.ts` (чтение + `setLocale`). Строки в UI — `useTranslation(ns)`. |
| Провайдер | **`I18nextProvider` в `frontend/src/main.tsx`** (рядом с Mantine), на всё дерево. Обернуть только `AdminLayout` = login мёртв. |
| Тестовый harness | `frontend/src/i18n/testUtils.tsx`: **`await renderWithI18n(ui, { locale: "en" })`** (функция async). Батчи без него роняют `useTranslation`. |
| Словари | `frontend/src/i18n/locales/{en,ru}/<ns>.json` |
| Namespaces (закрытый список) | `common`, `nav`, `auth`, `schedule`, `bookings`, `directory`, `tasks`, `chat`, `crm`, `money`, `reports`, `feed`, `settings`, `rbac`. Новый ns = JSON `en`+`ru` **и** запись в `frontend/src/i18n/index.ts` (`resources` + `I18N_NAMESPACES`) **и** `i18next.d.ts`. «Не пересобирай init» ≠ «не регистрируй ns». Не трогать: `fallbackLng`, detector, `useSuspense`, default `en`. |
| Init | `fallbackLng: "en"`, `defaultNS: "common"`, `interpolation.escapeValue: false`, **`react.useSuspense: false`**, `initAsync: false` (словари в бандле). Resources **клонируются** при init. |
| Переключатель | Один компонент `frontend/src/i18n/UiLocaleSwitch.tsx` (SegmentedControl EN/RU, §2). A1 только **ставит** его. Не форкать второй контрол. |
| Календарная сетка | `CompactMonthPicker`: **Пн→Вс в обоих locale** (европейская клиника). EN не переключает на Sunday-first. |
| Missing keys | В `en` отсутствующий ключ **виден** (ключ на экране = дыра батча). В `ru` → `en`. |
| Plural | Счётчики только `t(key, { count })` (формы `_one/_few/_many/_other` для `ru`). Конкатенация `"записей: " + n` запрещена. |
| Interpolation | Имена/даты — `{{name}}`, не склейка строк. |
| dayjs | **Один** sync в `i18n/index.ts`: `dayjs.locale(uiLocale)` + импорт `dayjs/locale/ru` и `en`. **Запрещено** `dayjs.locale(...)` на уровне модуля. Verified A0-audit: снят с `CompactMonthPicker` **и** с `AdminStaffCalendarPage` (eager import из `App.tsx` иначе убивал clock на всём SPA). A2 не возвращать module-scope locale. |
| RBAC | С A1: `useUiLocale()` + тот же `UiLocaleSwitch`; **удалить** локальный SegmentedControl на странице прав. Copy в `.ts` может жить до A9b. Подписи сегментов — **EN/RU**, не «English»/«Русский». |
| Даты в JS | `toLocaleString()` / `toLocaleDateString()` в админке — с locale из `useUiLocale()` (`en-US` \| `ru-RU`), не хардкод `"ru-RU"` в admin pages. |
| Деньги | Символ/провайдер (₽, YooKassa) — **регион клиники**, не язык UI (L3 OSS-плана). Не «переводить ₽ в $». |
| API `detail` | **Не** переводить сырой текст бэка. Есть `code` → ключ `common.errors.<code>`. Нет кода → `formatQueryError` как сейчас (часто RU с бэка) — **заявленный лимит волны**, не долг A12. |
| `formatQueryError` | **Не** переписывать в A0 на EN-generic: пациентский PWA передаёт те же тела. Admin: где важен смысл — маппить `code` на экране. |
| Тесты | Видимый chrome — **EN** (default) или `i18n.t('key')`. Фикстурные ФИО («Иванов Иван») — данные, не chrome. |
| E2E владельцы | Спека экрана чинится **в батче экрана**, не откладывается на A11. A11 — только хвосты. |
| Вне скоупа | `docs/**`, user guides в `documentation/**` (кроме ссылки на этот файл), `frontend/src/app/**`, маркетинг-страницы **форм**, бэкенд `patient_messages.py`. |
| В скоупе сверх `admin/` | `ClinicSignInPage`, `ClinicStaffSignInPanel`, `SignInShell` (split chrome), `frontend/e2e/smoke-routes.spec.ts` (только кейс `/admin/login`). |
| Качество | Нет `# TODO` на ключах уже видимого chrome. Law 1: файлы батча + словари его ns. |
| Git | Law 40: агент **не** делает `git commit` / `git push`. |
| Лицензия deps | MIT/Apache; i18next stack — MIT. |

### Гейт волны (после A12)

В JSX/строковых литералах **chrome** (то, что видит пользователь: кнопки, title, Alert, aria-label, nav, EmptyState) нет кириллицы в:

- `frontend/src/admin/**/*.{ts,tsx}`
- `frontend/src/auth/ClinicSignInPage.tsx`
- `frontend/src/auth/panels/ClinicStaffSignInPanel.tsx`
- `frontend/src/auth/SignInShell.tsx`
- shared, которые админка показывает без своего title: `QueryListStates.tsx`, `CompactMonthPicker.tsx`, `bookingStatusMeta.ts` (только `bookingStatusLabel` → `bookings.status.*`), `aiFeatures.ts` (tooltip/label), `errors.ts` **admin-path** (`code` → `common.errors.*`; 401 transport → `unauthorized`). `getBookingErrorMessage` — patient, не гейт админки. `AdminOwnerSubscriptionStrip.tsx`

**Не гейт:** комментарии кода; русские ФИО/тексты сообщений как **данные** в тестах; `index.html`; маркетинг `/`; patient `/app`; сырой API `detail` без `code`.

Переключатель: login (`SignInShell`) **и** admin header. Одинаковый контрол. F5 сохраняет locale.

---

## 1. Архитектура (закрыто @ARCH)

1. **Один clock locale.** `useUiLocale` → i18next `changeLanguage` + `dayjs.locale` + `document.documentElement.lang` на маршрутах `/admin*` (включая `/admin/login`). Вне `/admin*` runtime возвращает `lang` публичного шелла (`ru` = `index.html` этой волны). Подписка на `pushState`/`replaceState`/`popstate`: SPA-переход `/` → `/admin/login` тоже ставит lang, не только первый paint. Маркетинг и PWA не обязаны совпадать с `ui.locale` до своих волн (смешение на `/login` основателя — принятый средний риск, см. §3).
2. **Сложность:** i18n — UI concern, не новый bounded context, не ADR-номер. SPDX deps — MIT, Law 27.
3. **`SignInShell` split-колонка** переводится в A1. Побочный эффект: основатель `/platform/login` и `PublicLoginPage` получат EN/RU **оболочку**, формы внутри останутся RU до волны маркетинга. **Не** раздувать A1 на `PlatformFounderLoginPage` / `PublicLoginPage` body.
4. **Patient `QueryErrorAlert`:** всегда передаёт свой `title` (RU). Менять default title на `t()` в A0 безопасно для PWA. Тело ошибки (`formatQueryError`) не трогать оптом.
5. **ErrorBoundary** (class, в `App.tsx` на весь SPA): в A10 вынести fallback в **function** `ErrorBoundaryFallback` с `useTranslation("common")`. Не вызывать хук в class.
6. **Не** DatesProvider Mantine в этой волне, пока не появится `@mantine/dates` на админ-экране батча. Если файл батча уже использует dates — locale из того же хука.
7. HTML `index.html` (`lang="ru"`, title про запись) — **не** часть admin i18n; это публичный SPA-шелл / SEO. Отдельный разговор @SEO/@SCRIBE.

---

## 2. Дизайн переключателя (закрыто @DESIGN)

**REGISTER:** `instrument` (операционный контур). Не глобус, не маркетинговый жест, не второй «языковой остров» на RBAC.

| Решение | Значение |
|---------|----------|
| Паттерн | `UiLocaleSwitch` = существующий `SegmentedControl` size `sm`. Новый композиционный паттерн не вводим — отдельный `DESIGN_SPEC_*.md` не нужен. |
| Подписи | **`EN` / `RU`** (равная ширина, `min-width` на сегмент, `tabular-nums` не нужен). Не «English» / «Русский» — рвёт геометрию. |
| Login | В колонке **формы** `SignInShell` (правая/нижняя), `Group justify="flex-end"`, над заголовком или под ним на одной вертикали с формой. Не в тёмной маркетинговой колонке. |
| Admin header | В chrome `AdminLayout` справа: после `ClinicSelector`, до блока пользователя/logout. Не в nav, не floating. |
| Геометрия | Law 26: hover/active **не** меняют высоту ряда. Сегменты equal-height с соседями шапки (V16). `flexShrink: 0`. |
| Один контрол | Компонент `UiLocaleSwitch`. После A1 на странице прав **нет** второго SegmentedControl языка. |
| A11 a11y | `aria-label` из `common.language` (EN: "Language") — **уже в `UiLocaleSwitch`**. A11 не дублировать. |

Референс: Linear / Stripe — locale в account/chrome, не hero.

---

## 3. Риски (оставшиеся, не «закрыто словами»)

| ID | Класс | Риск | Митигация в очереди |
|----|-------|------|---------------------|
| R1 | 🔴→🟢 | Login без провайдера | **Закрыто A0:** `I18nextProvider` в `main.tsx` |
| R2 | 🔴→🟢 | Глобальный `dayjs.locale("ru")` на import | **Закрыто A0-audit:** снято с `CompactMonthPicker` и с `AdminStaffCalendarPage` (eager import в `App.tsx`). A2 не возвращать. |
| R3 | 🔴→🟢 | CI e2e login после A1 | **Закрыто A11 + A11-audit:** спеки EN; `ui.locale=en` в init; `npm run build` (PWA precache 3 MiB) — иначе Jenkins/`build-and-test-entitlements` красные при зелёном Playwright на stale `dist/` |
| R4 | 🟠 | Смешанный язык на `/platform/login` и `/login` | Принято; не расширять A1. Body `PublicLoginPage` / founder остаётся RU до волны маркетинга |
| R5 | 🟠→🟢 | Полоса подписки RU в EN-шелле | **Закрыто A1:** `AdminOwnerSubscriptionStrip` на `common.subscription.*` |
| R6 | 🟠→🟢 | Статусы записи RU на EN bookings | **Закрыто A2 + A2-audit:** `bookingStatusLabel` / `bookings.status.*`; сетка не маскирует `awaiting_payment` под occupied; waitlist/recall enum chrome на ключах |
| R7 | 🟠→🟢 | Spotlight tooltip из `aiFeatures.ts` | **Закрыто A1:** `common.ai.tooltip.*` + labels; A1-audit: хук подписан на `languageChanged`, гейт не кэширует stale string |
| R8 | 🟡 | `toLocaleString()` без locale на экранах | В каждом батче страницы, где уже есть вызов |
| R9 | 🟡 | A9 жирный (15 экранов) | Разрезан на A9 + A9b (RBAC JSON) |
| R10 | 🟡 | Сырой `detail` без code; HTML 4xx без transport-кода; RU текст в `normalizeErrorMessage` для patient | Не маскировать API `detail`. 401 admin **закрыт A12-audit**. 405 / 502–503 / 5xx-traceback **штампуют** `method_not_allowed` / `internal_server_error` (A12-repass 2026-08-18) — админский Alert мапит ключ, patient видит прежний RU `message`. HTML 4xx и короткий 5xx без code — ещё R10 |
| R11 | 🟡→🟢 | Грейп кириллицы бьёт комментарии | **Закрыто A12:** классификатор chrome vs comment vs data; комментарии не переводили |
| R12 | 🟢 | Две вкладки, разный locale | A0: `storage` event |
| R13 | 🟡 | Переключатель скрыт при свёрнутом navbar (80px) | Принято A1-audit: `AppShell.Header` нет; `UiLocaleSwitch` size sm не влезает без overflow (Law 26). Смена языка — после разворота сайдбара. Не плодить второй контрол и не масштабировать сегменты |
| R14 | 🟡 | Native HTML `required`/`type=email` — текст браузера, не `ui.locale` | Лимит волны. Пароль min: HTML `minLength` снят в A1-audit, ошибка через ключ. Остальной native constraint — не изобретать form-lib в A2–A12 |
| R15 | 🟡 | Два clinic picker: inline Select в `AdminLayout` и `ClinicSelector` | Оба на `common.clinics.*`. Не сливать в A2 без отдельного решения. A12 не гейтит дубль компонента |
| R16 | 🟢 | `rbacDomainGlossary.UiLocale` vs `@/i18n` `UiLocale` | **Закрыто A9b:** `UiLocale` только из `@/i18n`; глоссарий — re-export хелперов |

---

## Префикс QUEUE (встроен в каждый блок ниже)

Каждый промпт самодостаточен: в Queue вставляется **весь** fenced-блок батча, без отдельного копирования этого раздела. Текст префикса здесь — канон, чтобы не разъехался.

Обязательное чтение **до первой правки кода** (порядок фиксирован):

1. Этот файл: шапка + §0 + §1 + §2 + **только секция текущего батча** (не весь файл заново в работу).  
2. Файлы из списка батча — **Read с диска**, не из памяти прошлого чата.  
3. С A1: `frontend/src/i18n/index.ts`, `useUiLocale.ts`, `testUtils.tsx` — каркас A0 должен уже существовать. Нет провайдера в `main.tsx` → стоп, это не тот батч.  
4. Не изобретать второй i18n, не оборачивать только `AdminLayout`, не ставить `i18next-browser-languagedetector`.  
5. Не переводить `docs/` (кроме отчёта A12 в этом файле), patient `src/app`, body маркетинга, сырой API `detail`.  
6. Ключи сразу в **en и ru**. Новый ns — регистрация в `index.ts` + `i18next.d.ts`. Тесты: **`await renderWithI18n`**, chrome EN или `t()`. Law 40: нет `git commit` / `git push`.

---

## Очередь (карта A → B)

```
A0   каркас: provider в main, dayjs clock, testUtils, CompactMonthPicker, QueryErrorAlert default title
A1   login + SignInShell switcher + AdminLayout nav/spotlight + strip + RBAC hook + smoke-routes login
A2   расписание + записи + waitlist + recall + staff calendar + booking errors/status
A3   пациенты, врачи, услуги, клиники, персонал, кабинет
A4   задачи / kanban
A5   чаты + каналы + adminChatChrome aria-label + e2e omni chrome
A6   CRM / sales / marketing / retention / leads
A7   finance / commerce / loyalty / prepayment / payments / discounts
A8   dashboard (лента) + reports + AI reports + e2e dashboard chrome
A9   settings, subscription page, embed, RAG, export, AI, forms,
     agreements, notifications, styling, stickers, knowledge, integrations
A9b  RBAC copy ts → rbac.json (поведение locale уже с A1)
A10  ErrorBoundary fallback + оставшиеся common.errors codes + entitlementDisplay
A11  хвосты e2e (не повторять A1/A5/A8)
A12  гейт grep chrome + отчёт
```

---

## A0 — Каркас (блокер всех остальных)

**Статус:** принят в коде + A0-audit 2026-08-17. Не перезапускать QUEUE A0.

**Цель:** i18n живёт, default `en`, locale переживает F5, dayjs не залипает на RU, тесты могут рендерить хук.

**Файлы (факт после audit):**

- `frontend/package.json` + lock: `i18next` ^26 / `react-i18next` ^17 (MIT)
- `frontend/src/i18n/index.ts` — init, `fallbackLng: "en"`, `I18N_NAMESPACES`, clone resources
- `frontend/src/i18n/useUiLocale.ts` — persist, `storage` listener, `document.documentElement.lang` на `/admin*` + restore public `ru` вне admin, подписка на history
- `frontend/src/i18n/UiLocaleSwitch.tsx` — единственный SegmentedControl EN/RU (§2); A1 только монтирует
- `frontend/src/i18n/testUtils.tsx` — `await renderWithI18n`
- `frontend/src/i18n/locales/en/{common,nav,auth}.json` и `ru/`
- `frontend/src/main.tsx` — `I18nextProvider` + `UiLocaleSync`
- `frontend/src/shared/ui/CompactMonthPicker.tsx` — нет module-scope `dayjs.locale`
- `frontend/src/admin/pages/AdminStaffCalendarPage.tsx` — module-scope `dayjs.locale("ru")` **снят в A0-audit** (eager import из `App.tsx`)
- `frontend/src/shared/ui/QueryListStates.tsx` — default title `t("errors.loadFailed")`
- тесты: `src/i18n/__tests__/*`

**A0-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| `AdminStaffCalendarPage` `dayjs.locale("ru")` на модуле + eager import в `App.tsx` | Снят locale с модуля. Иначе clock A0 мёртв на любом маршруте |
| `document.lang` только при смене locale, не при SPA-переходе | `pushState`/`replaceState`/`popstate`; вне `/admin*` вернуть public `ru` |
| Новый ns в JSON без `index.ts` (A2 «не пересобирай init») | Контракт: регистрировать ns; A2 QUEUE исправлен |
| `renderWithI18n` async, очередь писала sync | Контракт: `await renderWithI18n` |
| Два SegmentedControl в A1 | `UiLocaleSwitch` готов, A1 только placement |
| `addResource` мутировал JSON-модуль | `structuredClone` при init |

**Приёмка:** `cd frontend && npm test -- src/i18n --run` зелёный.

### QUEUE A0 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A0. Не A1 и не экраны.

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — шапка (старт = A0), §0 контракт, §1 архитектура, §2 дизайн, секция «A0 — Каркас».
2) С диска: frontend/src/main.tsx, frontend/package.json, frontend/src/App.tsx (убедись: /admin/login = ClinicSignInPage ВНЕ AdminLayout — поэтому провайдер только в main.tsx).
3) frontend/src/shared/ui/CompactMonthPicker.tsx (module-scope dayjs.locale("ru")), frontend/src/shared/ui/QueryListStates.tsx (default title RU).
Не читай и не правь admin pages в этом батче.

СДЕЛАЙ: i18next + react-i18next (MIT), без i18next-browser-languagedetector.
I18nextProvider в frontend/src/main.tsx. Default en, localStorage ui.locale, storage event.
useUiLocale + frontend/src/i18n/testUtils.tsx renderWithI18n. useSuspense: false.
Снять module-scope dayjs.locale("ru") в CompactMonthPicker; dayjs.locale только из провайдера.
QueryErrorAlert default title через t("common.errors.loadFailed"); formatQueryError НЕ менять.
Словари-каркас en+ru: common, nav, auth (Save/Cancel/Loading/language/errors.loadFailed|generic, calendar weekdays).
Тест: нет ui.locale → en. npm test -- src/i18n.

НЕ: экраны, index.html, docs/, patient pages, backend, git commit/push (Law 40).
В конце: список файлов и как проверить.
```

---

## A1 — Вход и шелл

**Статус:** принят в коде + A1-audit 2026-08-17. Не перезапускать QUEUE A1.

**Цель:** холодный `/admin/login` на EN; переключатель на логине и в header; nav из `nav.json`.

**Файлы:**

- `frontend/src/auth/ClinicSignInPage.tsx`
- `frontend/src/auth/panels/ClinicStaffSignInPanel.tsx`
- `frontend/src/auth/SignInShell.tsx` — split chrome + **`UiLocaleSwitch`** (§2). Patient variant без переключателя (вне скоупа PWA).
- `frontend/src/admin/layouts/AdminLayout.tsx` — `navGroups` через `nav.*`; **`UiLocaleSwitch`** в header после `ClinicSelector`
- `frontend/src/i18n/UiLocaleSwitch.tsx` — не форкать; только разместить (login форма + header)
- `frontend/src/admin/components/ClinicSelector.tsx`
- `frontend/src/admin/components/AdminOwnerSubscriptionStrip.tsx` (шелл, не страница подписки)
- `frontend/src/shared/aiFeatures.ts` — человекочитаемые tooltip/label в `common` или `nav` (не оставлять RU tooltip у Spotlight)
- `frontend/src/admin/pages/AdminRightsPoliciesPage.tsx` — `useUiLocale()` вместо `useState("ru")`; **удалить** локальный language SegmentedControl (переключатель только в header)
- `frontend/e2e/smoke-routes.spec.ts` — **только** тест `clinic sign-in at /admin/login` на EN heading. Остальные кейсы маркетинга не трогать.
- словари `nav.json`, `auth.json`, `common.json`

`AdminAuthGuard.tsx` — UI-строк нет, не раздувать. `AdminLoginPage.tsx` — redirect, строк нет.

**Приёмка:** `/admin/login` EN; переключение RU переживает F5 и видно в nav после входа; страница прав без второго переключателя; smoke-routes login зелёный.

**A1-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| `ClinicStaffSignInPanel` общий с `/login`, e2e всё ещё ждал RU heading | `smoke-routes` кейс public `/login`: heading панели EN. Body `PublicLoginPage` («Вход», пациентский блок) не трогали |
| Ошибка пароля как уже переведённая строка в `useState` | Хранить `{ kind }`, `t()` на рендере; HTML `minLength` снят — иначе native tooltip браузера, не `ui.locale` |
| `useAiFeatures` / Spotlight `useMemo` / `useEffectiveAiFeatureGate` не зависели от `i18n.language` | Подписка `useTranslation` + `i18n.language` в deps; `common.ai.toolsUnavailable` вместо RU литерала в гейте |
| Переключатель только в развёрнутом сайдбаре | Не баг геометрии: collapsed 80px < EN\|RU sm. Зафиксировано как R13, не второй контрол |
| Доки всё ещё «следующий QUEUE A1» | Маршрут, R3/R5/R7, OSS/README — A1 принят, следующий A2 |

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n src/auth/__tests__/ClinicSignInPage.test.tsx src/admin/components/__tests__/ClinicSelector.test.tsx src/admin/components/__tests__/AdminOwnerSubscriptionStrip.test.tsx src/shared/__tests__/aiFeatures.i18n.test.ts`.

### QUEUE A1 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A1. Если нет frontend/src/i18n/ и I18nextProvider в main.tsx — СТОП, сначала A0.

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §0, §1 п.3 (SignInShell побочный эффект), §2 переключатель, секция «A1 — Вход и шелл».
2) Каркас A0 с диска: frontend/src/i18n/index.ts, useUiLocale.ts, testUtils.tsx, UiLocaleSwitch.tsx, main.tsx, locales/en|ru/{common,nav,auth}.json.
3) С диска файлы батча: ClinicSignInPage.tsx, ClinicStaffSignInPanel.tsx, SignInShell.tsx, AdminLayout.tsx, ClinicSelector.tsx, AdminOwnerSubscriptionStrip.tsx, aiFeatures.ts, AdminRightsPoliciesPage.tsx (только locale switcher), frontend/e2e/smoke-routes.spec.ts.

СДЕЛАЙ: ключи en+ru для login + split chrome SignInShell + nav/spotlight/header switcher + ClinicSelector + subscription strip + aiFeatures tooltips/labels.
Переключатель: **импортируй `UiLocaleSwitch`** из `frontend/src/i18n/UiLocaleSwitch.tsx` (колонка формы логина + header после ClinicSelector). Не глобус. Не в тёмной колонке SignInShell. Не копируй второй SegmentedControl.
AdminRightsPoliciesPage: useUiLocale, удали локальный language SegmentedControl. Copy ts НЕ переноси в JSON (A9b).
smoke-routes: только кейс /admin/login на EN heading. Лендинг/signup в том файле не трогать.
Тесты: **await renderWithI18n**, chrome EN или t().

НЕ: PatientSignInPage body, PlatformFounderLoginPage body, другие admin pages, docs/, git commit/push.
Побочный эффект EN-оболочки SignInShell на /platform/login и /login — принят, формы внутри не переводить.
```

---

## A2 — Расписание и записи

**Статус:** принят в коде + A2-audit 2026-08-17. Не перезапускать QUEUE A2.

**Цель:** операционный контур записи на EN **включая** статусы и booking `code`.

**Файлы:**

- `frontend/src/admin/pages/SchedulePage.tsx`
- `frontend/src/admin/components/ScheduleCalendarGrid.tsx` + тест (`Free` / ключ, не «Свободен»)
- `frontend/src/admin/components/ScheduleCalendar.tsx`
- `frontend/src/admin/components/WaitlistPanel.tsx`
- `frontend/src/admin/pages/AdminBookingsPage.tsx`
- `frontend/src/admin/components/entity/BookingEntityDrawer.tsx`
- `frontend/src/admin/pages/AdminWaitlistPage.tsx`
- `frontend/src/admin/pages/AdminRecallPage.tsx`
- `frontend/src/admin/pages/AdminDoctorSchedulePage.tsx`
- `frontend/src/admin/pages/AdminStaffCalendarPage.tsx` — chrome на EN; **не** возвращать `dayjs.locale("ru")` на модуль (снято в A0-audit)
- `frontend/src/shared/bookingStatusMeta.ts` — лейблы через `bookings.status.*`, не единственный `BOOKING_STATUS_LABEL_RU`
- `frontend/src/shared/errors.ts` — **только** ветка `getBookingErrorMessage` / booking codes → ключи; не ломать patient, если функция ещё дергается из app: вернуть ключ **или** принимать `t`. Предпочтение: `bookingErrorI18nKey(code)` + `t()` на admin caller.
- ns: `schedule.json`, `bookings.json`

**Регрессия P0:** пустая ячейка открывает create; ошибки формы не silent; кнопка create disabled+loading.

`ClinicSelector` и clinic-строки `AdminLayout` уже на ключах A1 — не переводить заново и не сливать два picker (R15). `toLocaleString` на этих экранах — с `useUiLocale()` (`en-US`\|`ru-RU`), риск R8.

**A2-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| Сетка: `awaiting_payment` падал в fallback `occupied` («Busy» / «Занято»), хотя ключ `bookings.status.awaiting_payment` уже был | Явная ветка `statusBadge`; vitest на EN badge |
| Waitlist таблица и панель: сырой `waiting`/`notified`; на RU пользователь видел английский enum | `waitlistStatusLabel` → `waitlistPage.*` |
| Recall таблица: сырой `draft`/`running` и `days_after_visit` (форма уже была на ключах) | `recall.campaignDraft\|Running\|Completed` + `daysAfterVisit` |
| WaitlistPanel / legacy calendar: UUID пациента в chrome (Law 8) | `looksLikeUuid` → `grid.unknownName` |
| `bookingErrorI18nKey(!code)` → generic `createFailed`, даже если на ошибке есть `EMPTY_DB`/`detail` без code (`'code' in ApiErrorWithCode` = true при `code === undefined`) | Missing/empty code → `null` → `formatQueryError`; `apiErrorCode` требует непустую строку |
| Empty-DB hint на bookings только по подстроке «клиник» | `isEmptyClinicDatabaseError` (RU copy + `no clinic(s)` + будущий `empty_db_no_clinic`) |
| Cancel/run/delete `isPending` крутил **все** кнопки ряда | `loading`/`disabled` только при `variables === id` |
| Доки всё ещё «следующий QUEUE A2» | Маршрут, R6, OSS/README — A2 принят, следующий A3 |

**Вне скоупа A2 (следующий шаг зафиксирован):**

- Тело `QueryErrorAlert` / `formatQueryError` оптом — **A10 / R10** (сырой API `detail` без `code` остаётся как есть).
- Native HTML `required` на дате waitlist — **R14**, не form-lib в A3–A12.
- `EMPTY_DB_NO_CLINIC` на бэке без `code` — не эта волна UI; hint на bookings работает по copy. Код на API — отдельное решение @ARCH, не A3.
- `BOOKING_STATUS_LABEL_RU` — мёртвый static map (patient SPA не импортирует). Не удалять в A3; не использовать в admin. **Удалено в A12-audit** (гейта A12 не требовал; после волны уборки не было).
- Строки «Расписание»/«Записи» на **других** экранах (reports, marketing, doctor drawer) — батч того экрана.
- Комментарии кода на RU — **R11 / A12**, не chrome.
- ₽ на prepayment — **L3**, регион клиники.
- Patient `BookingWizardPage` / `getBookingErrorMessage` — вне волны.

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n src/admin/components/__tests__/ScheduleCalendarGrid.test.tsx src/shared/__tests__/bookingErrors.i18n.test.ts`.

### QUEUE A2 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A2. Нет i18n в main.tsx или нет switcher на логине — СТОП (A0/A1).

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §0 (API code vs detail, dayjs), секция «A2», риск R6.
2) Каркас: useUiLocale, testUtils, locales en/ru. **Новые ns `schedule`+`bookings`: JSON + `I18N_NAMESPACES`/`resources` в index.ts + `i18next.d.ts`.** Не менять fallbackLng/detector/useSuspense/default en.
3) С диска: SchedulePage.tsx, ScheduleCalendarGrid.tsx + __tests__, ScheduleCalendar.tsx, WaitlistPanel.tsx, AdminBookingsPage.tsx, BookingEntityDrawer.tsx, AdminWaitlistPage.tsx, AdminRecallPage.tsx, AdminDoctorSchedulePage.tsx, AdminStaffCalendarPage.tsx, bookingStatusMeta.ts, errors.ts (только getBookingErrorMessage / booking codes).

СДЕЛАЙ: ключи en+ru, ns schedule.json + bookings.json **и регистрация ns в index.ts**.
P0 не ломать: пустая ячейка → create; ошибки формы не silent; submit disabled+loading.
bookingStatusMeta и booking-code → ключи в A2, не откладывать на A10.
AdminStaffCalendarPage: перевести chrome; **не** возвращать module-scope `dayjs.locale`.
Тест сетки: EN (не «Свободен»), await renderWithI18n.

НЕ: другие страницы, docs/, PWA, marketing, formatQueryError оптом, git commit/push.
```

---

## A3 — Справочники клиники

**Статус:** принят в коде + A3-audit 2026-08-17. Не перезапускать QUEUE A3.

**Файлы (полные пути):**

- `frontend/src/admin/pages/AdminPatientsPage.tsx`
- `frontend/src/admin/components/entity/PatientEntityDrawer.tsx`
- `frontend/src/admin/pages/AdminDoctorsPage.tsx`
- `frontend/src/admin/components/entity/DoctorEntityDrawer.tsx`
- `frontend/src/admin/pages/AdminServicesPage.tsx`
- `frontend/src/admin/components/entity/ServiceEntityDrawer.tsx`
- `frontend/src/admin/pages/AdminClinicsPage.tsx`
- `frontend/src/admin/pages/AdminAdministratorsPage.tsx`
- `frontend/src/admin/pages/AdminStaffCabinetPage.tsx`
- ns: **`directory.json` только** (не плодить patients.json)

ФИО/телефоны пациентов — данные, не ключи. `display_role` / lexicon клиники / `r.name` из RBAC-каталога — данные API.

**A3-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| Форма клиники: `label="E‑mail"` мимо `t("email")` — на RU таблица «Email», поле «E‑mail» | `t("email")` |
| `handleSubmit` клиники: пустое имя = тишина; ошибка API без catch | `clinics.nameRequired` / `saveFailed` + Alert; сырой `message` — R10 |
| Удаление врача/услуги с списка без confirm (пациент уже имел) | Modal `doctors.delete*` / `services.delete*` |
| Overflow Delete/Print/Copy в дроверах без `onClick` — кнопка «Удалить» ничего не делала | Print/Copy сняты (заглушки). Delete → `onRequestDelete` + тот же confirm |
| `deleteCat.isPending` крутил **все** × категорий | `variables === c.id`; confirm `staff.deleteCategory*` |
| Категории: сырые `admin, doctor` вместо имён из каталога | `roleCodesDisplay` → `r.name` (данные API; локализация имён — A9b) |
| Услуги: исполнитель без `full_name` в активном списке → «—» | `unknownName` (не UUID, не пустая ячейка) |
| `serviceCategoryLabel(null)` мог упасть на `.toLowerCase()` | `string \| null \| undefined` → `""` |
| Шапка визитов NPS литералом | `patientDrawer.nps` |

**Вне скоупа A3 (следующий шаг зафиксирован):**

- Тело `QueryErrorAlert` / `formatQueryError` оптом, в т.ч. fallback «Произошла ошибка…» — **A10 / R10**.
- Native `required` / `type="email"` / `type="date"` — **R14**.
- ₽ и даты `DD.MM.YYYY` в дроверах — регион клиники (L3), как Mon-first; не en-US.
- Имена ролей RBAC (`r.name`) на ключи — **A9b**.
- Онлайн-вкладка услуги не сохраняется (copy «when the API is available») — не i18n; бэк/волна услуг, не A4.
- `package_name` нет на `CustomerSubscription` в family-select — лейбл «Pass (remaining)» остаётся; рост DTO — A7 loyalty, не A4.
- Cabinet/staff: сырой `error.message` — R10.
- Комментарии кода на RU — **R11 / A12**.
- E2E справочников нет в `frontend/e2e/` (нечего чинить в A11 по A3).

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n src/admin/pages/__tests__/AdminPatientsPage.test.tsx src/admin/components/entity/__tests__/directoryI18n.test.ts`.

### QUEUE A3 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A3. Нет i18n в main.tsx или нет ns `schedule`/`bookings` — СТОП (A0/A1/A2).

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §0, секция «A3», инвентарь A3.
2) frontend/src/i18n/testUtils.tsx и существующие ns — не плодить patients.json.
3) С диска: AdminPatientsPage.tsx, PatientEntityDrawer.tsx, AdminDoctorsPage.tsx, DoctorEntityDrawer.tsx, AdminServicesPage.tsx, ServiceEntityDrawer.tsx, AdminClinicsPage.tsx, AdminAdministratorsPage.tsx, AdminStaffCabinetPage.tsx.

СДЕЛАЙ: ключи en+ru, один ns directory.json **и регистрация в index.ts + i18next.d.ts**. ФИО/телефоны — данные, не ключи.
Тесты: await renderWithI18n, селекторы EN.

НЕ: docs/, PWA, marketing, другие admin pages, git commit/push.
```

---

## A4 — Задачи / Kanban

**Статус:** принят в коде + A4-audit 2026-08-17. Не перезапускать QUEUE A4.

**Файлы (полные пути):**

- `frontend/src/admin/pages/AdminTasksPage.tsx`
- `frontend/src/admin/pages/AdminTaskDetailsPage.tsx`
- `frontend/src/admin/components/TaskDetailsView.tsx`
- `frontend/src/admin/pages/__tests__/AdminTasksPage.test.tsx`
- ns: **`tasks.json` только**
- helper: `frontend/src/shared/taskStatusI18n.ts` (подписи статусов/приоритетов; коды не менять)
- тонкая обёртка `AdminLeadsLogPage.tsx` — страница числится в A6, но рендерит `AdminTasksPage mode="leads-log"`. Проп `titleOverride` **снят** (A4-audit): A6 не может вернуть литерал «Лиды (лог)» через override.

Коды статусов (`open` / `in_progress` / …) и DnD — инварианты. Имена потоков/тегов/досок с API — данные.

**A4-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| `AdminLeadsLogPage` всегда передавал `titleOverride="Лиды (лог)"` — маршрут лидов оставался RU при EN default | override снят; заголовок = `t("leadsTitle")` |
| `onClaim` / `onTaskChat` на карточке были `_onClaim` / `_onTaskChat` — модалки чата и claim с API мертвы, chrome чата переведён вхолостую | пункты меню `card.claim` / `card.taskChat` |
| Колонки Kanban не получали `canMoveStream` — «Move to stream» только в очереди подтверждений | те же props, что у approval queue |
| Alt+Arrow обходил WIP/checklist/blocked (проверка была только на drag) | `handleKeyboardMoveGuarded` → `moveTask` / `canMoveToStatus` |
| Create / status-кнопки деталей / backend reject DnD — silent | Alert + `errors.createFailed` / `view.statusFailed` / `errors.transitionDenied`; Complete уважает blocked+checklist |
| `updateStatusMutation.isPending` крутил все три кнопки статуса | `loading` только при `variables.status === …` |
| Симуляция routing: склейка `Target stream: ${label}` | `routing.targetHit` |
| `closed_at` null → Invalid Date в chrome | рендер только если дата есть |
| Staff без имени: `id.slice(0, 8)` (Law 8) | уже `unknownStaff` в A4; не возвращать UUID |
| EmptyState «Create task» был `onClick: () => {}` | `onCreateTask` → открыть форму |
| `mutate` в `TasksKanbanPage` был сужен до 1 аргумента — `onError` не компилировался | типы `mutate(vars, opts?)` |
| В очереди подтверждений `.map((t) =>` затенял `t()` — claim onError падал бы в рантайме | параметр `queueTask` |
| Drop на слот **другой** колонки слал reorder+status сразу (гонка, 409) | другой статус → только `moveTask`; reorder только внутри колонки |
| `handleKeyboardColumnMove` в родителе обходил WIP/blocked и оставался миной | удалён; живой путь — `handleKeyboardMoveGuarded` |
| `titleOverride` оставлял дыру для A6 вернуть RU заголовок | проп снят; leads = `t("leadsTitle")` |
| Stream move / comment / routing save — silent или ошибка за модалкой | `errors.saveFailed` в видимом Alert |
| Tooltip карточки AI был литерал `"AI"` | `card.ai` |

**A4-repass 2026-08-21 (Kanban leftover review):**

| Дыра | Фикс |
|------|------|
| `AdminTaskDetailsPage` chrome литералы «Задача» / «Назад к Kanban» при ключах `detail.task` / `page.backToKanban` | страница на `useTranslation("tasks")` |
| `{/* legacy detail modal removed */}` ~600 строк всё ещё в файле (A12 заявлял удаление) | блок вырезан; живой путь только `TaskDetailsView` |
| Дубли ключей `view.assigneesInline` (JSON last-wins) + alias `assigneeDelegate` | один набор `view.*`; `TaskDetailsView` на канонические ключи |
| Колонки Kanban: `taskStatusLabel` без `i18n.language` в deps — подписи не обновлялись при смене языка | `statusColumns` зависит от `i18n.language` |
| `errors.createFailed` / `errors.claimFailed` в словаре, create/claim без `onError` в живом UI | Alert через `setDragError` |
| Create stream placeholder «Required» | `view.pickStream` |

**Вне скоупа A4 (следующий шаг зафиксирован):**

- Тело `QueryErrorAlert` / `formatQueryError` оптом — **A10 / R10** (сырой API `detail` без `code` остаётся как есть).
- Даты `DD.MM.YYYY` / `DD.MM HH:mm` на карточках — регион клиники (L3), как Mon-first; не en-US.
- Аудит перемещений (`auditTrail`) — `useState([])` никогда не пишется; панель пустая. Не i18n; отдельное решение @ARCH, не A5.
- Календарные слоты / «Add to calendar» / invite жили в закомментированном legacy-модале; живой `TaskDetailsView` их не показывает. Восстановление UI — не i18n-батч.
- Комментарии кода на RU — **R11 / A12**.
- `AdminLeadsLogPage` как страница A6: остальной crm-chrome (если появится вокруг обёртки) — **A6**. Проп `titleOverride` снят — не возвращать.
- E2E задач нет в `frontend/e2e/` (нечего чинить в A11 по A4).
- Поле `channel_type` в тесте routing остаётся техническим placeholder API (`TELEGRAM_BOT / …`) — данные, не chrome.
- Cross-column drop на конкретный слот больше не вставляет в позицию (только смена статуса, rank на сервере). Позиционирование в чужой колонке одним жестом — отдельный контракт API (status, затем reorder), не A5.

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n src/admin/pages/__tests__/AdminTasksPage.test.tsx src/admin/pages/__tests__/AdminTaskDetailsPage.test.tsx`.

### QUEUE A4 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A4.

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §0, секция «A4».
2) testUtils + i18n init (не пересобирать).
3) С диска: frontend/src/admin/pages/AdminTasksPage.tsx, AdminTaskDetailsPage.tsx, frontend/src/admin/components/TaskDetailsView.tsx, pages/__tests__/AdminTasksPage.test.tsx.

СДЕЛАЙ: ns tasks.json en+ru. getByText «Все потоки»/«Продажи» → EN или t().
Не меняй DnD и бизнес-статусы.

НЕ: другие страницы, git commit/push.
```

---

## A5 — Чаты и каналы

**Статус:** принят в коде + A5-audit 2026-08-17. Не перезапускать QUEUE A5.

**Файлы:**

- `AdminOmniChatPage.tsx`, `AdminOmniChannelsPage.tsx`, `AdminOmniVaultPage.tsx`, `AdminOmniAiSettingsPage.tsx`
- `AdminStaffChatPage.tsx`, `AdminChatPage.tsx`, `AdminChannelsPage.tsx`
- `frontend/src/shared/adminChatChrome.ts` — `aria-label` (это chrome, не «невидимый стиль»)
- `frontend/e2e/admin-omni-chat.spec.ts` — кнопки chrome EN; фикстуры «Иван Иванов» / «Здравствуйте» оставить

ns: `chat.json`

`staffFeedChrome.ts` — токены без UI-строк, не трогать.

**A5-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| `VoiceNoteRecorderButton` aria EN, ошибки «Микрофон недоступен»/«Ошибка записи» всё ещё RU (tooltip + `onError` в Omni/Staff) | опциональные `unavailableMessage` / `recordFailedMessage` / `micDeniedMessage`; админ-страницы передают `errors.mic*` |
| Автоclaim при открытии: `onError` пустой — сеть/409 невидимы; кнопка Claim при ошибке писала `takeOverFailed` | `errors.claimFailed`; Claim и auto-claim на этом ключе |
| E2E POST `/claim` уходил в `fallback` (висящий pending / гонка с кнопкой Claim) | мок claim 200 + `claimedChatIds`; GET detail согласован; e2e: Claim **или** Resolve ticket |
| Tooltip иконок канала показывал сырой `TELEGRAM_BOT` | `omniChannelTypeLabel` |
| Аналитика `admin_name ?? admin_id` — UUID в UI (Law 8) | `unknownName` |
| Staff: `id.slice(0, 8)` в селекте коллег и finder (Law 8) | `unknownName` |
| `onCreateGroup`: `const t = groupTitle.trim()` затенял `t()` — мина как в A4 queue | параметр `title` |
| Empty staff без комнат: copy «не удалось загрузить» при успешном `[]`, нет CTA (Law 9) | `emptyRoomsHint` = начать чат; `action` → New group (модалка снаружи ternary) |
| Omni channels EmptyState без CTA при «Add» только в шапке | `action` → `handleOpenCreate` |
| Presence `const t = setInterval` затенял `t()` в том же компоненте | `heartbeatId` |
| `PersonNameLink` / `displayPersonName` хардкод «Имя неизвестно» — клик по автору в staff-треде (и A2/A4) = RU при EN default | `common.unknownName` + `useTranslation` в линке |
| `StaffCardModal` (открывается из A5) целиком на RU литералах — A3 файл не включал shared modal | `directory.staff.card*` |
| AI settings: колонка типа = сырой `TELEGRAM_BOT`; save без ошибки; нет каналов = текст без CTA | `omniChannelTypeLabel`; Alert `errors.saveFailed`; EmptyState → `/admin/omni-channels` |
| Untitled `QueryErrorAlert` на AI settings / staff rooms/messages — title default EN с A0, но смысл общий | `errors.loadAiSettingsFailed` / `errors.loadDialogsFailed` |
| Empty staff: CTA только New group, hint обещал коллегу, finder был недоступен | вторая кнопка `staff.write` → finder |
| Create/update omni-канала, notify save, AI mode, patient send/claim/delete, staff post/DM/group — silent | Alert / `attachError` / `actionError` |
| Notify: `isPending` крутил Save на всех трёх карточках | `variables?.channel === …` |
| `errors.noConversation` в ru оставался английским | «нет диалога» |

**Вне скоупа A5 (следующий шаг зафиксирован):**

- Тело `QueryErrorAlert` / `formatQueryError` оптом — **A10 / R10** (сырой API `detail` без `code` остаётся как есть). Title на экранах A5 уже передан.
- Даты `DD.MM.YYYY HH:mm` в staff-треде и StaffCardModal — регион клиники (**L3**), не en-US.
- Комментарии кода на RU (`adminChatChrome`, vault TODO) — **R11 / A12**.
- Дефолты `EmojiMartPopoverPicker` (`ariaLabel="Эмодзи"`) и `VoiceNoteRecorderButton` без пропсов — **PWA**; админ A5 передаёт ключи. Не менять дефолт в A6.
- `src/app/ChatPage` — вне волны (контракт A5).
- `useAdminOmniVault.ts` RU-лейблы пресетов — fallback API; UI берёт `vaultPresetLabel`. Не править хук в A6.
- MultiSelect фильтр каналов: **value/label = код** (`VK_BOT`) — e2e кликает код; перевод типа — в таблице каналов, не в фильтре. Не «чинить» на `channelType.*`.
- `aria-label="needs-attention"` — технический селектор e2e, не chrome.
- Vault export/backup кнопки без API (существующие TODO) — не i18n; контракт API @ARCH, не A6.
- Vault EmptyState без CTA — нет жеста «загрузить медиа» в API; не выдумывать.
- Удаление сообщения пациента без Undo (I4) — не i18n; отдельный UX-батч, не A6.
- `StaffCardModal` `error.message` — R10, как cabinet.
- Presence HEARTBEAT/CLOSE без видимой ошибки — lease/TTL, не i18n; не делать toast на каждый pulse.

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n`.

### QUEUE A5 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A5.

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §0, секция «A5» (aria-label = chrome).
2) testUtils. Не трогай staffFeedChrome.ts (нет UI-строк).
3) С диска: AdminOmniChatPage, AdminOmniChannelsPage, AdminOmniVaultPage, AdminOmniAiSettingsPage, AdminStaffChatPage, AdminChatPage, AdminChannelsPage, frontend/src/shared/adminChatChrome.ts, frontend/e2e/admin-omni-chat.spec.ts.

СДЕЛАЙ: ns chat.json en+ru. Сообщения чата не переводить.
E2E: кнопки chrome EN; фикстуры «Иван Иванов»/«Здравствуйте» оставить. Это владение A5, не A11.

НЕ: src/app ChatPage, git commit/push.
```

---

## A6 — CRM / маркетинг

**Статус:** принят в коде + A6-audit 2026-08-17. Не перезапускать QUEUE A6.

**Файлы:** `AdminSalesPipelinePage.tsx` (+ тест), `AdminMarketingPage.tsx`, `AdminRetentionPage.tsx`, `AdminLeadsLogPage.tsx`, `AdminClientReferencePage.tsx`

`AdminLeadsLogPage` — обёртка над `AdminTasksPage mode="leads-log"`. Заголовок уже из `tasks.leadsTitle`. Проп `titleOverride` снят — **не** добавлять снова с литералом «Лиды (лог)».

`Intl.NumberFormat` / `toLocaleDateString` — locale из `useUiLocale`, не хардкод `ru-RU`.

ns: `crm.json`

**A6-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| Default-воронка не выбиралась: `selectedPipelineId` оставался `null`, `useCrmStages` disabled, UI врал «No stages configured». Тест мокал стадии всегда | auto-select `is_default` / первая воронка; мок стадий только при `pipe-1` |
| Deep-link `?lead_id=` ставил pipeline/stage только если они ещё пустые — после auto-select лид из другой воронки не открывался | эффект всегда берёт pipeline/stage с лида |
| Retention: `isError` сегментов/ROI выглядел как EmptyState «нет сегментов/кампаний» + CTA | `QueryErrorAlert`; EmptyState только на успешный `[]` |
| Retention без клиники = те же «нет сегментов» | EmptyState `pickClinic` |
| Атрибуция: `toISOString().slice(0, 10)` сдвигала 1-е число месяца в UTC (MSK → предыдущий день) | локальный `YYYY-MM-DD` |
| Офферы: `onSuccess` прошлого сегмента мог залить новый drawer | ref `offersSegmentRef` + сверка `segmentId` |
| Delete post/story: нет `onError` — модалка молчит при 403/500 | Alert `deleteFailed` / сырой `message` (R10) |
| Посты: `required` на input, submit через `onClick` кнопки — пустые title/body уходили в API | клиентская проверка `fieldsRequired` |
| Clipboard предоплаты без `catch` + таймер без cleanup | `copyFailed` + `copyTimerRef` |
| Pipelines/stages/lead details / колонка Kanban / drill: ошибка = пустота | `QueryErrorAlert` / `loadColumnsFailed` |
| AI apply/ignore/create/summary: silent fail | `aiActionFailed` Alert |
| Карточки: сырые `5000` при NumberFormat в шапке колонки; даты атрибуции без locale на суммах | `Intl.NumberFormat` из `useUiLocale` |
| Офферы все с «Unknown name» при DTO без ФИО (Law 8) | строка = текст оффера; имя пациента — рост DTO |
| Канал шаблона `sms` сырьём в Select | `crmRecallChannelLabel` |
| Stories: truncate без tooltip; edit не сбрасывал saveError | Tooltip; `setSaveError(null)` |
| Save note кликабелен на пустом тексте | `disabled={!noteText.trim()}` |

**Вне скоупа A6 (следующий шаг зафиксирован):**

- Тело `QueryErrorAlert` / `formatQueryError` оптом, сырой API `detail` без `code` — **A10 / R10**.
- Символ ₽ на карточках/атрибуции — регион клиники (**L3**), не `$`.
- Комментарии кода на RU — **R11 / A12**.
- `titleOverride` на leads-log — пропа нет; **не возвращать**.
- E2E этих экранов нет в `frontend/e2e/` (нечего чинить в A11 по A6).
- Native `required` / `type="date"` в маркетинге — **R14** (браузерный chrome даты). Клиентская проверка постов закрыта в A6-audit.
- Имена воронок/стадий/лидов/офферов/UTM — данные API, не ключи.
- `RetentionOfferItem` без ФИО пациента — рост DTO бэка (`full_name` в generate-offers). Не выдумывать имя и не показывать UUID.
- Нет экрана настроек воронки в `routePaths` — EmptyState стадий без CTA (не выдумывать маршрут).
- `AdminRecallPage` placeholder `sms / telegram / email` — хвост A2, не трогать в A7.
- Карточки сегментов разной высоты при длинном description — **Law 26 / @QA_VISUAL**, не i18n.

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n src/admin/pages/__tests__/AdminSalesPipelinePage.test.tsx`.

### QUEUE A6 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A6.

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §0 (даты/числа из useUiLocale), секция «A6».
2) testUtils.
3) С диска: AdminSalesPipelinePage.tsx + тест, AdminMarketingPage.tsx, AdminRetentionPage.tsx, AdminLeadsLogPage.tsx, AdminClientReferencePage.tsx.

СДЕЛАЙ: ns crm.json en+ru. toLocaleString/NumberFormat — locale из useUiLocale, не хардкод ru-RU.
AdminLeadsLogPage: не возвращать RU titleOverride (пропа больше нет — не добавлять).
Тесты pipeline — EN, renderWithI18n.

НЕ: другие страницы, git commit/push.
```

---

## A7 — Деньги клиники

**Статус:** принят в коде + A7-audit 2026-08-17. Не перезапускать QUEUE A7.

**Файлы:** `AdminFinancePage.tsx`, `AdminCommercePage.tsx`, `AdminLoyaltyPage.tsx`, `AdminPrepaymentPage.tsx`, `AdminPaymentGatewayPage.tsx`, `AdminDiscountsPage.tsx`

ns: `money.json`

₽ и YooKassa не «переводить». Подписи полей — ключи. `toLocaleString("ru-RU")` → locale из хука.

**Что закрыто в A7:**

| Экран | Chrome |
|-------|--------|
| Finance | кассы/транзакции/ЗП/склад; баланс `toLocaleString(useUiLocale)`; типы касс `moneyCashboxTypeLabel`; бронь без UUID; врач без UUID; EmptyState касс без фейкового CTA |
| Commerce | витрина PWA / CSV / сеть / остатки / движения / номенклатура; даты `toLocaleString(dateLocale)`; имена точек без UUID |
| Loyalty | пакеты/абонементы/кошельки/кампании; колонки UUID сняты; lookup пациента по UUID — поле поиска, не chrome |
| Prepayment | политики + confirm delete; таблица показывает лейблы scope/mode/amount, не сырые токены; toggle с catch |
| Gateway | YooKassa/Tinkoff/Sber/Robokassa/Stripe/PayPal/custom — бренды; ₽ не трогали |
| Discounts | типы из хелпера; EmptyState+CTA; confirm delete; loading только у своей строки |

**A7-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| Finance: `isError` не читался — сбой загрузки выглядел как пустой таб; скелетон OR по всем табам блокировал кассы | `QueryErrorAlert`; скелетон только `cashboxesLoading && !cashboxes`; loading на табе транзакций/ЗП/склада |
| Finance: складская история показывала «пусто» во время загрузки | empty только после успеха; `inventoryStock` `isError`/`isLoading` |
| Finance: типы/источник кассовых, ЗП и складских движений — сырые токены API | `moneyFinanceTxTypeLabel` / `txSource` / `salaryTxType` / `inventoryTxType` |
| Finance: клик по товару/складу без подсветки выбранной строки | `bg` как у кошелька лояльности |
| Loyalty: `subs.length===0` без UUID пациента = ложь «у пациента нет абонементов»; то же для кошелька | `needPatientId` / `needPatientWallet`; `isError` пакетов/абонементов/кошельков/кампаний |
| Loyalty: refetch кампании затирал черновик; смена пациента оставляла txs прошлого кошелька; после снятия UUID не было highlight | `campaignDirty`; сброс `selectedWalletId`; `bg` выбранной строки |
| Loyalty: `useLoyaltyCampaignSettings` / `useLoyaltyPackages` queryKey без `clinicId` при clinic-scoped API | ключ `…, clinicId`; `enabled: !!clinicId` |
| Loyalty: kind/status/wallet type сырьём; ISO-даты | хелперы `packageKind` / `passStatus` / `walletTxType`; `DD.MM.YYYY` |
| Commerce: `try/finally` без `catch` (load/save/CSV/vitrine) — сеть молча снимала спиннер | `catch` + `setError` + structured `console.error` |
| Commerce: `createNom`/`createLoc` empty `finally` — кнопка навсегда `loading` | `setSubmitting(false)` / `setLocSubmitting(false)` |
| Commerce: delete точки/номенклатуры без confirm (необратимо) | Modal `deleteLoc*` / `deleteNom*` |
| Commerce/Gateway: refetch клиники затирал несохранённую витрину/шлюз | `storeDirty` / `gatewayDirty` |
| Gateway: Stripe/PayPal label литералами EN; `useClinics` error не виден | ключи `stripeSecret` / `paypalClientId` / `paypalSecret`; `QueryErrorAlert` |
| Gateway `handleSave`: внешний `try` без `catch` | `catch` → `clinicUpdateError` |
| Prepayment: save только `onSuccess` — 403/500 молчит; clinics fail не виден | `onError` + `saveFailed`; `QueryErrorAlert` clinics |
| Discounts: type service/doctor без услуги/врача; percent/amount не enforced | клиентская проверка; lookup `isError` в drawer |

**Вне скоупа A7 (следующий шаг зафиксирован):**

- Тело `QueryErrorAlert` / `formatQueryError` оптом, сырой API `detail` без `code` — **A10 / R10**.
- Символ ₽ и YooKassa — регион клиники (**L3**), не `$` / не Stripe-rename.
- Даты `DD.MM.YYYY` / dayjs — европейская клиника (L3), как Mon-first; не en-US date format.
- Комментарии кода на RU — **R11 / A12**.
- E2E этих экранов нет в `frontend/e2e/` (нечего чинить в A11 по A7).
- Поиск абонемента/кошелька по UUID пациента — lookup UX, не invent name-search (рост DTO).
- Создание кассы с этого экрана — API нет; CTA убран, не stub.
- Payroll policy без `full_name` в DTO — `unknownName` / «по роли»; рост DTO не этот батч.
- Discounts **не** трогать снова в A9.
- CSV-импорт commerce без confirm (широкий blast) — не изобретать второй wizard в этом аудите; если вернёмся — confirm перед upload.
- Loyalty packages/campaigns: API берёт `clinic_id` из JWT, не из header picker. queryKey с `clinicId` делит кэш при смене клиники в UI; если JWT и picker разойдутся — ответ всё равно JWT-клиники. Это контракт платформы, не батч A8.
- Native `type="date"` на фильтре склада Finance — **R14** (браузерный chrome даты).
- Карточки/табы разной высоты — **Law 26 / @QA_VISUAL**, не i18n.
- `tx.source` значения вне closed set (`cash\|acquiring\|package\|deposit\|discount\|other`) остаются сырыми (данные, не chrome).

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n`.

### QUEUE A7 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A7.

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §0 деньги = регион клиники, не язык UI; секция «A7».
2) testUtils.
3) С диска: AdminFinancePage, AdminCommercePage, AdminLoyaltyPage, AdminPrepaymentPage, AdminPaymentGatewayPage, AdminDiscountsPage.

СДЕЛАЙ: ns money.json en+ru. Подписи полей — ключи. Не меняй ₽ / YooKassa.
Числа: locale из useUiLocale.

НЕ: discounts во второй раз в A9, git commit/push.
```

---

## A8 — Лента и отчёты

**Статус:** словари A8 2026-08-18; **перепроверка 2026-08-19:** JSX снова был на RU литералах, e2e ждал «Лента». Pass 3 заново подключил `useTranslation("feed"|"reports")` и EN e2e. Не запускать QUEUE A8 с нуля.

**Файлы:** `AdminDashboardPage.tsx`, `AdminReportsPage.tsx` (+ тест), `AdminAiReportsPage.tsx`, `frontend/e2e/admin-dashboard-feed.spec.ts`

ns: `reports.json`, `feed.json`

helper: `frontend/src/shared/feedI18n.ts` (`feedRevenuePeriodLabel`: `night` / `day` / `week`); `frontend/src/shared/reportsI18n.ts` (`reportsDrillItemTypeLabel`: `lead` / `booking` / `transaction`)

**Что закрыто в A8:**

| Экран / спека | Chrome |
|---------------|--------|
| Feed (`AdminDashboardPage`) | title / New post / compose aria / Publish / comments / metrics / composer+edit modals / attachment warnings — ключи `feed.*`; даты `toLocaleString(dateLocale)`; plural `filesQueued` |
| Reports | titleFull / Traffic source / Campaign / funnel interpolation / attribution table; даты дня `DD.MM.YYYY`; drill без UUID (`unnamedDrill`) |
| AI reports | Yes/No, Closed/Open; даты `toLocaleString(dateLocale)` |
| E2E `admin-dashboard-feed.spec.ts` | «Лента»/«Новый пост»/«Опубликовать» → Feed / New post / Publish / compose aria EN. Фикстуры «Клиника E2E» / «Сотрудник E2E» — данные |
| Vitest `AdminReportsPage` | `await renderWithI18n(..., { locale: "en" })`; chrome EN; фильтр источника = UUID API, не code |

**A8-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| Сбой/скелетон метрик (`dashboard-aggregate`) прятал всю ленту — посты и composer были недоступны | метрики грузятся в своей колонке; лента живёт отдельно |
| `useStaffFeedPosts` `isError` не читался — сеть выглядела как EmptyState | `QueryErrorAlert` + `postsLoadFailed`; empty только после успеха |
| Комментарии без `isError` — сбой = «No comments yet» | `commentsLoadFailed` |
| Delete/like/save поста молчали при 403/500 | Alert + `deletePostFailed` / `likeFailed` / `savePostFailed` + `console.error` |
| `createPost.isPending` падал до конца загрузки вложений — второй Publish во время upload | `isPublishing` до конца attachments; Cancel/overlay не закрывают модалку |
| EmptyState ленты без CTA при праве постить | `action: newPost` открывает composer |
| Фильтр «Traffic source» слал `traffic_source_code` (`google`) в query `traffic_source_id` (UUID) — 422, таблица пустела | Select value = `traffic_source_id`; опции копятся, чтобы фильтр не съедал сам себя |
| Drill при загрузке показывал `drillEmpty` | скелетон/`loading` / `QueryErrorAlert` |
| Drill всегда `drill_type=leads`, hint про bookings врал | SegmentedControl leads/bookings/transactions |
| `"AI Marketing Advisor"` и `"No-show: …"` литералы EN на RU locale | `advisorTitle` / `noShowRateLine` |
| `item.type` сырьём; UUID в drill при пустом label | `reportsDrillItemTypeLabel`; `unnamedDrill` |
| owner/campaigns/insights `isError` игнорировались; скелетон OR по всем запросам дублировал карточки | ошибки в `anyError`; boot-skeleton только пока нет ни одного блока |
| AI-отчёт без дат = ложь «нет конфликтов»; refetch error прятался за stale data | default 7 дней; empty только при выбранных датах; Alert при `isError` даже если есть cache |
| Карточки отчётов `shadow` + border (двойное отделение) | `withBorder`, без shadow |

**Вне скоупа A8 (следующий шаг зафиксирован):**

- Тело `QueryErrorAlert` / `formatQueryError` оптом, сырой API `detail` без `code` — **A10 / R10**. Heuristic empty-db `/клиник|clinic/i` на `detail` остаётся (R10).
- Символ ₽ на выручке ленты и в отчётах — регион клиники (**L3**), не `$`.
- Комментарии кода на RU в `AdminDashboardPage` — **R11 / A12**.
- Native `type="date"` на фильтрах отчётов / AI — **R14** (браузерный chrome даты).
- `issue_category` / `sentiment` в AI-таблице — открытый набор с API (данные). Closed set `lead`/`booking`/`transaction` в drill закрыт хелпером; неизвестный `type` остаётся сырым.
- `display_label` брони в drill может содержать сырой `booking.status` (`confirmed` и т.д.) — статус записи это контур **A2 bookings**, не выдумывать второй словарь здесь.
- Строки AI Marketing Advisor — текст с API, не chrome.
- MultiSelect клиник на ленте не синхронизируется с clinic picker в шапке после первого init — продуктовый контракт фильтра метрик, не A9.
- Настройки / strip / discounts — **A9 / A1 / A7**, не трогать здесь.
- E2E feed владение закрыто здесь; A11 не повторяет dashboard chrome.

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n src/admin/pages/__tests__/AdminReportsPage.test.tsx`.

### QUEUE A8 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A8.

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §0 e2e-владельцы, секция «A8».
2) testUtils.
3) С диска: AdminDashboardPage.tsx, AdminReportsPage.tsx + тест, AdminAiReportsPage.tsx, frontend/e2e/admin-dashboard-feed.spec.ts.

СДЕЛАЙ: ns reports.json + feed.json en+ru.
E2E dashboard: «Лента»/«Новый пост» → EN chrome. Это владение A8, не A11.
Тест AdminReportsPage — EN.

НЕ: git commit/push.
```

---

## A9 — Система (без RBAC JSON)

**Статус:** принят в коде + A9-audit 2026-08-18. Не перезапускать QUEUE A9. A9b–A12 приняты (A12 — гейт 2026-08-18).

**Файлы:**

- `AdminSettingsPage.tsx`, `AdminSubscriptionPage.tsx`, `AdminSubscriptionCapabilitiesCard.tsx`
- `AdminEmbedPage.tsx`, `AdminRagKbPage.tsx`, `AdminDataExportPage.tsx`
- `AdminAiSettingsPage.tsx`, `AdminFormsPage.tsx`, `AdminAgreementsPage.tsx`
- `AdminEmergencyNotificationsPage.tsx`, `AdminNotificationPolicyPage.tsx`
- `AdminStylingPage.tsx`, `AdminStickersPage.tsx`, `AdminKnowledgePage.tsx`, `AdminIntegrationsPage.tsx`

`AdminOwnerSubscriptionStrip` уже в A1 — не дублировать.

ns: `settings.json`

helper: `frontend/src/shared/settingsI18n.ts` (`settingsRoleLabel` / `settingsPriorityLabel` / `settingsAiIntentLabel` / `settingsAiModeLabel` / `settingsAiStatusLine` / `settingsFormStatusLabel` / `settingsFormSubmittedByLabel` + option builders)

**Что закрыто в A9:**

| Экран | Chrome |
|-------|--------|
| Settings hub | title / intro / 15 ссылок — ключи `hub.*` |
| Subscription page | title / intro; карточка capabilities chrome (`capabilities.*`) |
| Embed | webhook / keys / copy tooltips / revoke confirm; даты `toLocaleString(dateLocale)` |
| RAG KB | CRUD chrome; empty vs loading; delete confirm; даты locale |
| Data export | owner-only / summary / manifest / request; UUID организации не показывается (Law 8); download try/catch |
| AI settings | intents/modes/status через хелпер; `ai_provider_type` — токен API |
| Forms | шаблоны + submissions; loop var `tpl` (не тень `t()`); default field / copy suffix; lookup ID — фильтр; closed-set `status` / `submitted_by` хелпером; UUID пациента/визита в таблице **не показываются** (Law 8) |
| Agreements / notify / styling / stickers / integrations | поля и save; styling/1C save `catch` + Alert |
| Emergency | роли/приоритет хелпером; comments `useTranslation`; UUID админа → `staffFallback`; publish не чистит форму до success |
| Knowledge | роли на бейджах; EmptyState CTA; дата `DD.MM.YYYY` (L3) |

**A9-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| Стена объявлений не обновлялась после publish/ack: `useStaffAnnouncements` жил на ключе `["staff-collab","announcements","posts",limit]`, мутации инвалидировали только `feedPosts` | `queryKeys.staffCollab.announcementsPosts*` + `invalidateStaffFeedSurfaces` на create/like/ack **и** update/delete/upload/комментарии |
| Сырые ключи publish-policy рядом с префиксом announcements | `announcementPublishPolicy` / `announcementPublishPolicyAudit` в `queryKeys.ts` |
| Embed / RAG / export: `!session` во время загрузки = «нет org» / «только owner» | отдельный `sessionLoading` / `sessionError` |
| Embed: пустой webhook после успеха выглядел как loading | `noWebhookUrl` vs loading |
| Embed/RAG/Knowledge/notify/ack/publish: мутации без `onError` | Alert + ключи `*Failed` + `console.error` |
| RAG list `isError` в карточке = пусто | `loadListFailed`; empty только после успеха |
| RAG edit: refetch документа затирал черновик | `editHydrated` как у Knowledge |
| RAG Delete: `isPending` на всех строках | `delMut.variables === row.id` |
| RAG/export: session error молчал | Alert `sessionFailed` |
| Export download / request через `window.alert`; success показывал RU `message` с бэка и UUID заявки | in-page Alert; `export.requestOk`; UUID заявки не показывается |
| Export кнопка манифеста не блокировалась на время fetch | `downloading` |
| Forms `status` / `submitted_by` сырьём (`signed`/`patient`) | `settingsFormStatusLabel` / `settingsFormSubmittedByLabel` |
| Forms таблица показывала `patient_id` / `booking_id` UUID (Law 8) | `patientLinked` / `visitLinked` / «—»; фильтр по ID остаётся lookup |
| Comments `isError` = «нет комментариев» | `commentsLoadFailed` |
| Ack modal без loading/error | loading / `ackStatusFailed` |
| Ack кнопка без pending | `loading` + disable всех ack на время мутации |
| Agreements / AI / styling / integrations / knowledge edit: refetch затирал unsaved draft | dirty / hydrated флаги |
| Integrations / styling load `isError` игнорировались | Alert `loadFailed`; loading gate до пустой формы |
| Capabilities card: `isError` = `null`; `shadow`+border | Alert сессии; только `withBorder` |
| Stickers — задекларированная страница без набора | chrome честный: built-in set + later custom (не фейковый picker) |

**Вне скоупа A9 (следующий шаг зафиксирован):**

- `labelForEntitlementKey` / `entitlementDisplay.ts` — бейджи на карточке capabilities остаются RU до **A10**. **Закрыто в A10.**
- `AdminOwnerSubscriptionStrip` / `common.subscription.*` — **A1**.
- `AdminDiscountsPage` — **A7**.
- `PlatformPricingSection` на `/admin/subscription` — маркетинговый каталог, RU copy. **A10–A12 не владеют.** Зафиксировано во «Вне очереди» п.4 (волна лендинга тарифов).
- `rbacRightsPoliciesPageCopy` / `rbacDomainGlossary` / `rbacCsvExport` / copy `AdminRightsPoliciesPage` — **A9b**.
- Тело `QueryErrorAlert` / `formatQueryError` оптом, сырой API `detail` без `code` — **A10 / R10**. Heuristic empty-db на `detail` остаётся.
- Комментарии кода — **R11 / A12**.
- Native date chrome — **R14**.
- Имена пациентов/визитов в forms — рост DTO (`patient_name` / номер визита). Фильтр по ID остаётся; в таблице UUID больше нет. Не invent name-search.
- `formats_note` / ключи `approximate_counts` / `ai_provider_type` / `folder_key` / payload `submission.data` — данные API, не chrome.
- Политика публикации объявлений: GET `/publish-policy` требует `rbac.manage`. Клиент стены **не** читает политику (403 у врача). Deny ловится как `publishFailed` после POST. Нужен лёгкий `GET .../announcements/can-publish` для актора — **не A9b**, отдельный API-рост; иначе 403, который UI мог знать заранее.
- Имена брендов 1C / Bitrix24 не переводятся.
- `AdminStickersPage` custom upload — продуктовый later, не A9b–A12.
- Backend `DataExportRequestResponse.message` остаётся RU в API (не chrome). UI больше его не показывает.
- E2E этих экранов нет в `frontend/e2e/` (нечего чинить в A11 по A9).
- Сырые ключи `["staff-collab","calendar-month"]` в calendar-мутациях — контур календаря (A2), не A9.

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n`.

### QUEUE A9 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A9 (система без RBAC JSON).

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — секция «A9», инвентарь A9. Discounts = A7, strip = A1, RBAC JSON = A9b.
2) testUtils. Ключи strip подписки не дублировать, если уже в A1.
3) С диска: AdminSettingsPage, AdminSubscriptionPage, AdminSubscriptionCapabilitiesCard, AdminEmbedPage, AdminRagKbPage, AdminDataExportPage, AdminAiSettingsPage, AdminFormsPage, AdminAgreementsPage, AdminEmergencyNotificationsPage, AdminNotificationPolicyPage, AdminStylingPage, AdminStickersPage, AdminKnowledgePage, AdminIntegrationsPage.

СДЕЛАЙ: ns settings.json en+ru.

НЕ: rbacRightsPoliciesPageCopy / rbacDomainGlossary / rbacCsvExport (A9b). Не git commit/push.
```

---

## A9b — RBAC словари

**Статус:** принят в коде + A9b-audit 2026-08-18. Не перезапускать QUEUE A9b. A10–A12 приняты (A12 — гейт 2026-08-18).

**Файлы:**

- ns: `frontend/src/i18n/locales/{en,ru}/rbac.json` (+ регистрация в `index.ts` / `i18next.d.ts`)
- helper: `frontend/src/shared/rbacI18n.ts` (`getDomainGlossary` / `getDomainPrimaryLabel` / `getDomainPlainSelectLabel` / `getPolicyFieldLabel` / `getRolePresetOptionLabel` / `rbacTooltipStyles`)
- `rbacDomainGlossary.ts`, `rbacRightsPoliciesPageCopy.ts` — тонкие re-export, **без** встроенных словарей
- `rbacCsvExport.ts` — download helper без chrome; заголовки CSV — ключи `csv.*`
- `AdminRightsPoliciesPage.tsx` — `useTranslation("rbac")`; второго language SegmentedControl нет (A1)

**Что закрыто в A9b:**

| Экран / модуль | Chrome |
|----------------|--------|
| Rights & policies | title / intro / glossary / tabs / panels / diffs / create-delete clinic role / critical confirm — ключи корневого `rbac.*` |
| Announcement publish policy (owner) | было литералами RU на странице → `announcements.*`; роли deny через `settingsRoleLabel` |
| Announcement audit log | `announcements.audit*` + CSV headers; actor без UUID; denied users резолвятся в имя |
| Domain glossary | short/gentle/inside en+ru; неизвестный домен — `domains.unknown` / `fallback`; **баг:** `all` всегда отдавал RU short — теперь locale |
| Policy field labels (diff table) | `policy.*` |
| CSV domain/permission/announcement | заголовки `t("csv.*")`, не snake_case в коде |
| R16 | `UiLocale` только `@/i18n` |

**A9b-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| Session `isError` → ложь «нет доступа» (`canManage=false`) | отдельный `sessionFailed` |
| Нет клиники: catalog `enabled=false`, `isLoading=false` → пустые селекты ролей | ждать clinic context; `needClinic*` EmptyState |
| `users`/`policies`/`audit` без `enabled` при `clinicId=null` мешали JWT-home с выбранной клиникой | `enabled: Boolean(effectiveClinicId)` как у catalog |
| `auditQ.isLoading`/`isError` блокировали **весь** экран (роли нельзя править, если журнал лежит) | аудит грузится/ошибается во вкладке; empty = `auditEmpty` |
| Refetch каталога/политик затирал unsaved draft (роль, сотрудник, политики, deny объявлений) | dirty/hydrate; смена клиники сбрасывает **clinic-scoped** draft, не org-policy объявлений |
| PATCH роль/сотрудник/политики и critical-Apply без `onError`; модалка закрывалась до ответа | Alert `saveFailed` + `console.error`; модалка закрывается только на success; Apply `loading` |
| Delete clinic role без `onError` | Alert в модалке, `Accept-Language` уже уходил |
| GET publish-policy у non-owner / до сессии → 403 в кэше; сбой GET = пустая форма, Save мог затереть политику | `enabled: isOwner`; loading/error; Save disabled пока не загрузилось и нет dirty |
| `e.message` на Save объявлений | ключ `announcements.saveFailed` (create/delete роли оставляют localized API `detail` — контракт Accept-Language) |
| Boolean diff политик = сырые `true`/`false` | `valueYes` / `valueNo` |
| RU chrome «Diff before save» | «Изменения до сохранения» / EN «Changes before save» |
| Intro papers `shadow` + `withBorder` | только `withBorder` |
| `AdminClinicContext` fallback «Текущая клиника» (не в `admin/`, A12 grep не поймал бы) | `common.clinics.currentFallback` |

**Вне скоупа A9b (следующий шаг зафиксирован):**

- `labelForEntitlementKey` / `entitlementDisplay.ts` — **A10**. **Закрыто в A10.**
- Тело `QueryErrorAlert` / `formatQueryError` / сырой `detail` без `code` на PATCH (кроме create/delete роли, где бэкенд сам локализует по Accept-Language) — **A10 / R10**. Коды на `/admin*` закрыты в A10; сырой `detail` без `code` остаётся R10.
- Описания прав из API-каталога (`p.description`) остаются языком продукта (часто RU) — не выдумывать второй каталог. Ключ `catalogDescriptionLanguageNote` объясняет это на EN; в `ru` строка пустая (не fallback на EN).
- Имена кастомных ролей `r.name` — данные API; системные manager/admin/doctor в deny-select закрыты `settingsRoleLabel`.
- Колонка аудита `entity_type:entity_id` и сырой `action` — технический журнал (Law 8/9 exception, не резолвить UUID сущности без отдельного API).
- `r.action` / permission codes в badge — коды системы, не chrome.
- `PlatformPricingSection` — после A12 / marketing i18n.
- ErrorBoundary fallback — **A10**. **Закрыто в A10.**
- PATCH RBAC (permissions/roles/policies) не шлёт `Accept-Language` — бэкенд этих ручек не читает header. Не раздувать API в A9b; если понадобятся локализованные 409 — отдельный бэкенд-срез, не A10.
- Каталог GET без Accept-Language: `description` как в БД. Не invent EN catalog.

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n`.

### QUEUE A9b (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A9b (RBAC словари). A1 должен уже подключить useUiLocale и убрать второй switcher.

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §0 RBAC, §2 «один контрол», секция «A9b».
2) С диска: rbacRightsPoliciesPageCopy.ts, rbacDomainGlossary.ts, rbacCsvExport.ts, AdminRightsPoliciesPage.tsx, существующий useUiLocale.

СДЕЛАЙ: перенос copy в frontend/src/i18n/locales/{en,ru}/rbac.json. Один источник.
Не возвращай SegmentedControl языка на страницу. CSV headers — ключи.

НЕ: git commit/push.
```

---

## A10 — Shared хвосты

**Статус:** принят в коде + A10-audit 2026-08-18. Не перезапускать QUEUE A10. A11–A12 приняты (A12 — гейт 2026-08-18).

**Файлы:**

- `frontend/src/shared/ErrorBoundary.tsx` — class ловит; chrome — `ErrorBoundaryFallback` (`useTranslation("common")`, ключи `errors.crash*`)
- `frontend/src/shared/entitlementDisplay.ts` — без RU map; `settings.entitlements.{slug}` (`crm.pipeline` → `crm_pipeline`)
- `frontend/src/shared/errors.ts` — `commonErrorI18nKey` / `isAdminChromePath`; **`formatQueryError` не переписывался** (пациентский PWA)
- `frontend/src/shared/ui/QueryListStates.tsx` — на `/admin*` известный `code` → `common.errors.<code>`; иначе `formatQueryError`
- `frontend/src/shared/ui/AdminDrawer.tsx` — close `aria-label` = `common.drawerClose`
- ns: `common.json` (`errors.crash*`, coded errors, `drawerClose`, `emoji`) + `settings.json` (`entitlements.*`)
- Admin emoji (default picker остаётся RU для PWA): `AdminDashboardPage` composer + `AdminTasksPage` передают `tCommon("emoji")`. Чаты A5 уже передают `chat.omni.emojiAria`

**Что закрыто в A10:**

| Модуль | Chrome |
|--------|--------|
| ErrorBoundary | title / body / retry / error label — ключи `errors.crash*`. `error.message` сырьём (техническое) |
| QueryErrorAlert на `/admin*` | известные HTTP/domain `code` → `common.errors.<code>` (не сырой `detail`) |
| QueryErrorAlert на `/app*` | по-прежнему `formatQueryError` (в т.ч. RU `detail`) |
| Capabilities badges | `labelForEntitlementKey` читает `settings.entitlements.*`; неизвестный ключ — сырой key + `fallbackHint` |
| AdminDrawer close | `drawerClose` |
| Emoji aria (admin dashboard/tasks) | `common.emoji`; default `"Эмодзи"` не трогали |

Не дублировали: AI tooltips (A1), PersonNameLink / StaffCardModal (A5-audit), `AdminClinicContext` fallback (A9b-audit), CompactMonthPicker (A0).

**A10-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| Backend `EMPTY_DB_NO_CLINIC` — строка на HTTP 404; handler ставит `code: not_found`. A10 мапил `not_found` → «запись не найдена» и **съедал** empty-clinic | `adminQueryErrorI18nKey`: heuristic `isEmptyClinicDatabaseError` **раньше** generic `not_found` |
| Ключ `empty_db_no_clinic` был в словаре, но бэкенд этот `code` **не шлёт** — декларация без эффекта | heuristic + тест: 404 + RU copy → `errors.empty_db_no_clinic` |
| HTTP 405 `method_not_allowed` есть в каноне API, в `COMMON_ERROR_CODES` не было → RU из `normalizeErrorMessage` | ключ `errors.method_not_allowed` |
| Root `ErrorBoundary` общий с маркетингом/PWA. A10 `useTranslation` + default `en` → crash на `/` и `/app` стал EN | вне `/admin*` fallback берёт `getFixedT("ru")` |
| `ErrorBoundary` retry: `setState` + reload без disabled | `retrying` + `loading`/`disabled` на кнопке |
| Crash chrome без рамки (Title на пустом фоне) | `Paper withBorder`, без shadow |
| Длинный `error.message` раздувал экран | `lineClamp={6}` |
| Hints `settings.entitlements.*.hint` переведены, на карточке **не показывались** | `Tooltip` на бейджах capabilities |
| `AdminDrawer` close aria: `t` стабилен, смена языка могла оставить старый label; caller `closeButtonProps` затирал default | deps `i18n.language`; default aria, если caller не задал |
| `GlassModal` (admin chrome) без локализованного close | `common.dialogClose` |
| Два предиката `/admin*` (`isAdminPath` и `isAdminChromePath`) | `isAdminPath` делегирует в `isAdminChromePath` |

**Вне скоупа A10 (следующий шаг зафиксирован):**

- Сырой API `detail` без своего `code` **почти не бывает** на HTTPException: handler всегда ставит status-default (`forbidden` / `not_found` / …). Остаток R10: клиентский `new Error` без `code`; HTML 4xx без transport-кода; доменные коды вне allowlist (`omni_*`, `rag_*`, `billing_revoked`, booking `slot_unavailable` на QueryErrorAlert). 401 admin: **закрыто A12-audit**. 405/502/traceback: **A12-repass** штампует transport `code`.
- `formatQueryError` generic fallback остаётся RU — пациентский PWA.
- Default `VoiceNoteRecorderButton` / `SignatureCanvas` / `EmojiMartPopoverPicker` — patient props; admin уже передаёт `t()`.
- `BOOKING_STATUS_LABEL_RU` — **удалено A12-audit**; admin только `bookingStatusLabel`.
- `chatMessageBodyDisplay` плейсхолдеры `[Голосовое сообщение]` — данные протокола, не chrome.
- `PlatformPricingSection` — после A12 / marketing i18n.
- Остатки RU chrome в экранах (например сроки на `AdminTasksPage`) — **закрыто в A12:** это был мёртвый `{/* legacy detail modal removed */}`, живой UI уже `TaskDetailsView` + ключи.
- PATCH без `Accept-Language` — как в A9b, не раздувать API здесь.
- Бэкенд по-прежнему не шлёт `code: empty_db_no_clinic` (строка + 404). Снять heuristic — отдельный бэкенд-срез, не A11. Пока heuristic обязателен.
- Доменные коды omni/RAG/billing в `QueryErrorAlert` остаются `formatQueryError` (экранные ключи A5/A9, не раздувать `common.errors`).
- E2E chrome — **A11**. **Закрыто в A11** (инвентарь спек; SignInShell split на `/login` и `/platform/login`).

Проверка: `cd frontend && npx tsc -b` + `npm test -- --run src/i18n src/shared/__tests__/bookingErrors.i18n.test.ts src/shared/ui/__tests__/QueryListStates.test.tsx`.

### QUEUE A10 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A10 (shared хвосты). Экраны A2–A9 должны быть уже на ключах.

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §1 п.5 ErrorBoundary class, §0 formatQueryError, секция «A10», риск R10.
2) С диска: frontend/src/shared/ErrorBoundary.tsx, entitlementDisplay.ts, errors.ts (что ещё не ключи по code), QueryListStates/CompactMonthPicker (не ломать A0).

СДЕЛАЙ: ErrorBoundary fallback — function component с useTranslation, не хук в class.
entitlementDisplay, если ещё RU. Добить common.errors по code. Не сырой detail.

НЕ: src/app pages, git commit/push.
```

---

## A11 — E2E хвосты

**Статус:** принят в коде + A11-audit 2026-08-18. Не перезапускать QUEUE A11. A12 принят 2026-08-18.

Пять спек в `frontend/e2e/` (других `*.spec.ts` нет).

| Спека | Admin chrome | Осталось RU | Решение A11 |
|-------|--------------|-------------|-------------|
| `smoke-routes.spec.ts` `/admin/login` | heading `Clinic staff sign-in` + SignInShell `auth.shell.title` | — | A1 heading; A11 добавил assertion оболочки SignInShell (EN) |
| `smoke-routes.spec.ts` `/login` | panel `Clinic: staff and owner` + SignInShell title | body `Вход` | оболочка EN; body маркетинга **не** трогали (R4) |
| `smoke-routes.spec.ts` `/platform/login` | SignInShell title EN | body `Основатель платформы` | оболочка EN; body основателя **не** переводили (R4) |
| `smoke-routes.spec.ts` landing/pricing/sandbox | — | marketing headings | не трогали |
| `smoke-routes.spec.ts` `/signup` | — | `Регистрация организации` | не переводили; assertion сверена с `SignupPage` Title (было устаревшее «клиники») |
| `admin-omni-chat.spec.ts` | Omni-chat / Claim / Emoji / File / Photo / voice / Assistant mode / Reply / Channels: all | фикстуры ФИО и реплики | HEAD ещё RU → A11 закрыл chrome; фикстуры — data |
| `admin-dashboard-feed.spec.ts` | Feed heading / compose aria / New post / Publish | фикстуры «Клиника E2E» / «Сотрудник E2E»; тело поста | HEAD ещё RU → A11 закрыл chrome |
| `smoke-public.spec.ts` | — | landing | не трогали |
| `patient-entry-sign-in.spec.ts` | — | patient headings | не трогали |

R14 (native `type=email` / `required`) не чинили.

**A11-audit (что было формально и не работало):**

| Дыра | Фикс |
|------|------|
| A11 гонял Playwright на **stale `dist/`**. `npm run build` exit 1: workbox 2 MiB, `index-*.js` 2.3 MB. Jenkins, `build-and-test-entitlements.yml`, ADR-006 `build && test:e2e` — красные при «зелёном» e2e | `workbox.maximumFileSizeToCacheInBytes` = **3 MiB** в `vite.config.ts` и зеркале `vite.config.js`. Runtime cache `/assets/*.js` по-прежнему NetworkFirst |
| Спеки не фиксировали `ui.locale`. Default сейчас `en`, но leftover `ru` в storage = ложный красный на EN chrome | `localStorage.setItem("ui.locale","en")` в init smoke-routes / omni / dashboard |
| `getByText("Feed").first()` мог пройти по **nav link**, если страница ленты не смонтировалась | `getByRole("heading", { name: "Feed" })` — `ContextBar` `Title order={3}` |
| Тест omni называется «channel filter works», после VK не проверял, что Иван исчез (Мария видна и без фильтра). Детальный GET всегда возвращал «Иван Иванов» — клик по Марии не менял шапку | `omniDetail(chatId)` совпадает со списком; после клика по Марии: `getByText("Иван Иванов")` count 0 |
| Мёртвый `STORAGE` в omni spec | удалён |
| Review-pass R3 всё ещё писал «CI красный до A11» при закрытом A1 | таблица §review + R3: закрыто A11 + этот audit |

**Вне скоупа A11 (следующий шаг зафиксирован):**

- Маркетинг body / patient e2e / `index.html` lang — после A12, отдельный разговор @LEAD/@SEO.
- Founder form (`PlatformFounderLoginPage` / `PlatformFounderSignInPanel`) остаётся RU (R4).
- Фикстуры omni/dashboard — data, не chrome (A12 classify, не переводить).
- Backend pytest `tests/e2e/` — не Playwright admin chrome (проверено: RU login/лента/claim строк нет).
- Слить дубль `vite.config.js` ↔ `vite.config.ts` — отдельный hygiene, не A12 grep.
- `aria-label="needs-attention"` в omni — технический EN, не i18n; A12 не гейтит (нет кириллицы).
- Docker compose profile `e2e` бьёт в сервис `frontend`, не в vite preview — образ собирает человек, не этот батч.
- R14 native HTML validation — лимит волны.

Проверка (2026-08-18, A11-audit): `cd frontend && npm run build` (exit 0) + `npx playwright test` — **17 passed** на свежем `dist/`.

### QUEUE A11 (исторический — не запускать повторно)

```
@DEV ТОЛЬКО батч A11 (e2e хвосты). Не повторяй A1/A5/A8, если их спеки уже EN.

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — §0 e2e-владельцы, секция «A11».
2) С диска все frontend/e2e/*.spec.ts. Сверьсь: `/admin/login` + `/login` panel heading = A1, omni = A5, dashboard feed = A8.

СДЕЛАЙ: почини только оставшийся admin chrome на RU.
Маркетинг/patient e2e не переводить, кроме падения из-за SignInShell split (тогда assertion оболочки, не body).
Не добавляй сценарии.

НЕ: git commit/push.
```

---

## A12 — Гейт

**Статус:** принят в коде 2026-08-18 + A12-audit тот же день. Не перезапускать QUEUE A12. Отчёт — `## A12 report` / A12-audit ниже.

1. Grep кириллицы в литералах (не цель — вычистить комментарии):

```
rg -n --pcre2 "['\"\`][^'\"\`]*[А-Яа-яЁё]" frontend/src/admin frontend/src/auth/ClinicSignInPage.tsx frontend/src/auth/panels/ClinicStaffSignInPanel.tsx frontend/src/auth/SignInShell.tsx frontend/src/shared/errors.ts frontend/src/shared/bookingStatusMeta.ts frontend/src/shared/aiFeatures.ts frontend/src/shared/ui/QueryListStates.tsx frontend/src/shared/ui/CompactMonthPicker.tsx frontend/src/shared/ui/AdminDrawer.tsx frontend/src/shared/ui/GlassModal.tsx frontend/src/shared/ErrorBoundary.tsx frontend/src/shared/adminChatChrome.ts frontend/src/shared/entitlementDisplay.ts
```

2. Каждый хит классифицировать: `chrome` (чинить ключом) / `data` (ФИО, фикстура) / `comment` (не гейт) / `api-detail-passthrough` (лимит R10).
3. `cd frontend && npm test` (или честно: какие suites и почему не полный).
4. Дописать сюда `## A12 report` с датой и таблицей хитов.

### QUEUE A12 (исторический — не запускать повторно)

```
@QA_ARCH + @DEV ТОЛЬКО батч A12 — гейт волны, не новый перевод «всего подряд».

СНАЧАЛА ПРОЧИТАЙ (порядок, до любой правки):
1) docs/artifacts/ADMIN_I18N_EN_ROADMAP.md — «Гейт волны», секция «A12», риски R10/R11.
2) Прогони grep из секции A12 по файлам из списка. Классифицируй каждый хит: chrome / data / comment / api-detail-passthrough.

СДЕЛАЙ: chrome на русском = ключ en+ru, не «потом».
data/comment/api-detail — в отчёт, не океан комментариев.
Запусти frontend тесты админки (или честно напиши, какие suites).
Допиши ## A12 report в конец docs/artifacts/ADMIN_I18N_EN_ROADMAP.md.

НЕ: перевод docs/, index.html, patient/marketing body, git commit/push.
```

## A12 report

**Дата:** 2026-08-18.  
**Греп:** тот же класс `['"\`][^'"\`]*[А-Яа-яЁё]` по списку секции A12 (ripgrep / Cursor Grep). One-liner `rg --pcre2` в PowerShell на этой машине ломает кавычки — не притворялись, что он отработал.  
**Дополнительно:** любой `[А-Яа-яЁё]` в `frontend/src/admin` (включая JSX без кавычек и комментарии) — чтобы гейт не был формальным.

### Chrome, который чинили

| Файл | Хит | Класс | Действие |
|------|-----|--------|----------|
| `AdminTasksPage.tsx` ~1439–2054 (до правки) | ~50 RU label/кнопка/Alert внутри `{/* legacy detail modal removed */}` | `comment` (мёртвый JSX; A10-audit принял за живой chrome сроков) | Блок **удалён**. Живой detail = `TaskDetailsView` + `tasks.view.*` (en+ru уже были). Ключи не дублировали. |

Живого RU chrome (кнопка / title / Alert / aria / EmptyState) в gated-путях **не осталось**. Auth `ClinicSignInPage` / `ClinicStaffSignInPanel` / `SignInShell` — 0 хитов. `AdminOwnerSubscriptionStrip` — 0. `TaskDetailsView` — 0.

### Остаток официального grep (не chrome)

Сгруппировано. Комментарии **не** переводили (R11).

| Класс | Где | Что |
|-------|-----|-----|
| `comment` | `AdminTasksPage.tsx` JSDoc `taskAssigneeIdList`; `AdminDashboardPage.tsx` aria-controls; `AdminOmniVaultPage.tsx` TODO Excel; `AdminStaffCalendarPage.tsx` (14, в т.ч. «Дата»/«В календарь» в `//`); `AdminLoginPage.tsx`; `ScheduleCalendarGrid.tsx` / `ScheduleCalendar.tsx` / `SchedulePage.tsx` / `BookingEntityDrawer.tsx` / `PatientEntityDrawer.tsx` / `DoctorEntityDrawer.tsx` / `entityDrawerChrome.tsx` / `AdminAdministratorsPage.tsx` / `AdminOmniChatPage.tsx` / `rbacCsvExport.ts`; `aiFeatures.ts`; `AdminDrawer.tsx` «админская оболочка»; `QueryListStates.tsx` / `CompactMonthPicker.tsx` JSDoc; `adminChatChrome.ts` (кириллица в JSDoc без кавычек — regex литералов не бьёт) | Не гейт |
| `data` | `AdminReportsPage.test.tsx` «Кампания 1»; `AdminSalesPipelinePage.test.tsx` имена воронки/стадий/лида/заметки; `ScheduleCalendarGrid.test.tsx` «Иванов Иван» | Фикстуры API, не chrome |
| `data` (негатив EN) | `AdminTasksPage.test.tsx` `queryByText("Все потоки"/"Задачи"/"Лиды (лог)")`; `AdminPatientsPage.test.tsx` `"Пациенты"` | Проверка, что default **не** RU |
| `api-detail-passthrough` (R10) | `errors.ts` `formatQueryError` fallback «Произошла ошибка…»; heuristic empty-db (`нет ни одной клиник` / `no clinic`); `getBookingErrorMessage` RU (вызывает **только** `BookingWizardPage`, не admin) | Не маскировать под «переведено». Admin booking chrome — `bookingErrorI18nKey` + `bookings.json` |
| `api-detail-passthrough` (R10) | `AdminReportsPage.tsx` `/клиник\|clinic/i` на `errMsg` | Heuristic empty-db, как A8/A10 |
| не chrome | `bookingStatusMeta.ts` `BOOKING_STATUS_LABEL_RU` | **Удалено A12-audit.** Admin: `bookingStatusLabel` → `bookings.status.*` |

`ErrorBoundary.tsx`, `entitlementDisplay.ts`, `GlassModal.tsx` — 0 кириллицы.

### Вне списка A12 (не чинили)

| Что | Почему не A12 |
|-----|----------------|
| `frontend/src/api/client.ts` `throw new Error("Требуется авторизация")` | **Закрыто A12-audit:** `ApiErrorWithCode("Authentication required", "unauthorized")` |
| Default `EmojiMartPopoverPicker` / `VoiceNoteRecorderButton` / `SignatureCanvas` RU | A10: admin уже передаёт `t()`; patient props |
| `QueryListStates.test.tsx` RU title / `/app` crash / API detail | Тест контракта patient vs admin, не дыра chrome |
| Founder/patient panels (`PlatformFounder*`, `PatientPhoneAuthPanel`) | R4 / вне волны |
| `index.html` `lang="ru"`, маркетинг body | **Phase 4 + leftover 2026-08-21.** Sandbox/legal/founder ops/PWA chrome on keys. Task **modal** (`TaskDetailsView`) + **Kanban/create/routing/stream colour/chat/approval queue** + **`AdminTaskDetailsPage` chrome** on `tasks` keys. Остальные admin families, API catalog без seed, backend `detail`. |

### Тесты (честно, не полный `npm test`)

Полный `cd frontend && npm test` (vitest watchless по всему `src/`, включая patient/marketing) **не** гоняли: вне волны, долго, не гейт A12.

Прогнано:

```
cd frontend && npx tsc -b
npx vitest run src/i18n src/admin src/shared/__tests__ src/shared/ui/__tests__/QueryListStates.test.tsx src/auth/__tests__/ClinicSignInPage.test.tsx
```

**`tsc -b` exit 0.** Vitest A12: 16 files / 102 passed. A12-audit vitest: 17 files / 107 passed (`client-api-errors` + 401/status-map). Playwright в A12 **не** гоняли — дыра, закрыта A12-audit (см. ниже).

### Гейт волны

В JSX/строковых литералах **chrome** кириллицы нет в `frontend/src/admin/**`, трёх auth-файлах списка и shared из § «Гейт волны». Сырой API `detail` / patient `getBookingErrorMessage` / HTML 4xx в `normalizeErrorMessage` / комментарии — заявленный остаток R10 (см. A12-repass + «Вне очереди»).

### A12-audit (что было формально и не работало)

| Дыра | Фикс |
|------|------|
| Гейт перечислял `bookingStatusMeta.ts` как файл без chrome-кириллицы, но `BOOKING_STATUS_LABEL_RU` жила в том же модуле. A12 классифицировал «не chrome» и оставил карту. После A12 уборки в очереди не было; `documentation/USER_DOCS/ADMIN_BOOKINGS.md` всё ещё ссылался на карту как на источник статусов | Карта **удалена**. Подписи только `bookingStatusLabel`. USER_DOCS сверен с кодом. Тест: `"BOOKING_STATUS_LABEL_RU" in mod === false` |
| 401 admin: `throw new Error("Требуется авторизация")` **после** `location.href = login`. QueryErrorAlert / ErrorBoundary на `/admin*` могли вспыхнуть RU: нет `code` → `formatQueryError` | `throwAdminUnauthorized()` → `ApiErrorWithCode(..., "unauthorized")`. Alert мапит `common.errors.unauthorized` (EN default). Редирект как был |
| «Вне очереди» было списком лозунгов без владельца: `PlatformPricingSection` на `/admin/subscription` (смешанный EN chrome + RU прайс) легко потерять | Нумерованный backlog ниже |
| «Как кидать»: «QUEUE A0–A12 ниже» — блоки размазаны по секциям батчей, не в конце файла | Формулировка исправлена |
| A12 и A12-audit **не** прогнали Playwright: «17 passed» было со слов A11-audit. После правок `client.ts` / `AdminTasksPage` / статусов это не доказательство. `npx playwright install` на этой Windows зависал после 100% zip (chromium extract, потом ffmpeg-1010 → 0-байтный `ffmpeg-win64.exe`) | Chromium 1148 + headless-shell уже были на диске. ffmpeg-1010 дожат `curl` + `tar` (1.3 MiB zip). `npm run build` exit 0 (PWA 3 MiB). `npx playwright test` — **17 passed** на свежем `dist/` (2026-08-18). `ECONNREFUSED :8000` в логе preview — нет API, спеки мокают admin; не красный |

Проверка (2026-08-18, A12-audit): `cd frontend && npm run build` (exit 0) + vitest i18n/admin/shared/auth/`client-api-errors` (**107 passed**) + `npx playwright test` (**17 passed**, свежий `dist/`).

### A12-repass (тот же день — формальное vs живое)

| Дыра | Фикс |
|------|------|
| «17 passed» в Playwright **не** покрывает 401/405. Цифра e2e — smoke оболочек, не гейт transport | Покрытие: vitest `client-api-errors` + `QueryListStates` (`unauthorized`, `method_not_allowed`). E2E 401 **не** добавляли (редирект + mock session ломает остальные спеки). Зафиксировано во «Вне очереди» п.5 остаток HTML 4xx |
| `normalizeErrorMessage` на 405/502/traceback подменял тело на RU **без** `code` → QueryErrorAlert на `/admin*` снова RU после «закрытого» A12-audit | `throwCodedHttpFailure`: transport-код только если тело *заменили*. Admin мапит ключ. Patient `formatQueryError` без смены языка. Короткий 5xx с бизнес-текстом **без** выдуманного code |
| Три копии admin-401 (json/form/blob) — дрейф при следующем патче | `redirectAndThrowAdminUnauthorized` + один `throwCodedHttpFailure` |
| `isEmptyClinicDatabaseError`: `msg.includes("клиник")` ловил «нет доступа к клинике» / «поликлиник» → ложный EN empty-db вместо `not_found` | Узкий паттерн `нет ни одной клиник` + `\bno clinics?\b` + code. `AdminReportsPage` больше не дублирует `/клиник\|clinic/i` |
| Нумерация «Вне очереди»: 13 → 15, пункт 14 пропущен; шапка «14 пунктов» врала | Сквозная 1–14 |
| Playwright 17 passed **не** доказывает A12 после правок `client.ts` этой сессии | Vitest transport suites ниже; полный Playwright после этого среза — если менялся бандл UI (здесь — client + reports heuristic, e2e не цепляет) |

Проверка (2026-08-18, A12-repass): `npx tsc -b` exit 0; vitest i18n/admin/shared/auth/`client-api-errors` — **17 files / 110 passed**.

---

## Вне очереди (следующий разговор, не Queue A13)

Владелец без отдельного батча i18n — иначе к этому не вернутся.

1. **Маркетинг / SEO:** Phase 4 + checkout chrome **сделаны**. Sandbox/legal bodies + `founder` ns + FE catalog overlay. Checkout/lead **errors** follow `ui.locale`. SSG нет (ADR-018). SEO TECH — не заявлен. Остаток: API `display_name` без seed overlay. Задачи: Kanban/create/routing/stream colour + details-page chrome закрыты ключами `tasks`.
2. **Founder form after login** (dashboard / queue / leads / MFA) на `founder` ns. Ошибки очереди — `FounderQueryError` (перевод на рендере, без refetch при смене языка).
3. **Patient `/app`:** chrome на `patient` ns (включая loyalty/forms/feed/success). Остаток: `getBookingErrorMessage`, `formatQueryError` fallback, default emoji/voice/signature; имена полей анкет — с API.
4. **`PlatformPricingSection`:** chrome + overlay + entitlement overlay. **Остаток:** Alembic-only DB без seed — RU `display_name`.
5. **`client.ts` HTML 4xx / 502–503 traceback:** `common.errors` (`method_not_allowed`, `html_gateway`, `service_unavailable`, `internal_server_error`). Admin 401 → `ApiErrorWithCode(..., "unauthorized")`. Короткий 5xx с телом API без code — сырой `detail` (R10).
6. **Backend `code: empty_db_no_clinic`:** сейчас 404 + RU `detail` + узкий heuristic. Снять heuristic после кода на API.
7. **Доменные коды** `omni_*` / `rag_*` / `billing_revoked` / booking `slot_unavailable` на `QueryErrorAlert` — экранные ключи, не раздувать `common.errors`.
8. **R14** native HTML `required` / `type=email` — текст браузера ≠ `ui.locale`.
9. **R15** два clinic picker (layout Select + `ClinicSelector`) — не сливать без решения.
10. **Hygiene:** слить `frontend/vite.config.js` в `vite.config.ts` (лимиты PWA уже совпадают). Не в этой сессии: риск сломать Vite resolve на Windows.
11. **Комментарии кода на RU** — не долг перевода (R11).
12. **`chatMessageBodyDisplay`** токен `[Голосовое сообщение]` — протокол данных, не chrome.
13. Перевод `docs/` / user docs / этот roadmap; `git commit` / `git push` (Law 40).
14. **Windows `npx playwright install`:** после 100% zip extract может зависнуть (0-байтный exe). Обход: `curl` zip + `tar -xf` в `%LOCALAPPDATA%\ms-playwright\…`. CI Linux не трогать. Playwright e2e **не** гейтит 401/405 — это vitest.

@LEAD: пункт 1+4 — один разговор про публичный EN; пункт 5 — только если всплывёт HTML-прокси на админке.

---

## Инвентарь страниц `frontend/src/admin/pages/` (51 уникальный файл)

`AdminLoginPage` — redirect, UI-строк нет.

| Батч | Страницы |
|------|----------|
| A1 | `AdminLoginPage` (redirect), поведение `AdminRightsPoliciesPage` locale (copy → A9b) |
| A2 | `SchedulePage`, `AdminBookingsPage`, `AdminWaitlistPage`, `AdminRecallPage`, `AdminDoctorSchedulePage`, `AdminStaffCalendarPage` |
| A3 | `AdminPatientsPage`, `AdminDoctorsPage`, `AdminServicesPage`, `AdminClinicsPage`, `AdminAdministratorsPage`, `AdminStaffCabinetPage` |
| A4 | `AdminTasksPage`, `AdminTaskDetailsPage` |
| A5 | `AdminOmniChatPage`, `AdminOmniChannelsPage`, `AdminOmniVaultPage`, `AdminOmniAiSettingsPage`, `AdminStaffChatPage`, `AdminChatPage`, `AdminChannelsPage` |
| A6 | `AdminSalesPipelinePage`, `AdminMarketingPage`, `AdminRetentionPage`, `AdminLeadsLogPage`, `AdminClientReferencePage` |
| A7 | `AdminFinancePage`, `AdminCommercePage`, `AdminLoyaltyPage`, `AdminPrepaymentPage`, `AdminPaymentGatewayPage`, `AdminDiscountsPage` |
| A8 | `AdminDashboardPage`, `AdminReportsPage`, `AdminAiReportsPage` |
| A9 | `AdminSettingsPage`, `AdminSubscriptionPage`, `AdminEmbedPage`, `AdminRagKbPage`, `AdminDataExportPage`, `AdminAiSettingsPage`, `AdminFormsPage`, `AdminAgreementsPage`, `AdminEmergencyNotificationsPage`, `AdminNotificationPolicyPage`, `AdminStylingPage`, `AdminStickersPage`, `AdminKnowledgePage`, `AdminIntegrationsPage` |
| A9b | `AdminRightsPoliciesPage` (словари) |

Дроверы/сетка едут с батчем экрана. Shared из §0/A0/A1/A2 — не «в конце, если повезёт».

---

## Как кидать в Cursor Queue

1. **A0–A12 уже в коде** (+ A12-audit). Нового блока QUEUE нет. Дальше — нумерованный «Вне очереди», не A13.  
2. Исторические `### QUEUE A*` живут **внутри секций батчей**, не одним блоком в конце файла — **не** запускать повторно.  
3. A9b шёл после A9. Если агент полез в чужой батч — стоп.  
4. «Смешанный EN nav + RU страница» между A1 и A12 **было** ожидаемо; после A12 admin chrome на ключах.  
5. Новый ns: JSON + `index.ts` (`I18N_NAMESPACES` + `resources`) + `i18next.d.ts`. Тесты: `await renderWithI18n`.

Reference: `frontend/src/admin/layouts/AdminLayout.tsx` · `frontend/src/auth/ClinicSignInPage.tsx` · `frontend/src/main.tsx` · `frontend/src/App.tsx` · `docs/artifacts/OSS_PUBLIC_READINESS_PLAN.md`
