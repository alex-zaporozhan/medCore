# Мастер записи (пациент, PWA)

## Метаданные

- **Path:** `/app/booking` и зеркало `/c/:clinicSlug/app/booking` (тот же компонент)
- **Зона:** app
- **Компонент в App.tsx:** `BookingWizardPage` в `PATIENT_APP_PAGE_BY_SEGMENT`
- **Файл страницы:** `frontend/src/app/pages/BookingWizardPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/app/pages/BookingWizardPage.tsx`<br>`frontend/src/contexts/PatientAuthContext.tsx ← импорт из frontend/src/app/pages/BookingWizardPage.tsx`<br>`frontend/src/shared/semanticUi.ts ← импорт из frontend/src/app/pages/BookingWizardPage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/app/pages/BookingWizardPage.tsx`<br>… +2 файлов |
| Строк (сумма по фрагментам) | 1412 |
| Хуки (эвристика, union) | `useClinics`, `useCreatePatientBooking`, `useCreatePayment`, `useDoctorSchedule`, `useDoctors`, `usePatientAuth`, `usePublicClinicServices` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Пошаговая запись пациента: выбор клиники (если несколько), услуги, врача, слота, при необходимости оплата.

## Логика и данные

- **Контекст:** `usePatientAuth` (токен, `patientId`).
- **Хуки:** `useClinics`, `usePublicClinicServices`, `useDoctors`, `useDoctorSchedule`, `useCreatePatientBooking`, `useCreatePayment` и др. из `@/hooks`.
- **Локальное состояние:** шаг `Stepper`, выбранные clinic/service/doctor/slot; prefill из `?clinic_id=` и `localStorage` (`app.selectedClinicId`).
- **API (факт):**
  - `POST /v1/patient/bookings?patient_id={id}` — создание записи (`useCreatePatientBooking`), инвалидация `["patient-bookings"]`.
  - `POST /v1/payments` с `booking_id` (и опционально `gateway_id`) — `useCreatePayment` (`frontend/src/hooks/usePayments.ts`); цепочка: успех booking → onSuccess → `createPayment`; при `prepayment_required === false` или после `payment_url` — редирект на success/внешнюю оплату.
  - Сопутствующие GET для услуг/расписания — см. хуки `usePublicClinicServices`, `useDoctorSchedule`.

## RBAC / entitlements / edition

Доступ по пациентскому JWT; без токена функциональность не гарантируется (guard на уровне роутера/провайдера).

## UI-скелет (as-built)

- Mantine `Stepper`, `Card`, `Select`, `SimpleGrid`, `Alert`, сообщения об ошибках через `getBookingErrorMessage` / коды API.

## Инвентарь поверхностей UI (as-built)

`AdminDrawer` / `GlassModal` / `Menu` **нет**.

| Поверхность | Триггер | Данные / мутация | Примечание |
|-------------|---------|------------------|------------|
| `Stepper` | Клик по шагу (`onStepClick`) | Шаги: при `multiClinic` — «Клиника», затем «Услуга», «Врач», «Дата и время», при `prepaymentEnabled` — «Подтверждение / оплата»; иначе услуга с индекса 0 | Индексы шагов пересчитываются в коде (`clinicStep`, `serviceStep`, …) (**fact**) |
| `Alert` | Ошибка `createBooking` или `createPayment` | Тексты `bookingErrorMessage` / `paymentErrorMessage` | После успешного шага ошибки сбрасываются мутациями React Query (**fact**) |
| Кнопки «Далее» / подтверждение | Навигация по шагам и `handleConfirm` / `handleConfirmWithoutPayment` | См. раздел «Логика и данные» | `nextDisabled` блокирует переход (**fact**) |

## Целевой UX (target vs as-built)

- *target:* предсказуемый поток при мультиклинике и понятные ошибки слота/оплаты.
- *as-built:* ветвление шагов зависит от `multiClinic`; редиректы успеха — см. `ROUTE_PATHS` и страницу success вне `/app`.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md); тексты ошибок — согласовать с `patient_messages` на бэкенде где применимо.

## Тесты

- Поиск e2e/vitest по `BookingWizard` в `frontend`.

## Gap scan

- В v2: полная таблица шагов ↔ поля API при всех комбинациях `multiClinic` / `prepaymentEnabled`.
