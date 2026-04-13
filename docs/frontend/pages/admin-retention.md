# Admin Retention

## Метаданные

- **Path:** `/admin/retention`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminRetentionPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminRetentionPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminRetentionPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminRetentionPage.tsx`<br>`frontend/src/hooks/useAdminRecall.ts ← импорт из frontend/src/admin/pages/AdminRetentionPage.tsx`<br>`frontend/src/hooks/useAdminRetention.ts ← импорт из frontend/src/admin/pages/AdminRetentionPage.tsx`<br>… +3 файлов |
| Строк (сумма по фрагментам) | 1337 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminRecall`, `useAdminRecallAutomations`, `useAdminRecallCampaigns`, `useAdminRecallLogs`, `useAdminRecallSegments`, `useAdminRecallTemplates`, `useAdminRetention`, `useAdminRetentionCampaignsRoi`, `useAdminRetentionSegments`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreateRecallAutomation`, `useCreateRecallCampaign`, `useCreateRecallSegment`, `useCreateRecallTemplate`, `useDeleteRecallAutomation`, `useDeleteRecallCampaign`, `useDeleteRecallSegment`, `useDeleteRecallTemplate`, `useGenerateRetentionOffers`, `useMutation`, `useQuery`, `useQueryClient`, `useRunRecallCampaign`, `useUpdateRecallAutomation`, `useUpdateRecallCampaign`, `useUpdateRecallSegment`, `useUpdateRecallTemplate` |
| Пути в строках `/v1/...` | `/v1/ai/generate-offers` |
| Вхождения UI | AdminDrawer: 5, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Удержание: сегменты аудитории (те же сущности, что recall), конструктор кампании recall (сегмент + шаблон + название), запрос персональных офферов через `POST /v1/ai/generate-offers`, таблица ROI кампаний по воронке (`GET .../retention/campaigns/roi-summary`).

## Логика и данные

- **Хуки:** `useAdminRetentionSegments`, `useAdminRetentionCampaignsRoi`, `useGenerateRetentionOffers` (`frontend/src/hooks/useAdminRetention.ts`); `useAdminRecallTemplates`, `useCreateRecallCampaign` (`useAdminRecall.ts`); `useAdminClinic`.
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/clinics/{clinicId}/retention/segments` → тело `{ segments: [...] }`
  - `GET /v1/admin/clinics/{clinicId}/retention/campaigns/roi-summary` → массив строк воронки
  - `POST /v1/admin/clinics/{clinicId}/recall/campaigns` — создание кампании
  - `GET /v1/admin/clinics/{clinicId}/recall/templates` — список шаблонов (нужны права/энтайтлмент напоминаний)
  - `POST /v1/ai/generate-offers` — тело `{ segment_id }`, ответ `{ offers: [...] }` (сейчас может быть пустым)

## RBAC / entitlements / edition

- **fact:** Сегмент `retention` → ключ **`retention.bundle`** в `SEGMENT_ENTITLEMENT` (`adminEntitlementNav.ts`). Шаблоны recall зависят от **`marketing.attribution`** и прав на маркетинг.

## UI-скелет (as-built)

- `ContextBar`, кнопка «Создать кампанию».
- **`Tabs`:** «Сегменты», «Waterfall и ROI».
- `AdminDataTableSurface`, `EmptyState`, плейсхолдеры при загрузке.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` «Новая кампания»:** название, сегмент, шаблон; `useCreateRecallCampaign`; ошибка мутации в тексте.
- **`AdminDrawer` «Персональные офферы по сегменту»:** `useGenerateRetentionOffers`, список результатов или пустое состояние.
- **GlassModal / Mantine Modal:** нет.

## Целевой UX (target vs as-built)

- *target:* сегменты → кампании → измеримый ROI и персональные офферы.
- *as-built:* сегменты и ROI по кампаниям из API; создание кампании через recall; генерация офферов вызывает AI-эндпоинт (ответ может быть пустым до подключения модели).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** узких тестов страницы нет; см. RBAC на `retention/segments` в `tests/api/test_admin_rbac_box_cuts.py`.

## Gap scan (вторая редакция)

- Расширить `POST /v1/ai/generate-offers` реальной генерацией; при расхождении энтайтлментов retention vs marketing — выровнять политику доступа к шаблонам recall.
