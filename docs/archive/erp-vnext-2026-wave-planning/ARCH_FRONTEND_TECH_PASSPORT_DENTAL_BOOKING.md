# Техпаспорт фронтенда: Dental Booking (Business OS)

> **Репозиторий:** `dental_booking` · **Корень UI:** `frontend/`  
> **Назначение:** единая точка правды для маршрутов, зон, стека и слоя данных. Поведение экранов (Drawer, таблицы, сущности) — в `../../TECH_PASSPORT_FRONTEND_UI_LOGIC.md`. Визуал лендинга — в `../../TEMPLATE_DESIGN_UX.md`.

---

## 1. Стек и сборка

| Компонент | Версия / выбор |
|-----------|----------------|
| Сборка | Vite 6 |
| Runtime | React 18.3 + TypeScript 5.6 |
| UI | Mantine 7 (`@mantine/core`, `@mantine/hooks`, `@mantine/spotlight`) |
| Данные | TanStack Query 5 |
| Маршруты | React Router 6 (`createBrowserRouter`) |
| DnD | `@dnd-kit/core`, `@dnd-kit/utilities` |
| Иконки | `@tabler/icons-react` |
| Даты | Day.js |
| PWA | `vite-plugin-pwa` (см. `frontend/vite.config.ts`) |

**Команды:** `npm run dev`, `npm run build`, `npm test` (Vitest).

**Точка входа:** `frontend/src/main.tsx` — порядок импорта: стили Mantine первыми, затем провайдеры (Mantine, Query, Router). Роутер объявлен в `frontend/src/App.tsx` (`RouterProvider`); в тестах тот же порядок обёрток — `frontend/src/test-utils.tsx` (`renderWithProviders`).

**Трассируемость (закрытие фаз 0–1, @QA_ARCH):** сверка маршрутов §2 с `App.tsx`, гейты `npm test` / `npm run build` — `./ARCH_FRONTEND_TECH_PASSPORT_DEV_IMPLEMENTATION_PLAN.md` (блок «Статус закрытия фаз»).

**Тема:** `frontend/src/theme.ts` · **Глобальные токены:** `frontend/src/index.css` (`:root`).

**Визуальный канон (Midnight & Graphite, SaaS «инструмент»):** `./ARCH_FRONTEND_DESIGN_SYSTEM_MIDNIGHT.md` — палитра, токены, навигация админки, экономия внимания на плотных панелях (в т.ч. Omni Chat), E2E-устойчивость.

---

## 2. Зоны приложения и маршруты

Источник кода: дерево маршрутов — `frontend/src/App.tsx` (дочерние маршруты админки и пациента строятся из сегментов `ADMIN_SHELL_ROUTE_SEGMENTS` / `PATIENT_APP_ROUTE_SEGMENTS` в `frontend/src/routePaths.ts` и таблиц страниц в `App.tsx`). Канонические path (ссылки, guard’ы, навигация, редиректы при 401 в `client.ts`) — `ROUTE_PATHS` в том же файле; нормализация сравнения path (в т.ч. trailing slash для `/login`) — `frontend/src/routePathUtils.ts`. При изменении публичных маршрутов обновлять §2, `routePaths.ts` и тест `src/__tests__/routePaths.test.ts` в одном merge.

### 2.1. Маркетинг (витрина)

| Path | Назначение |
|------|------------|
| `/` | Лендинг (`LandingPage` inline в `App.tsx`) |

Канон вёрстки: `../../TEMPLATE_DESIGN_UX.md`.

### 2.2. Админка

Базовый префикс: `/admin`. Обертки: `AdminAuthGuard` → при успешной авторизации `AdminClinicProvider` + `AdminLayout`.

