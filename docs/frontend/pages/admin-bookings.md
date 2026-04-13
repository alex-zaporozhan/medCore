# Admin Bookings

## Метаданные

- **Path:** `/admin/bookings`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminBookingsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminBookingsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminBookingsPage.tsx`<br>`frontend/src/api/types.ts ← импорт из frontend/src/admin/pages/AdminBookingsPage.tsx`<br>`frontend/src/hooks/useAdminBookings.ts ← импорт из frontend/src/admin/pages/AdminBookingsPage.tsx`<br>`frontend/src/hooks/useDoctors.ts ← импорт из frontend/src/admin/pages/AdminBookingsPage.tsx`<br>… +7 файлов |
| Строк (сумма по фрагментам) | 2598 |
| Хуки (эвристика, union) | `useAdminBookings`, `useAdminClinic`, `useAdminFormTemplates`, `useAdminLoyaltySummaryByContact`, `useAdminSession`, `useBusinessLexicon`, `useCancelBookingAdmin`, `useCheckoutInfo`, `useClinics`, `useCompleteBookingAdmin`, `useCreateAdminBooking`, `useDoctor`, `useDoctors`, `useErpInventory`, `useLoyalty`, `useMutation`, `usePatchBookingAdmin`, `usePatient`, `usePatients`, `useQuery`, `useQueryClient`, `useRescheduleBookingAdmin`, `useSendFormLink`, `useService`, `useServiceConsumables`, `useServices`, `useSetBookingStatusAdmin` |
| Пути в строках `/v1/...` | `/v1/admin/bookings` |
| Вхождения UI | AdminDrawer: 8, GlassModal: 6, Modal: 0, Menu: 8 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Реестр записей на приём с фильтрами (врач, дата, статус, телефон пациента): таблица, открытие карточки записи, отмена с подтверждением, завершение визита (чекаут: абонемент или «в кассу»), отправка ссылки на цифровую форму пациенту.

## Логика и данные

- **Хуки:** `useAdminBookings`, `useCancelBookingAdmin`, `useCompleteBookingAdmin`, `useCheckoutInfo`, `useDoctors`, `usePatients`, `useServices`, `useAdminFormTemplates`, `useSendFormLink`, `useAdminClinic`.
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/bookings?...` (фильтры `doctor_id`, `date`, `status`, `patient_phone` и т.д. — см. вызов в странице)
  - `PUT /v1/admin/bookings/{id}/cancel`
  - `GET /v1/admin/bookings/{id}/checkout-info`
  - `PUT /v1/admin/bookings/{id}/complete` (тело с `use_subscription_id` или `null`)
  - `GET /v1/doctors?...` · `GET /v1/patients?...` · `GET /v1/services?...`
  - `GET /v1/admin/forms/templates`
  - `POST /v1/admin/forms/send-link` (шаблон, канал `whatsapp` | `sms` | `copy_only`)

## RBAC / entitlements / edition

- **fact:** Сегмент `bookings` **не** входит в `SEGMENT_ENTITLEMENT` (`adminEntitlementNav.ts`) — отдельного ключа `marketing.attribution` / иных entitlement для этого пути в карте нет.
- **fact:** Доступ к данным и мутациям определяется бэкендом по админской сессии.

## UI-скелет (as-built)

- `ContextBar`, фильтры (`Select` врача/статуса, дата, телефон), `AdminDataTableToolbar` / `AdminDataTableSurface`, таблица с `Menu` действий на строке.
- Пустое/ошибочное состояние: подсказка `EmptyStateHint` / `QueryErrorAlert`, `DataSkeleton` при загрузке.

## Инвентарь поверхностей UI (ось H)

- **`BookingEntityDrawer`:** **`AdminDrawer`** (паттерн entity) — детали записи, обновление, инициация отмены.
- **`GlassModal`:** подтверждение отмены записи (`pendingCancelId`).
- **`AdminDrawer` «Чекаут»:** выбор списания с абонемента или завершения «в кассу» (`checkoutBookingId`, `useCheckoutInfo`, `completeMutation`).
- **`AdminDrawer` «Отправить форму»:** выбор шаблона и канала, `useSendFormLink` (**fact:** при `copy_only` и успехе — попытка `navigator.clipboard.writeText`).

## Целевой UX (target vs as-built)

- *target:* оператор видит слоты и статусы, быстро закрывает визит и досылает формы.
- *as-built:* несколько выезжающих панелей + одна модалка подтверждения; чекаут вынесен в отдельный drawer.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** выделенных тестов страницы не найдено.

## Gap scan (вторая редакция)

- Несколько `AdminDrawer` с разным назначением на одной странице — при росте сценариев стоит унифицировать навигацию (один drawer с шагами или вкладками).
