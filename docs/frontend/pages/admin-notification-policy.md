# Admin Notification Policy

## Метаданные

- **Path:** `/admin/notification-policy`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminNotificationPolicyPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminNotificationPolicyPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminNotificationPolicyPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminNotificationPolicyPage.tsx`<br>`frontend/src/hooks/useAdminNotificationPolicy.ts ← импорт из frontend/src/admin/pages/AdminNotificationPolicyPage.tsx`<br>`frontend/src/shared/ui/DataSkeleton.tsx ← импорт из frontend/src/admin/pages/AdminNotificationPolicyPage.tsx`<br>… +1 файлов |
| Строк (сумма по фрагментам) | 334 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminNotificationPolicy`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useMutation`, `useQuery`, `useQueryClient`, `useUpdateAdminNotificationPolicyMutation` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Три переключателя политики: может ли пациент в приложении сам отключать уведомления о скидках, напоминания о приёме и все уведомления целиком. Каждое изменение уходит отдельной мутацией `PUT` с одним полем.

## Логика и данные

- **Хуки:** `useAdminClinic`; `useAdminNotificationPolicy`, `useUpdateAdminNotificationPolicyMutation` из `@/hooks/useAdminNotificationPolicy`.
- **queryKey:** `queryKeys.adminNotificationPolicy(clinicId)`.
- **API:**
  - `GET /v1/admin/clinics/{clinicId}/notification-policy` — объект с булевыми `allow_patient_disable_discount_notifications`, `allow_patient_disable_reminders`, `allow_patient_disable_all_notifications`.
  - `PUT /v1/admin/clinics/{clinicId}/notification-policy` — частичное тело (в коде передаётся одно поле за раз); инвалидация того же queryKey.

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для сегмента `notification-policy` ключа нет (**fact**).

## UI-скелет (as-built)

Без клиники: `ContextBar` + `Text`. Загрузка: `DataSkeleton`. Ошибка: `QueryErrorAlert`. Основной вид: пояснение `Text`, `Paper` с тремя `Switch`, на время `updatePolicy.isPending` переключатели `disabled`.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal, Menu, Stepper:** на странице нет.

## Целевой UX (target vs as-built)

- *target:* пакетное сохранение, черновики, подсказки о правовых последствиях.
- *as-built:* мгновенный PATCH-стиль по одному флагу; общий loading на все три switch.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Нет отображения ошибки мутации при сбое `PUT` (только query load/error).
- Нет явной связи между «отключить все» и двумя другими переключателями (конфликты правил только на бэкенде/продукте).
