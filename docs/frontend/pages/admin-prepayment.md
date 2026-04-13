# Admin Prepayment

## Метаданные

- **Path:** `/admin/prepayment`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminPrepaymentPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminPrepaymentPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminPrepaymentPage.tsx`<br>`frontend/src/hooks/useAdminPrepayment.ts ← импорт из frontend/src/admin/pages/AdminPrepaymentPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminPrepaymentPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminPrepaymentPage.tsx` |
| Строк (сумма по фрагментам) | 534 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminPrepayment`, `useAdminPrepaymentPolicies`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreatePrepaymentPolicy`, `useDeletePrepaymentPolicy`, `useMutation`, `useQuery`, `useQueryClient`, `useUpdateClinicMutation`, `useUpdatePrepaymentPolicy` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 3, GlassModal: 0, Modal: 0, Menu: 5 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Управление предоплатой для выбранной клиники: глобальный переключатель «предоплата включена» (поле клиники), таблица правил (область: услуга / врач / врач+услуга, режим, тип суммы, дедлайн, приоритет), CRUD политик через боковую панель.

## Логика и данные

- **Хуки:** `useAdminClinic` (`currentClinicId`), `useClinics`, `useUpdateClinicMutation`, `useAdminPrepaymentPolicies`, `useCreatePrepaymentPolicy`, `useUpdatePrepaymentPolicy`, `useDeletePrepaymentPolicy`, `useDisclosure`.
- **Типовые API (`/v1/...`):**
  - `PUT /v1/clinics/{clinicId}` — обновление `prepayment_enabled` (через `useUpdateClinicMutation`)
  - `GET /v1/admin/clinics/{clinicId}/prepayment/policies`
  - `POST /v1/admin/clinics/{clinicId}/prepayment/policies`
  - `PUT /v1/admin/clinics/{clinicId}/prepayment/policies/{policyId}`
  - `DELETE /v1/admin/clinics/{clinicId}/prepayment/policies/{policyId}`

## RBAC / entitlements / edition

- **fact:** Сегмент `prepayment` **не** в `SEGMENT_ENTITLEMENT` — отдельного SaaS-ключа в `adminShellSegmentEntitlementKey` нет.
- **fact:** Без выбранной клиники показывается подсказка; кнопка «Добавить политику» отключена, пока `prepayment_enabled` выключен.

## UI-скелет (as-built)

- `ContextBar` «Предоплата», `Paper` с `Switch` включения предоплаты.
- Таблица политик или `EmptyState`; **`Menu`** на строке — редактировать / удалить.
- Состояния: `PageSkeleton`, `QueryErrorAlert`.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer`:** создание/редактирование политики (`opened` / `editingId`, форма `Select` + `NumberInput` + `Switch` + «Сохранить»).
- **GlassModal / raw Modal:** нет.

## Целевой UX (target vs as-built)

- *target:* явное включение продукта предоплаты и предсказуемый приоритет правил.
- *as-built:* компактная форма в drawer; режимы и типы суммы — из фиксированных списков в коде.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** тестов страницы не найдено.

## Gap scan (вторая редакция)

- Область `doctor_service` в UI не раскрывает связку id врача/услуги в этом проходе — при аудите бэкенда сверить обязательные поля DTO и отразить в паспорте при появлении в форме.
