# Масштаб паспортов страниц SPA и риски (фаза 0)

> **Версия:** 2026-04-10  
> **Связь:** план QA_ARCH «единая документация фронта»; критерии — [`../frontend/PAGE_PASSPORT_CRITERIA.md`](../frontend/PAGE_PASSPORT_CRITERIA.md).

**Якорь перечня страниц для паспортов (SPA):** `ALL_PUBLIC_APP_PATHS` / `buildDerivedPublicAppPaths()` в `frontend/src/routePaths.ts` плюс динамические шаблоны и цепочки из `frontend/src/App.tsx`. Список экранов **не** строить из `src/api/v1/router.py`: для паспорта API-контур — это типовые вызовы из хуков страницы, а не построчное соответствие `include_router`. Скрипт заглушек и проверки: `scripts/gen_frontend_page_passport_stubs.py`; матрица Path → файл: [`../frontend/pages/README.md`](../frontend/pages/README.md).

## Объём маршрутов (оценка)

| Категория | Количество (порядок) | Источник истины |
|-----------|----------------------|-----------------|
| Админ shell (сегменты под `/admin/*`) | **46** | `ADMIN_SHELL_ROUTE_SEGMENTS` в `frontend/src/routePaths.ts`, зеркало в `ADMIN_SHELL_PAGE_BY_SEGMENT` в `frontend/src/App.tsx` |
| Админ дашборд (index) + логин | **2** | `App.tsx`: index → `AdminDashboardPage`, `login` → `ClinicSignInPage` |
| Динамика админки | **1 шаблон** | `/admin/tasks/:taskId` → `AdminTaskDetailsPage` |
| Пациент `/app/*` | **8** (index + 7 сегментов) | `PATIENT_APP_ROUTE_SEGMENTS` + `HomePage` на index |
| Пациент `/c/:clinicSlug/...` | **дублирует** `/app/*` + sign-in | Тот же набор страниц под `AppLayout`, плюс `PatientSignInPage` |
| Маркетинг / публичное | **6+** | `/`, `/pricing`, `/signup`, privacy, terms, `/:clinicSlug/doctors/:doctorSlug` |
| Платформа (основатель) | **4** | login, MFA, dashboard, provision-queue |
| Прочее | **4** | legacy sign-in redirect, `/login` redirect, oauth result, booking success |

**Итого уникальных «логических» паспортов:** порядок **60–75**, если считать `/app/booking` и `/c/x/app/booking` одним паспортом с пометкой двойного монтирования; при раздельном учёте — ближе к верхней границе.

Мастер-список статических path для регрессий: `ALL_PUBLIC_APP_PATHS` в `routePaths.ts`; расширенная матрица: [`FRONTEND_ROUTE_AUDIT_MATRIX.md`](./FRONTEND_ROUTE_AUDIT_MATRIX.md).

## Приоритет зон (v1 паспортов)

1. **P0 — витрина и первый контакт:** лендинг, pricing, signup, patient sign-in chain.
2. **P1 — операционное ядро админки:** dashboard, bookings, patients, omni, tasks, finance (данные + селекты).
3. **P2 — остальные сегменты admin shell** по `ADMIN_SHELL_ROUTE_SEGMENTS` в `frontend/src/routePaths.ts`.
4. **P3 — platform founder**, юридические страницы, публичный профиль врача.

Сегменты админки перечислены в коде: `frontend/src/routePaths.ts` (`ADMIN_SHELL_ROUTE_SEGMENTS`).

## Зависимости от бэкенда

Паспорт страницы **не заменяет** OpenAPI: для полноты цепочки UI↔API нужны актуальные контракты API и манифест [`documentation/API_V1_ROUTER_MANIFEST.md`](../../documentation/API_V1_ROUTER_MANIFEST.md) (контур пользовательской документации — см. [`DOCUMENTATION_POLICY.md`](../../DOCUMENTATION_POLICY.md)). Перечень **React-маршрутов** для паспортов не выводить из агрегатора `router.py` — только из `routePaths.ts` и `App.tsx`, как выше. Расхождения — в [`../architecture/UNRESOLVED_AND_CONFUSION_LOG.md`](../architecture/UNRESOLVED_AND_CONFUSION_LOG.md) при появлении.

## Что входит в v1 vs v2 паспорта

| Версия | Содержание |
|--------|------------|
| **v1** | Path, зона, компонент(ы), назначение, основные хуки и пути API, RBAC/entitlements на уровне UI, скелет UI из кода, явные **fact / gap** |
| **v2** | Целевой премиум UX (target vs as-built), Gap scan второго прохода, тесты (vitest/e2e) |

## Риски («разрушительная» критика)

- **Объём:** полное заполнение всех паспортов с премиум-слоем — много итераций; реалистично вести **спринтами по зонам**.
- **Устаревание:** при изменении `App.tsx` / `routePaths.ts` обновлять [`../product_state/FRONTEND_PASSPORT.md`](../product_state/FRONTEND_PASSPORT.md) и индекс [`../frontend/pages/README.md`](../frontend/pages/README.md).
- **Галлюцинации RAG:** без пометок fact/gap документация подменяет код — см. [`../RAG_CANON.md`](../RAG_CANON.md).

## Волны заполнения паспортов

- **Волна A:** пилоты в [`../frontend/pages/README.md`](../frontend/pages/README.md) с инвентарём поверхностей UI (ось H в [`../frontend/PAGE_PASSPORT_CRITERIA.md`](../frontend/PAGE_PASSPORT_CRITERIA.md)).  
- **Волна B:** маркетинг P0 + `patient-sign-in-chain.md`.  
- **Волна C:** остальные админские сегменты пакетами.
