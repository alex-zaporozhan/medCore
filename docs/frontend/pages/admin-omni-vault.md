# Admin Omni Vault

## Метаданные

- **Path:** `/admin/omni-vault`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminOmniVaultPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminOmniVaultPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminOmniVaultPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminOmniVaultPage.tsx`<br>`frontend/src/shared/ui/EmptyState.tsx ← импорт из frontend/src/admin/pages/AdminOmniVaultPage.tsx`<br>`frontend/src/hooks/useAdminOmniVault.ts ← импорт из frontend/src/admin/pages/AdminOmniVaultPage.tsx` |
| Строк (сумма по фрагментам) | 642 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminOmniVault`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useMutation`, `useOmniVaultBackupStatus`, `useOmniVaultExportPresets`, `useOmniVaultMediaGallery`, `useQuery`, `useQueryClient`, `useRequestOmniVaultBackupMutation` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 3, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Вкладки: медиа-галерея по выбранной клинике (фильтр по типу; в коде `date_from` задаётся как сегодняшняя дата), заглушка «Голосовые», Export Builder с пресетами колонок и кнопками Excel/CSV, Full Backup (запрос задачи и статус с возможной ссылкой скачивания). Клик по карточке медиа открывает детали в боковой панели.

## Логика и данные

- **Хуки:** `useAdminClinic`; `useOmniVaultMediaGallery`, `useOmniVaultExportPresets`, `useRequestOmniVaultBackupMutation`, `useOmniVaultBackupStatus` из `frontend/src/hooks/useAdminOmniVault.ts`; локальные пресеты `OMNI_VAULT_EXPORT_PRESETS`.
- **queryKey:** `queryKeys.omniVault.media`, `exportPresets`, `backup` (зависят от `clinicId`, см. `queryKeys.ts`).
- **API:** `GET /v1/admin/clinics/{clinic_id}/media` с query; `GET /v1/admin/clinics/{clinic_id}/export/presets` (при ошибке — локальные пресеты); `POST /v1/admin/clinics/{clinic_id}/backup/request`; `GET /v1/admin/clinics/{clinic_id}/backup/status`.

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для сегмента `omni-vault` ключа нет (**fact**).
- Box не блокирует сегмент.
- Без `currentClinicId` запросы к API клиники отключены (`enabled` в хуках).

## UI-скелет (as-built)

`ContextBar`, затем `Tabs`: медиа (кнопки фильтра, сетка карточек, скелетоны, пустое состояние), голосовые (`EmptyState`), экспорт (`Grid`, `MultiSelect`, текст превью), бэкап (`Card`).

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer`:** деталь выбранного медиа (изображение по `url`, пациент, канал, дата). Кнопка «Открыть в чате» только закрывает drawer — перехода в omni-chat нет (**gap**).
- **`Modal` / `GlassModal`:** нет.
- **Excel/CSV:** обработчики помечены как TODO, реального `POST` экспорта нет (**gap**).

## Целевой UX (target vs as-built)

- *target:* рабочий экспорт, выбор даты для медиа, голосовая вкладка с данными.
- *as-built:* часть сценариев в статусе заглушки / фаза 5.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Дата выборки медиа зашита на «сегодня», пользователь не меняет её в UI.
