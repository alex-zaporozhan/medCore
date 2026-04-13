# Admin Integrations

## Метаданные

- **Path:** `/admin/integrations`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminIntegrationsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminIntegrationsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminIntegrationsPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminIntegrationsPage.tsx`<br>`frontend/src/hooks/useAdminIntegrations.ts ← импорт из frontend/src/admin/pages/AdminIntegrationsPage.tsx`<br>`frontend/src/shared/emptyStateHint.tsx ← импорт из frontend/src/admin/pages/AdminIntegrationsPage.tsx` |
| Строк (сумма по фрагментам) | 280 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminIntegrationSettings1c`, `useAdminIntegrations`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useMutation`, `useQuery`, `useQueryClient`, `useUpdateAdminIntegrationSettings1cMutation` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Карточка настроек интеграции с 1C (URL API и учётные данные, хранение зашифрованным на бэкенде). Информационный блок про CSV-обмен через расписание и отчёты; заглушка-секция Bitrix24 («в следующих версиях»).

## Логика и данные

- **Хуки:** `useAdminClinic`, `useAdminIntegrationSettings1c`, `useUpdateAdminIntegrationSettings1cMutation` (`frontend/src/hooks/useAdminIntegrations.ts`).
- **queryKey:** `queryKeys.integrationSettings1c(clinicId)` (см. `frontend/src/queryKeys.ts`).
- **API:** `GET /v1/admin/clinics/{clinic_id}/integration-settings/1c`; `PUT` с телом `{ api_url, credentials }` (пустой `credentials` — не менять сохранённый ключ, по подсказке в UI).

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для `integrations` ключа нет (**fact**).
- Без клиники — только `ContextBar` и `EmptyStateHint`.

## UI-скелет (as-built)

`ContextBar` → синий `Alert` (CSV) → `AdminSettingsSectionCard` «1C» с полями и кнопкой сохранения → пустая по смыслу карточка «Bitrix24» (только title/description).

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` / `GlassModal` / `Modal`:** нет.

## Целевой UX (target vs as-built)

- *target:* реальные поля Bitrix24 или скрытие секции до готовности API.
- *as-built:* минимальный 1C + текстовый плейсхолдер под Bitrix24.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Локальный `saving1c` дублирует состояние мутации; можно упростить до `save1c.isPending`.
