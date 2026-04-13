# Admin Reports

## Метаданные

- **Path:** `/admin/reports`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminReportsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminReportsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminReportsPage.tsx`<br>`frontend/src/hooks/useAdminReports.ts ← импорт из frontend/src/admin/pages/AdminReportsPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminReportsPage.tsx`<br>`frontend/src/shared/emptyStateHint.tsx ← импорт из frontend/src/admin/pages/AdminReportsPage.tsx`<br>… +2 файлов |
| Строк (сумма по фрагментам) | 947 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminReports`, `useAdminReportsDashboard`, `useAdminReportsDashboardAggregate`, `useAdminReportsDashboardByClinics`, `useAdminReportsNoShow`, `useAdminReportsRevenue`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useMarketingAttribution`, `useMarketingAttributionDrillDown`, `useMarketingAttributionSummary`, `useMarketingCampaigns`, `useMarketingInsights`, `useOwnerDashboard`, `useQuery` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 3, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Сводная аналитика клиники: дашборд записей/нагрузки, no-show, выручка, owner-dashboard, блок маркетинговой атрибуции (фильтры по датам, источнику, кампании), AI-insights по клинике. Клик по строке атрибуции открывает **`AdminDrawer`** с drill-down лидов (`useMarketingAttributionDrillDown`, тип `leads`) при enterprise-сборке.

## Логика и данные

- **Хуки:** `useAdminReportsDashboard`, `useAdminReportsNoShow`, `useAdminReportsRevenue`, `useOwnerDashboard` (`useAdminReports.ts`); `useMarketingAttributionSummary`, `useMarketingCampaigns`, `useMarketingInsights`, `useMarketingAttributionDrillDown` (`useMarketingAttribution.ts`); `useAdminClinic`; `isBoxEdition` из `@/config/edition`.
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/clinics/{clinicId}/reports/dashboard?date=&period=`
  - `GET /v1/admin/reports/dashboard-aggregate?...` (агрегат без привязки к клинике в URL — см. хук)
  - `GET /v1/admin/clinics/{clinicId}/reports/no-show?date_from&date_to`
  - `GET /v1/admin/clinics/{clinicId}/reports/revenue?date_from&date_to`
  - `GET /v1/admin/clinics/{clinicId}/reports/owner-dashboard?...`
  - Атрибуция: `GET /v1/admin/attribution/summary?...`, `GET /v1/admin/attribution/drill-down?...`, `GET /v1/admin/attribution/campaigns`, `GET /v1/admin/clinics/{clinicId}/marketing/insights`

## RBAC / entitlements / edition

- **fact:** Сегмент `reports` **не** в `SEGMENT_ENTITLEMENT`.
- **fact (edition):** `showEnterpriseMarketingAnalytics = !isBoxEdition()` — drawer drill-down по атрибуции рендерится только вне box-редакции.

## UI-скелет (as-built)

- `ContextBar`, поля дат, карточки/таблицы метрик, `PageSkeleton` и `QueryErrorAlert` при загрузке и ошибках.
- Таблица атрибуции с кликабельными строками (`data-table-clickable-row`).

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer`:** детализация выбранной строки атрибуции (до 50 элементов списка + подсказка об общем `total`) — только если `showEnterpriseMarketingAnalytics`.
- **GlassModal:** нет.

## Целевой UX (target vs as-built)

- *target:* единый экран отчётов для владельца клиники.
- *as-built:* смесь клинико-специфичных и агрегированных эндпоинтов; часть аналитики завязана на edition.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** тестов страницы не найдено.

## Gap scan (вторая редакция)

- Согласовать с продуктом видимость агрегатного `dashboard-aggregate` vs клинико-специфичного дашборда, чтобы не дублировать смысл в UI.
