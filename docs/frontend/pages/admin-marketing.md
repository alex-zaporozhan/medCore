# Admin Marketing

## Метаданные

- **Path:** `/admin/marketing`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminMarketingPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminMarketingPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminMarketingPage.tsx`<br>`frontend/src/hooks/useAdminMarketing.ts ← импорт из frontend/src/admin/pages/AdminMarketingPage.tsx`<br>`frontend/src/hooks/useMarketingAttribution.ts ← импорт из frontend/src/admin/pages/AdminMarketingPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminMarketingPage.tsx`<br>… +1 файлов |
| Строк (сумма по фрагментам) | 1013 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminMarketing`, `useAdminPromoPosts`, `useAdminSession`, `useAdminStories`, `useBusinessLexicon`, `useClinics`, `useCreatePromoPost`, `useCreateStory`, `useDeletePromoPost`, `useDeleteStory`, `useMarketingAttribution`, `useMarketingAttributionDrillDown`, `useMarketingAttributionSummary`, `useMarketingCampaigns`, `useMarketingInsights`, `useMutation`, `useQuery`, `useQueryClient`, `useUpdatePromoPost`, `useUpdateStory` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 7, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Контент и аналитика маркетинга клиники: **Посты** (лента PWA), **Сторис** (медиа + порядок), **Атрибуция** (сводка по каналам/кампаниям за период, drill-down лидов/записей/транзакций в `AdminDrawer`). Черновики поста/сторис сохраняются в `sessionStorage` (`POST_DRAFT_KEY` / `STORY_DRAFT_KEY`).

## Логика и данные

- **Хуки:** `useAdminPromoPosts`, `useCreatePromoPost`, `useUpdatePromoPost`, `useDeletePromoPost`, `useAdminStories`, `useCreateStory`, `useUpdateStory`, `useDeleteStory` (`useAdminMarketing.ts`); для атрибуции — `useMarketingAttributionSummary`, `useMarketingAttributionDrillDown`, опционально `useMarketingInsights`, `useMarketingCampaigns` (`useMarketingAttribution.ts`).
- **Типовые API (`/v1/...`):**
  - `GET|POST /v1/admin/clinics/{clinicId}/marketing/posts` · `PATCH|DELETE .../posts/{postId}`
  - `GET|POST /v1/admin/clinics/{clinicId}/marketing/stories` · `PATCH|DELETE .../stories/{storyId}`
  - `GET /v1/admin/attribution/summary?date_from&date_to&...` (хук передаёт `clinicId` в queryKey/`enabled`; в query string на клиенте — даты и опциональные фильтры — фактическая привязка к клинике на стороне API)
  - `GET /v1/admin/attribution/drill-down?...`
  - `GET /v1/admin/attribution/campaigns`
  - `GET /v1/admin/clinics/{clinicId}/marketing/insights`

## RBAC / entitlements / edition

- **fact:** Сегмент `marketing` → ключ **`marketing.attribution`** в `SEGMENT_ENTITLEMENT` (тот же ключ, что у `recall` в карте навигации).

## UI-скелет (as-built)

- Без клиники — подсказка.
- **`Tabs`:** посты | сторис | атрибуция.
- Посты/сторис: таблицы или `EmptyStateHint`, кнопки добавления.
- Атрибуция: `AdminDataTableToolbar` (диапазон дат), таблица ROI, клик по строке открывает drawer.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer`:** создание/редактирование поста; создание/редактирование сторис (**fact:** `Alert` при `saveError` в drawer сторис).
- **`AdminDrawer` детализации атрибуции:** вложенные **`Tabs`** (лиды / записи / транзакции), данные из `useMarketingAttributionDrillDown`.
- **GlassModal:** нет (по текущему проходу).

## Целевой UX (target vs as-built)

- *target:* контент в ленте + измеримость каналов в одном разделе.
- *as-built:* черновики в `sessionStorage` снижают потерю ввода при случайном закрытии вкладки.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** тестов страницы не найдено.

## Gap scan (вторая редакция)

- Общий entitlement-ключ с recall может путать продуктовую политику тарифов — при разделении фич на бэкенде стоит синхронизировать карту `SEGMENT_ENTITLEMENT` и этот паспорт.