| Path | Страница (файл) |
|------|-----------------|
| `/admin/login` | `AdminLoginPage` |
| `/admin` | `AdminDashboardPage` |
| `/admin/clinics` | `AdminClinicsPage` |
| `/admin/services` | `AdminServicesPage` |
| `/admin/schedule` | `SchedulePage` |
| `/admin/tasks` | `AdminTasksPage` |
| `/admin/bookings` | `AdminBookingsPage` |
| `/admin/prepayment` | `AdminPrepaymentPage` |
| `/admin/waitlist` | `AdminWaitlistPage` |
| `/admin/recall` | `AdminRecallPage` |
| `/admin/marketing` | `AdminMarketingPage` |
| `/admin/retention` | `AdminRetentionPage` |
| `/admin/sales` | `AdminSalesPipelinePage` |
| `/admin/attention` | `AdminAttentionFeedPage` |
| `/admin/reports` | `AdminReportsPage` |
| `/admin/finance` | `AdminFinancePage` |
| `/admin/loyalty` | `AdminLoyaltyPage` |
| `/admin/forms` | `AdminFormsPage` |
| `/admin/doctors` | `AdminDoctorsPage` |
| `/admin/doctor-schedule` | `AdminDoctorSchedulePage` |
| `/admin/patients` | `AdminPatientsPage` |
| `/admin/omni-chat` | `AdminOmniChatPage` |
| `/admin/omni-channels` | `AdminOmniChannelsPage` |
| `/admin/omni-ai-settings` | `AdminOmniAiSettingsPage` |
| `/admin/channels` | `AdminChannelsPage` |
| `/admin/integrations` | `AdminIntegrationsPage` |
| `/admin/omni-vault` | `AdminOmniVaultPage` |
| `/admin/styling` | `AdminStylingPage` |
| `/admin/stickers` | `AdminStickersPage` |
| `/admin/settings` | `AdminSettingsPage` |
| `/admin/administrators` | `AdminAdministratorsPage` |
| `/admin/payment-gateway` | `AdminPaymentGatewayPage` |
| `/admin/client-reference` | `AdminClientReferencePage` |
| `/admin/discounts` | `AdminDiscountsPage` |
| `/admin/notification-policy` | `AdminNotificationPolicyPage` |
| `/admin/agreements` | `AdminAgreementsPage` |

Лейаут: `frontend/src/admin/layouts/AdminLayout.tsx`.

### 2.2.1. Omni Chat (`/admin/omni-chat`) — плотность и два «сайдбара»

Решения **только для этого маршрута** (не глобальная смена лейаута всей админки):

| Решение | Файл / механизм |
|---------|-----------------|
| Ширина контента | `AdminLayout`: если `location.pathname` начинается с `ROUTE_PATHS.admin.omniChat` — `Container fluid` и обёртка-`Paper` с `p="sm"` вместо `size="xl"` и `p="md"`, чтобы основная зона использовала ширину при **свёрнутом левом** меню без лишних полей. |
| Сетка 3 колонки | `frontend/src/components/layout/ThreeColumnLayout.tsx`, пресет **`omni-inspector`**: узкий inbox слева (`minmax` + cap по `vw`), центр на `minmax(0,1fr)`, справа инспектор с `minmax` по ширине; проп **`omniRightCollapsed`** — третья колонка фиксирована **56px** (вертикальная рейка иконок). |
| Правая панель «Рабочий центр» | Сворачивание в рейку иконок (аналог идеи схлопнутого sidebar): быстрые ссылки CRM / Расписание / Задачи + переключение вкладок Клиент / Анкеты / Таймлайн / AI; состояние в **`localStorage`** (`admin_omni_inspector_collapsed`); вкладки **`Tabs`** — контролируемые (`inspectorTab` в `AdminOmniChatPage`). |
| Горячие клавиши | `AdminOmniChatPage` (`useHotkeys`): `mod+J` — фокус поля поиска диалогов; `mod+Enter` — отправить сообщение; `Escape` — закрыть боковые Drawer (форма / задача); **`mod+shift+l`** — переключить свёрнутость **правого** инспектора. По умолчанию хоткеи **не срабатывают** в `INPUT` / `TEXTAREA` / `SELECT`. |
| Список диалогов (inbox) | Превью строки: ФИО (`size="sm"`) и телефон (`size="xs"`) визуально **крупнее** метастроки статуса; метаданные одной строкой (`fz` 9), без «бейджевого» второго ряда; сырой статус API (**OPEN**, **CLOSED**, …) с **`title`**-пояснением (OPEN = диалог активен, можно обмениваться сообщениями); обрезка длинных имён (`truncate`, `minWidth: 0` на цепочке flex/grid); выделение выбранного чата нейтральное (фон + `var(--divider)` + вертикальный акцент), не «primary-заливка» — см. `ARCH_FRONTEND_DESIGN_SYSTEM_MIDNIGHT.md` §5.1. |

### 2.3. Пациент (PWA / веб-приложение)

Префикс: `/app`, обертка `PatientAuthProvider` + `AppLayout`.

