# App Home

## Метаданные

- **Path:** `/app` (index) и зеркало `/c/:clinicSlug/app`
- **Зона:** app (пациент)
- **Компонент(ы) в App.tsx:** `HomePage`
- **Файл страницы:** `frontend/src/app/pages/HomePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/app/pages/HomePage.tsx`<br>`frontend/src/contexts/PatientAuthContext.tsx ← импорт из frontend/src/app/pages/HomePage.tsx`<br>`frontend/src/shared/utmTracking.ts ← импорт из frontend/src/app/pages/HomePage.tsx`<br>`frontend/src/shared/ui/EmptyState.tsx ← импорт из frontend/src/app/pages/HomePage.tsx`<br>… +2 файлов |
| Строк (сумма по фрагментам) | 801 |
| Хуки (эвристика, union) | `useClinics`, `useDoctors`, `usePatientAuth`, `usePatientBookings`, `usePatientName`, `usePublicClinicServices`, `useQuery`, `useQueryClient`, `useUtmTracking` |
| Пути в строках `/v1/...` | `/v1/patient/me` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Домашний экран PWA: приветствие с именем из профиля при наличии токена, карточка ближайшего визита с подписью врача и услуги, заглушка «Акции и новости», блок онлайн-записи с выбором клиники (localStorage ключ `app.selectedClinicId`), ссылки на историю и запись. UTM через `useUtmTracking`.

## Логика и данные

- **Хуки:** `useClinics`, `usePatientBookings`, `useDoctors`, `usePublicClinicServices`, `usePatientAuth`, `useUtmTracking`; локальный `usePatientName` — `useQuery` с динамическим `authApi(accessToken).get` на путь `/v1/patient/me`.
- **queryKey:** клиники из `useClinics`; `patient-bookings` с patientId; `patient` и `me`; публичные услуги клиники и `doctors` с фильтром для подписи к визиту.
- **API:** `GET /v1/clinics`; `GET /v1/patient/bookings` с query `patient_id` и Bearer; `GET /v1/patient/me`; `GET /v1/public/clinics/{clinicId}/services`; `GET /v1/doctors` с query.

## RBAC / entitlements / edition

- Нужен контекст `PatientAuthProvider`: без patientId и токена список записей не грузится (**fact**).

## UI-скелет (as-built)

Вертикальный `Stack`: заголовок, кнопка обновления (инвалидация bookings, clinics, patient me), карточка визита или `EmptyState`, горизонтальный `ScrollArea` с тремя плейсхолдерами, `Paper` с CTA и картами клиник.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal:** нет.
- Блок QR: квадрат 56px с подписью «QR» без генерации изображения.

## Целевой UX (target vs as-built)

- *target:* сторисы из API, рабочий QR, перенос и отмена с API с карточки.
- *as-built:* кнопки ведут на другие маршруты; сторисы статичны.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Сторисы и QR не на данных.
- Выбор клиники в localStorage не связан явно с первым шагом booking.
