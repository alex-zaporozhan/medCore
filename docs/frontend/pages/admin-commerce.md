# Admin Commerce

## Метаданные

- **Path:** `/admin/commerce`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminCommercePage`
- **Файл страницы:** `frontend/src/admin/pages/AdminCommercePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminCommercePage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/admin/pages/AdminCommercePage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminCommercePage.tsx`<br>`frontend/src/hooks/useAdminSession.ts ← импорт из frontend/src/admin/pages/AdminCommercePage.tsx` |
| Строк (сумма по фрагментам) | 1956 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useQuery` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/admin/auth/session`, `/v1/admin/clinics/{clinic_id}/commerce/nomenclature/import-spec`, `/v1/admin/clinics/{clinic_id}/commerce/stock-locations/{location_id}/balances/import-spec`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 2, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Управление сетевой торговлей клиники: точки продаж (stock locations), номенклатура, остатки по точке, движения товаров, импорт CSV, журнал импортов и сводка по организации (read-model «сеть»). Данные грузятся и мутируют через `fetch` + Bearer, без React Query на странице.

## Логика и данные

- **Хуки:** `useAdminSession`, `useAdminClinic`; локальный `useState` + `useCallback` для загрузки и форм.
- **queryKey / мутации:** нет TanStack Query на странице; инвалидации кэша не используются.
- **API (типовые `/v1/...`):**
  - `GET /v1/admin/clinics/{clinic_id}/commerce/overview`
  - `GET /v1/admin/clinics/{clinic_id}/commerce/stock-locations` · `POST` · `PATCH` · `DELETE` по id
  - `GET /v1/admin/clinics/{clinic_id}/commerce/nomenclature` · `POST` · `PATCH` · `DELETE` по id · `POST .../import-csv`
  - `GET /v1/admin/clinics/{clinic_id}/commerce/movements` · `POST` · `GET .../movements/{doc_id}` (детализация)
  - `GET /v1/admin/clinics/{clinic_id}/commerce/stock-locations/{location_id}/balances` · `PATCH .../balances/{item_id}` · `POST .../balances/import-csv`
  - `GET /v1/admin/organization/commerce/network-overview`
  - `GET /v1/admin/clinics/{clinic_id}/commerce/import-jobs?limit=30`
  - В UI есть подсказки путей `.../balances/import-spec` и `.../nomenclature/import-spec` (документация формата).

## RBAC / entitlements / edition

- **Entitlement (нав + сервер):** `commerce.store_network` — см. `frontend/src/shared/adminEntitlementNav.ts`; при отказе бэкенда страница показывает `Alert` с текстом про `entitlement_required`.
- **Box:** сегмент `commerce` в `BOX_DISALLOWED_ADMIN_SEGMENTS` (`frontend/src/config/edition.ts`) — в редакции Box пункт скрыт в сайдбаре; прямой заход возможен только если маршрут не заблокирован иначе.
- **Организация:** без `organization_id` в сессии — жёлтый `Alert` «Нет организации».

## UI-скелет (as-built)

`Stack` → `ContextBar` («Магазин (Commerce)») → блоки `AdminSettingsSectionCard`: сводка, журнал импортов, сеть организации (таблица по клиникам), далее таблицы/формы точек, номенклатуры, остатков, движений, `FileInput` для CSV, чекбоксы/кнопки сохранения. Ошибки — `Alert` (entitlement / общая).

## Инвентарь поверхностей UI (ось H)

- **`Modal` (Mantine):** деталь движения (`movModalOpen`); редактирование номенклатуры (`nomModalOpen`). Закрытие сбрасывает состояние; загрузка детали движения — локальный `movDetailLoading`.
- **`AdminDrawer` / `GlassModal`:** на странице нет.
- **Прочее:** `Checkbox`, `NumberInput`, `Select`, `FileInput`, `Table`, `Code` для путей API.

## Целевой UX (target vs as-built)

- *target:* единый слой данных (хуки/React Query), явные состояния loading/error по сущностям, `AdminDrawer` для длинных форм при необходимости.
- *as-built:* монолитный `fetch` + ручной `load`; два `Modal`; сильная связка с `currentClinicId` и токеном.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest/e2e под страницу не найдено (**gap** для регрессии CSV/движений).

## Gap scan (вторая редакция)

- Нет React Query: дублирование логики загрузки, сложнее отмена/повтор.
- Импорт и движения — много ручного UI без пошагового wizard.
- Покрытие тестами отсутствует.