| Path | Страница |
|------|----------|
| `/app` | `HomePage` |
| `/app/feed` | `FeedPage` |
| `/app/booking` | `BookingWizardPage` |
| `/app/history` | `HistoryPage` |
| `/app/loyalty` | `LoyaltyPage` |
| `/app/forms` | `FormsPage` |
| `/app/chat` | `ChatPage` |
| `/app/profile` | `ProfilePage` |

### 2.4. Прочее

| Path | Назначение |
|------|------------|
| `/login` | Вход пациента (`LoginPage`) |
| `/oauth/result` | OAuth callback (`OAuthResultPage`) |
| `/booking/success` | Успех записи (`BookingSuccessPage`, вне `/app`) |

---

## 3. API (обёртка)

- **Файл:** `frontend/src/api/client.ts`
- **Базовый путь:** `API_BASE` / `"/api"` (относительно origin; в dev проксируется Vite на бэкенд — `vite.config.ts`)
- **Авторизация:** Bearer из `localStorage` — единый реестр ключей `API_STORAGE_KEYS` (админ / пациент / id / `admin_clinic_id`); контекст `PatientAuthContext` использует те же ключи, что и клиент (§3.2 техплана).
- **Корреляция:** на каждый исходящий запрос выставляется заголовок **`X-Request-Id`** (UUID или fallback), если вызывающий код не передал свой — для сопоставления с логами API/ingress при инцидентах.
- **Ошибки:** разбор тела FastAPI (`parseFastApiErrorBody`), в т.ч. **`detail` как массив** (422 validation); при необходимости — верхнеуровневое `message`. `ApiErrorWithCode` (`name: "ApiErrorWithCode"`, поля `code` / `traceId` / `details`); типы — `ApiErrorResponseBody` в `types.ts`. При **401** пациентской сессии: `shouldClearPatientSessionOn401` — для `/v1/patient/*` только при признаке сессии (Bearer в запросе **или** токен в `localStorage`); для `/v1/payments*` при отправленном Bearer; иначе совпадение `resolvedToken` с `getPatientToken()` для эндпоинтов с тем же JWT вне перечисленных путей. Далее — очистка пациентских ключей и редирект на `/login`, кроме уже открытой страницы входа (`isPatientLoginPath` в `routePathUtils.ts`). **Сопровождение:** новый пациентский маршрут с JWT вне `/v1/patient/` и без префикса `/v1/payments` — обновить `shouldClearPatientSessionOn401` в `client.ts` (или согласовать контракт с бэкендом).
- **Типы DTO:** `frontend/src/api/types.ts` (и локальные типы рядом с фичами при необходимости)

**Прод-база и масштаб (фронт + мост):** `./ARCH_FRONTEND_ENTERPRISE_BASELINE.md`. Отказоустойчивость бэкенда/БД/очередей — отдельные треки (в т.ч. `QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER.md`).

Детальные контракты эндпоинтов — в `./ARCH_DEV_*.md` и OpenAPI/роутерах бэкенда (`src/api/v1/`).

---

## 4. Структура `frontend/src/`

```
frontend/src/
├── main.tsx
├── App.tsx
├── routePaths.ts    # канон §2: ROUTE_PATHS, сегменты shell, buildDerivedAllTechPassportPaths
├── routePathUtils.ts # normalizePathname, matchesPatternPath, isPatientLoginPath / isAdminLoginPath
├── queryKeys.ts     # фабрика ключей TanStack Query (§5)
├── theme.ts
├── index.css
├── api/              # client.ts, types.ts
├── hooks/            # TanStack Query хуки по доменам
├── contexts/         # AdminClinic, PatientAuth, …
├── admin/
│   ├── layouts/
│   ├── pages/
│   └── AdminAuthGuard.tsx
├── app/
│   ├── layouts/
│   └── pages/
└── shared/           # UI-переиспользование, ErrorBoundary, утилиты (`shared/index.ts` — баррель; `@/shared`)
```

**Баррели (фаза 4 плана реализации):** публичные точки входа — `hooks/index.ts` (доменные хуки из всех `use*.ts` в каталоге; публичные типы домена — `export type` в конце того же файла, импорт из `@/hooks`), `contexts/index.ts` (пациент и админ-клиника **раздельно**), `shared/index.ts` и `shared/ui/index.ts`. Регресс «каждый `use*.ts` подключён в баррель» — `frontend/src/hooks/__tests__/hooksBarrelParity.test.ts`.

