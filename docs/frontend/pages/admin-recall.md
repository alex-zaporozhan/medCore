# Admin Recall

## Метаданные

- **Path:** `/admin/recall`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminRecallPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminRecallPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminRecallPage.tsx`<br>`frontend/src/hooks/useAdminRecall.ts ← импорт из frontend/src/admin/pages/AdminRecallPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminRecallPage.tsx`<br>`frontend/src/shared/emptyStateHint.tsx ← импорт из frontend/src/admin/pages/AdminRecallPage.tsx` |
| Строк (сумма по фрагментам) | 1053 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminRecall`, `useAdminRecallAutomations`, `useAdminRecallCampaigns`, `useAdminRecallLogs`, `useAdminRecallSegments`, `useAdminRecallTemplates`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreateRecallAutomation`, `useCreateRecallCampaign`, `useCreateRecallSegment`, `useCreateRecallTemplate`, `useDeleteRecallAutomation`, `useDeleteRecallCampaign`, `useDeleteRecallSegment`, `useDeleteRecallTemplate`, `useMutation`, `useQuery`, `useQueryClient`, `useRunRecallCampaign`, `useUpdateRecallAutomation`, `useUpdateRecallCampaign`, `useUpdateRecallSegment`, `useUpdateRecallTemplate` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 9, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Recall и автоматизации для клиники: вкладки «Сегменты» (фильтры аудитории, превью числа пациентов), «Шаблоны» сообщений, «Кампании» (создание, запуск, удаление), «Автоматизации» (триггеры, в коде задан тип «через N дней после визита»). CRUD через `AdminDrawer` на каждой вкладке.

## Логика и данные

- **Хуки:** семейство `useAdminRecall*` из `frontend/src/hooks/useAdminRecall.ts` (сегменты, шаблоны, кампании, `useRunRecallCampaign`, автоматизации; логи кампаний — эндпоинт `.../recall/logs` в том же модуле при необходимости).
- **Типовые API (`/v1/...`):** префикс `/v1/admin/clinics/{clinicId}/recall/` и ресурсы `segments`, `templates`, `campaigns`, `campaigns/{id}/run`, `automations` (GET, POST, PATCH, DELETE по сценарию).

## RBAC / entitlements / edition

- **fact:** Сегмент `recall` в `SEGMENT_ENTITLEMENT` сопоставлен с ключом **`marketing.attribution`**. При `entitlement_enforced` без этого ключа сегмент блокируется (`isAdminSegmentBlockedByEntitlements`).

## UI-скелет (as-built)

- `ContextBar` с заголовком «Recall / Автоматизации».
- Без выбранной клиники — текст «Выберите клинику».
- Корневой **`Tabs`:** segments, templates, campaigns, automations; внутри таблицы, `EmptyStateHint`, кнопки добавления.

## Инвентарь поверхностей UI (ось H)

- **По одному `AdminDrawer` на вкладку** (сегмент, шаблон, кампания, автоматизация): формы создания/редактирования, `useDisclosure` для открытия.
- **`GlassModal`:** нет на уровне страницы (по текущему проходу).

## Целевой UX (target vs as-built)

- *target:* напоминания и рассылки настраиваются в админке без внешних инструментов.
- *as-built:* четыре вкладки с повторяющимся паттерном таблица плюс drawer.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** автотестов страницы не найдено.

## Gap scan (вторая редакция)

- Один entitlement-ключ с маркетингом (`marketing.attribution`) — при изменении тарифов проверять оба паспорта; дублирование логики drawer между вкладками — кандидат на общий компонент.
