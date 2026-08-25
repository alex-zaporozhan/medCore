# Канон архитектуры и стиля фронтенда (SPA)

> **Версия:** 2026-04-10  
> **Назначение:** единая навигационная и нормативная страница перед работой с паспортами экранов ([`pages/`](./pages/), [`PAGE_PASSPORT_CRITERIA.md`](./PAGE_PASSPORT_CRITERIA.md)).  
> **Порядок эпиков для агента @QA_ARCH (фазы 0–8) и скрипт паспортов:** [`MASTER_FRONTEND_EXECUTION_PLAN.md`](./MASTER_FRONTEND_EXECUTION_PLAN.md).  
> **Источник истины по фактам:** код (`frontend/src/`) и [`../product_state/FRONTEND_PASSPORT.md`](../product_state/FRONTEND_PASSPORT.md).  
> **Слои, трассируемость, чеклист PR:** [`FRONTEND_ENGINEERING_CONVENTIONS.md`](./FRONTEND_ENGINEERING_CONVENTIONS.md).

## 0. Макро / микро / премиум (как читать качество UI)

- **Макро:** иерархия экрана (контекст → первичное действие → вторичное), соответствие зоне продукта (маркетинг vs операционный shell), навигация без тупиков. Рубрика и матрица UI↔API: [`../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md`](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md).
- **Микро:** состояния загрузки/пусто/ошибка, подсказки одной строкой, плотность таблиц, фокус и доступность базового уровня. Нормы компонентов: [`../TECH_PASSPORT_FRONTEND_UI_LOGIC.md`](../TECH_PASSPORT_FRONTEND_UI_LOGIC.md).
- **Премиум (85+):** визуальная система Swiss Slate / Ink, токены, календарь, модалки расписания — [`../design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md`](../design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md); **где в коде править** — [`../design/DESIGN_CODE_MAP.md`](../design/DESIGN_CODE_MAP.md), [`../design/DESIGN_COMPONENT_MAPPING.md`](../design/DESIGN_COMPONENT_MAPPING.md). Не подменяет базовый `theme.ts` без решения продукта.

## 1. Зоны продукта и оболочки

| Зона | URL (паттерн) | Layout / guard | Код |
|------|----------------|----------------|-----|
| Маркетинг | `/`, `/pricing`, `/signup`, юридические | Без админской оболочки | `App.tsx`, `marketing/pages/*` |
| Платформа (основатель) | `/platform/login`, `/platform/login/mfa`, `/platform/*` | `PlatformFounderLayout` для защищённых веток | `marketing/pages/Platform*`, `marketing/layouts/PlatformFounderLayout.tsx` |
| Админ ERP | `/admin/login`, `/admin`, `/admin/<segment>` | `AdminAuthGuard` → `AdminClinicProvider` → `AdminLayout` | `admin/layouts/AdminLayout.tsx`, `AdminAuthGuard.tsx` |
| Пациент (PWA) | `/app/*`, зеркало `/c/:clinicSlug/app/*` | `PatientAuthProvider` + `AppLayout` | `app/layouts/AppLayout.tsx` |
| Вход пациента по slug | `/c/:clinicSlug/sign-in` | `PatientAuthProvider` на вложенных маршрутах приложения | `PatientSignInPage`, `PatientEntryBoundary` |
| Публичный профиль врача | `/:clinicSlug/doctors/:doctorSlug` | Без shell | `PublicDoctorProfilePage` |

Сегменты админского shell и пациентского приложения — **`ADMIN_SHELL_ROUTE_SEGMENTS`**, **`PATIENT_APP_ROUTE_SEGMENTS`** в `frontend/src/routePaths.ts`; соответствие страницам — словари в `frontend/src/App.tsx`.

## 2. Дизайн-токены и тема

**Без дублирования:** нормы Mantine, CSS-переменных и дисциплина `AdminDrawer` — в [`UI_THEME.md`](./UI_THEME.md). Таблица «какой документ дизайна → какой файл в репозитории» (включая `AdminLayout`, календарь, entity drawers) — в [`../design/DESIGN_CODE_MAP.md`](../design/DESIGN_CODE_MAP.md). Оба читать вместе; расхождение между ними — дефект документации.

