# Admin Services

## Метаданные

- **Path:** `/admin/services`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminServicesPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminServicesPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminServicesPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminServicesPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminServicesPage.tsx`<br>`frontend/src/admin/components/entity/ServiceEntityDrawer.tsx ← импорт из frontend/src/admin/pages/AdminServicesPage.tsx`<br>… +1 файлов |
| Строк (сумма по фрагментам) | 1418 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminClinicServices`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreateAdminClinicService`, `useDeleteAdminClinicService`, `useDoctors`, `useErpInventory`, `useQueryClient`, `useServiceConsumables`, `useUpdateAdminClinicService` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 3, GlassModal: 0, Modal: 0, Menu: 12 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Каталог услуг **текущей** клиники (из `AdminClinicContext`): таблица с ценой/длительностью/врачами, просмотр карточки кликом по строке, создание и правка через drawer, удаление из меню строки.

## Логика и данные

- **Хуки:** `useAdminClinic` (`currentClinicId`), `useAdminClinicServices`, `useDeleteAdminClinicService`, `useDoctors` (активные врачи для подписей в таблице); `useQueryClient` для инвалидации после сохранения в drawer.
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/clinics/{clinicId}/services`
  - `POST /v1/admin/clinics/{clinicId}/services`
  - `PATCH /v1/admin/clinics/{clinicId}/services/{serviceId}` (через хуки create/update внутри `ServiceEntityDrawer`)
  - `DELETE /v1/admin/clinics/{clinicId}/services/{serviceId}`
  - `GET /v1/doctors?...` (фильтр `clinic_id`, `is_active`)

## RBAC / entitlements / edition

- **fact:** Сегмент `services` **не** в `SEGMENT_ENTITLEMENT` — отдельного ключа entitlement в навигационной карте нет.
- **fact:** Без выбранной клиники в шапке страница показывает подсказку вместо данных (guard на `clinicId`).

## UI-скелет (as-built)

- `ContextBar` «Услуги» + «Добавить услугу».
- Загрузка: `PageSkeleton`; ошибка: `QueryErrorAlert`.
- Пустой список: `EmptyState` с действием создания.
- Таблица с колонками название, категория, цена (зачёркнутая база при скидке), длительность, врачи, статус, колонка действий.

## Инвентарь поверхностей UI (ось H)

- **`ServiceEntityDrawer`** (`frontend/src/admin/components/entity/ServiceEntityDrawer.tsx`): обёртка **`AdminDrawer`** — create/edit/view, табы, поля услуги, связь с врачами, ERP consumables при наличии хуков (**fact:** каноничный паттерн entity-drawer).
- **Mantine `Menu`** на строке: «Редактировать», «Открыть карточку», «Удалить» (`deleteMutation`).
- **GlassModal / raw Modal:** нет на самой странице.

## Целевой UX (target vs as-built)

- *target:* управление прайсом и составом услуги в одном месте с предсказуемым drawer.
- *as-built:* таблица + `AdminDrawer` для сущности услуги.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** тестов страницы/drawer не найдено.

## Gap scan (вторая редакция)

- Удаление без промежуточного подтверждения в UI (только пункт меню) — продуктовый риск; при политике «мягкое удаление» стоит синхронизировать с API.