Тесты рядом с кодом: `**/__tests__/**/*.test.tsx`, Vitest + Testing Library.

---

## 5. Данные (TanStack Query)

- Все запросы к API — через хуки в `frontend/src/hooks/` (или согласованное место фичи), не напрямую из компонентов без крайней нужды.
- **Ключи запросов:** фабрика `frontend/src/queryKeys.ts` — единые кортежи для списков/фильтров (клиника, статусы) и префиксной инвалидации мутаций; хуки импортируют `queryKeys`, чтобы не разъезжались строки с `invalidateQueries`. В том числе: CRM (`queryKeys.crm.*` в `useCrmLeads.ts`), настройки AI клиники и глобальный статус AI (`queryKeys.adminAi.*`, `useAdminAiSettings.ts`).
- Мутации: `invalidateQueries`; для DnD и смены статусов — по возможности optimistic update (`onMutate` / rollback / `onSettled`). Пример: `useUpdateAdminTaskStatusMutation` в `useAdminTasks.ts`, `useUpdateLeadStage` в `useCrmLeads.ts`.
- Исключения без эпика: разовый транспорт в `AdminLoginPage` (логин), guard/layout (`getAdminToken`, `clearAdminToken` и т.п.).
- Регресс ключей: `frontend/src/__tests__/queryKeys.test.ts` (минимальная стабильность кортежей для CRM/задач/AI).

---

## 6. UI-каноны (куда смотреть)

| Тема | Документ |
|------|----------|
| Поведение админки и PWA (Drawer, таблицы, сущности) | `../../TECH_PASSPORT_FRONTEND_UI_LOGIC.md` |
| **Omni Chat** — сетка, плотность inbox, схлопывание правого инспектора, хоткеи | §2.2.1 этого файла; `./ARCH_FRONTEND_DESIGN_SYSTEM_MIDNIGHT.md` §5.1 |
| **Оболочка правых панелей админки** (`AdminDrawer`, `shellPanelStyles`, миграция с Mantine `Drawer`; фазы B+ — меню/IA отдельно) | `./ARCH_FRONTEND_ADMIN_SHELL_DRAWER_2026.md` |
| Чеклисты страниц и приёмка | `../../DOMAIN_STANDARDS.md` |
| Маркетинг, hero, glass, производительность motion | `../../TEMPLATE_DESIGN_UX.md` |
| Два визуальных контура, роль @FRONTEND | `../../ROLE_FRONTEND.md` |
| NFR и зрелость | `../../ARCHITECTURE_EXCELLENCE_PASSPORT.md` |

**Факт в коде (фаза A оболочки, план реализации §6):** детальные панели справа — `frontend/src/shared/ui/AdminDrawer.tsx` (дефолты оверлея и «glass»-контента); общие токены с центральными модалками — `shellPanelStyles.ts` + `GlassModal.tsx`. Новые правые формы с таблиц — через `AdminDrawer`, не через «голый» Mantine `Drawer`, без эпика на отклонение.

**§11 NFR (четыре состояния списков/ошибок запросов):** `formatQueryError` в `frontend/src/shared/errors.ts`; `QueryErrorAlert` и `QueryListStates` в `frontend/src/shared/ui/QueryListStates.tsx`; типовые экраны админки и **пациентской зоны** (`frontend/src/app/pages/*`: лента, домашняя, лояльность, история, чат, анкеты, вход) переведены с «красного текста» на `QueryErrorAlert` / Mantine `Alert`; глобальный сбой рендера — `Alert` в `frontend/src/shared/ErrorBoundary.tsx`; контроль регрессии — ESLint `frontend/eslint.config.mjs` (запрет `Drawer` из `@mantine/core` в `src/admin/**`), тест `frontend/src/__tests__/adminNoRawMantineDrawer.test.ts`, Vitest `QueryListStates.test.tsx`.

---

## 7. Что не менять без эпика

- Префикс API `/api` и семантика токенов в `client.ts` без согласования с бэкендом и деплоем.
- Разделение зон `/admin` / `/app` и guard’ов авторизации.
- Замена Mantine на другой UI-kit без версионирования и плана отката (`ROLE_FRONTEND`).