- **Обязательный слой:** `frontend/src/theme.ts`, `frontend/src/index.css`, семантика [`SEMANTIC`](../TECH_PASSPORT_FRONTEND_UI_LOGIC.md) в `shared/semanticUi` (как в техпаспорте UI).
- **Канон текстов и Mantine:** [`UI_THEME.md`](./UI_THEME.md).
- **Карта «док дизайна → файл кода»:** [`../design/DESIGN_CODE_MAP.md`](../design/DESIGN_CODE_MAP.md).
- **Опциональный слой 85+:** JSON и playbook в [`../design/`](../design/) (например `DESIGN_TOKENS_85_PLUS.json`) — не подменяет базовую тему без явного решения продукта.

## 3. Компонентные правила

- Правые панели деталей в админке — **`AdminDrawer`** из `@/shared/ui`, не «голый» `Drawer` из Mantine (ESLint: `frontend/eslint-restricted-ui-imports.mjs`, тест `adminNoRawMantineDrawer`).
- Overlay-поверхности админ-shell (`GlassModal`, `AdminDrawer`, сырой `Modal` в calendar/Ask AI) **не** ставят `lockScroll` на `document.body`: иначе `pointer-events: none` глушит клики по navbar. Контракт: `ADMIN_NAV_SAFE_MODAL_PROPS` + inset overlay `SHELL_OVERLAY_PROPS` (`shellPanelStyles.ts`). `trapFocus` остаётся включённым (клавиатура в диалоге; мышь по navbar — да).
- Карточки списков и тулбары — паттерны `data-table-card`, `data-toolbar-card` и т.п., как в [`../TECH_PASSPORT_FRONTEND_UI_LOGIC.md`](../TECH_PASSPORT_FRONTEND_UI_LOGIC.md).
- Модалки vs drawer: критерии в том же техпаспорте (подтверждение, форма, контекст).

## 4. Данные и состояние

- HTTP: `frontend/src/api/client.ts` (`API_BASE`, Bearer, ключи `localStorage` — см. паспорт фронта §7).
- Серверное состояние: **TanStack Query**; ключи — `frontend/src/queryKeys.ts` и доменные хуки `frontend/src/hooks/`.
- **Анти-паттерн:** запрос, зависящий от параметра, который сам блокируется без справочника (пример «зарплата без списка врачей») — см. §8 [`../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md`](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md). Инвалидация после мутаций должна быть явной и согласованной с ключами.

## 5. RBAC, edition, entitlements (UI)

- **Box edition:** `frontend/src/config/edition.ts` — `isAdminSegmentBlockedInBox` (например скрытие `retention`, `sales`).
- **Entitlements:** `adminShellSegmentEntitlementKey`, `isAdminSegmentBlockedByEntitlements` + сессия админа (`useAdminSession`) в `AdminShellSegmentPage`.
- Сервер остаётся источником истины: 403 возможен при рассинхроне `VITE_EDITION` и бэкенд `EDITION`.

## 6. Как читать паспорт страницы

Каждый файл в [`pages/`](./pages/) (шаблон — [`pages/README.md`](./pages/README.md)) должен содержать кратко:

1. **Метаданные:** path, зона, компонент в `App.tsx`, путь к файлу страницы.  
2. **Назначение** — один абзац.  
3. **Данные:** хуки, `queryKey` при необходимости, пути `/api/v1/...`, мутации и инвалидация.  
4. **RBAC / entitlements / edition** — что режет UI.  
5. **UI-скелет (as-built)** — layout, вкладки, таблицы, drawer; без выдуманных цветов.  
6. **Инвентарь поверхностей UI** — каждый значимый Drawer/Modal/Menu/Stepper/Alert (см. [`PAGE_PASSPORT_CRITERIA.md`](./PAGE_PASSPORT_CRITERIA.md)).  
7. **Целевой UX** — отдельно, пометка *target* vs *as-built*.  
8. **Копирайт** — отсылка к [`../COPY_STYLE_POLICY_RU.md`](../COPY_STYLE_POLICY_RU.md).  
9. **Тесты** — vitest/e2e при наличии.  
10. **Gap scan** — второй проход.

## 7. Связанные документы

- Инженерная дисциплина SPA: [`FRONTEND_ENGINEERING_CONVENTIONS.md`](./FRONTEND_ENGINEERING_CONVENTIONS.md)  
- Рубрика Enterprise UI: [`../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md`](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md)  
- Маршруты и оболочки (архитектура): [`../architecture/frontend/routing_and_shells.md`](../architecture/frontend/routing_and_shells.md)  
- Масштаб паспортов и риски: [`../review/07_FRONTEND_PAGE_PASSPORT_SCOPE_AND_RISKS.md`](../review/07_FRONTEND_PAGE_PASSPORT_SCOPE_AND_RISKS.md)
