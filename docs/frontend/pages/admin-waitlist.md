# Admin Waitlist

## Метаданные

- **Path:** `/admin/waitlist`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminWaitlistPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminWaitlistPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminWaitlistPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminWaitlistPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminWaitlistPage.tsx`<br>`frontend/src/admin/components/ClinicSelector.tsx ← импорт из frontend/src/admin/pages/AdminWaitlistPage.tsx` |
| Строк (сумма по фрагментам) | 566 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminQueuePolicy`, `useAdminSession`, `useAdminWaitlistEntries`, `useBusinessLexicon`, `useClinics`, `useCreateWaitlistEntry`, `useDeleteWaitlistEntry`, `useDoctors`, `usePatients`, `useUpdateWaitlistEntry`, `useUpsertQueuePolicy` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 5, GlassModal: 0, Modal: 0, Menu: 5 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Очередь ожидания записи для клиники: политика очереди (режим sequential/broadcast, размер рассылки, таймаут ответа), список записей с приоритетом и статусом, добавление и редактирование записей, удаление.

## Логика и данные

- **Хуки:** `useAdminWaitlistEntries`, `useAdminQueuePolicy`, `useCreateWaitlistEntry`, `useUpdateWaitlistEntry`, `useDeleteWaitlistEntry`, `useUpsertQueuePolicy`, `useDoctors`, `usePatients`, `useAdminClinic`, `useDisclosure`.
- **Типовые API (`/v1/...`):** семейство под `/v1/admin/clinics/{clinicId}/waitlist` и `/v1/admin/clinics/{clinicId}/queue-policy` (см. `useAdminWaitlist.ts` — GET списка, POST запись, PATCH/DELETE записи, GET/PUT политики).

## RBAC / entitlements / edition

- **fact:** Сегмент `waitlist` **не** в `SEGMENT_ENTITLEMENT` — отдельного ключа entitlement в навигационной карте нет.

## UI-скелет (as-built)

- `ContextBar` «Очередь ожидания» + `ClinicSelector` compact, кнопка «Добавить в очередь».
- Блок «Политика очереди»: `Select` режима, числовые поля, «Сохранить» (`upsertPolicyMutation`).
- Таблица записей или `EmptyState`; **`Menu`** — редактировать / удалить.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` «Добавить в очередь»:** форма пациент, дата, время, врач, приоритет.
- **`AdminDrawer` «Редактировать запись»:** вложенный `EditWaitlistEntryForm` (статусы waiting / notified / expired / cancelled).
- **GlassModal:** нет.

## Целевой UX (target vs as-built)

- *target:* управляемая очередь с понятной политикой уведомлений.
- *as-built:* политика на той же странице, что и список — удобно для оператора, но смешивает два уровня абстракции.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** тестов не найдено.

## Gap scan (вторая редакция)

- Статусы захардкожены в UI — при расширении enum на бэкенде нужна синхронизация.