**Регрессия в коде (фаза 7 плана):** `frontend/src/__tests__/techPassportSection7.test.ts` (префикс API, ключи `localStorage`, порядок зон в `App.tsx`, прокси `/api` в `vite.config.ts`); ESLint — `frontend/eslint.config.mjs` + `frontend/eslint-restricted-ui-imports.mjs` (параллельные UI-kit и сырой Mantine `Drawer` в админке). CI: `.github/workflows/frontend-ci.yml`.

---

## 8. Связанные артефакты в `./`

- **План реализации по фазам (LEAD → DEV, приёмка @QA_ARCH):** `ARCH_FRONTEND_TECH_PASSPORT_DEV_IMPLEMENTATION_PLAN.md` — гейты, DoD PR, трассируемость с `DOMAIN_STANDARDS` и §11 NFR-фронта; не заменяет этот техпаспорт, детализирует исполнение §1–§8. **Статус (2026-03):** фазы **0–7** плана — **закрыты**; доработки API — техпаспорт **v1.5.3** (§3); структура §4 и баррели — **v1.5.4**; данные TanStack Query §5 — **v1.5.5–v1.5.6**; план **v1.6.1** … **v1.6.7** (в т.ч. фаза 7 §7, CI фронта). **Дополнение (2026-03):** канон Omni Chat — этот техпаспорт **§2.2.1**, план **v1.6.9** (не новая фаза, трассируемость документов).
- **Базовая планка прод/enterprise (маршруты, мост, Query, корреляция):** `ARCH_FRONTEND_ENTERPRISE_BASELINE.md`
- **Фронт и программа 8.5+ (отложенные эпики, стыковка с неделями):** `ARCH_FRONTEND_85_PLUS_ALIGNMENT.md` (v1.4: §6–§8 перформанс «на потом», в т.ч. доп. таблица §8) · трекер: `QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER.md` §8 (выжимка) · `archive/QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER.md` (полная программа)
- Gaps и дорожные карты UI: `FRONTEND_GAPS_*.md`, `UX_FLOWS_AND_GAPS_NEXT.md`
- Задачи по доменам: `ARCH_DEV_*_TASKS.md`
- **Сводный исполнительный промпт по бэклогу «на потом» (waves, OBS/ERP/и т.д.):** `DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md` + инвентаризация `QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md` — **отдельный трек** от оболочки админки; не подменяет этот техпаспорт.
- **Фаза A оболочки админки:** чеклист и список файлов — `ARCH_FRONTEND_ADMIN_SHELL_DRAWER_2026.md` (§4–§6, §10); после реализации — один абзац-правило в этом файле (§6 или отдельный подпункт §3 при необходимости).

*Версия паспорта: **1.5.11** · синхронизировать с `App.tsx` и `routePaths.ts` при добавлении маршрутов; **v1.5.11** — §2.2.1: Omni Chat (`/admin/omni-chat`) — `Container fluid`, `ThreeColumnLayout` + `omniRightCollapsed`, инспектор и хоткей `mod+shift+l`, канон inbox; **v1.5.10** — §7: регрессия `techPassportSection7.test.ts`, ESLint параллельных UI-kit, CI `frontend-ci.yml`; **v1.5.9** — §11: пациентская зона + `ErrorBoundary`; **v1.5.8** — §11: `QueryListStates`, `formatQueryError`, ESLint admin `Drawer`; **v1.5.7** — §6: `AdminDrawer` + `shellPanelStyles`, единый оверлей с `GlassModal`; v1.5.6 — §5: CRM/adminAi в `queryKeys`, `useAdminAiSettings`, тест `queryKeys.test.ts`; v1.5.5 — §5: `queryKeys.ts`, доменные хуки и инвалидация мутаций; v1.5.4 — §4: баррели `hooks/index.ts`, `contexts/index.ts`, `shared/index.ts`; v1.5.3 — доработка @QA_ARCH: 422 `detail[]`, сужение 401 по `/v1/patient/*`, `ApiErrorWithCode.name`, правило сопровождения `shouldClearPatientSessionOn401`; v1.5.2 — фаза 3 API-слоя; v1.5.1 — ссылка в §8 на `ARCH_FRONTEND_85_PLUS_ALIGNMENT.md` и §8 трекера 8W. Документы артефактов (`ENTERPRISE_BASELINE`, `ALIGNMENT`, `QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER` §8) — отметка «сделано» по базе фронта/моста (2026-03).*
