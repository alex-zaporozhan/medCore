# Admin Schedule

## Метаданные

- **Path:** `/admin/schedule`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `SchedulePage`
- **Файл страницы:** `frontend/src/admin/pages/SchedulePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/SchedulePage.tsx`<br>`frontend/src/api/types.ts ← импорт из frontend/src/admin/pages/SchedulePage.tsx`<br>`frontend/src/admin/components/ScheduleCalendarGrid.tsx ← импорт из frontend/src/admin/pages/SchedulePage.tsx`<br>`frontend/src/admin/components/WaitlistPanel.tsx ← импорт из frontend/src/admin/pages/SchedulePage.tsx`<br>… +7 файлов |
| Строк (сумма по фрагментам) | 4604 |
| Хуки (эвристика, union) | `useAbsence`, `useAddFamilyMember`, `useAdminBookings`, `useAdminClinic`, `useAdminClinicServices`, `useAdminLoyaltySummaryByContact`, `useAdminPatientDiagnoses`, `useAdminPatientMedicalFiles`, `useAdminPatientMedicalVisits`, `useAdminPublicDoctorProfileByDoctor`, `useAdminSchedule`, `useAdminSession`, `useAdminWaitlist`, `useBusinessLexicon`, `useCancelBookingAdmin`, `useCancelWaitlistEntry`, `useClinics`, `useCreateAdminBooking`, `useCreateAdminPatientDiagnosis`, `useCreateAdminPatientMedicalVisit`, `useCreateAdminPublicDoctorProfileMutation`, `useCreateDoctor`, `useCreatePatient`, `useDoctor`, `useDoctorScheduleConfig`, `useDoctors`, `useDraggable`, `useDroppable`, `useErpInventory`, `useErpPayroll`, `useLoyalty`, `usePatchAdminPublicDoctorProfileMutation`, `usePatchBookingAdmin`, `usePatient`, `usePatientAiInsight`, `usePatients`, `usePayrollPolicies`, `useQueryClient`, `useRescheduleBookingAdmin`, `useSalaryTransactions`, `useSensor`, `useSensors`, `useServiceConsumables`, `useSetBookingStatusAdmin`, `useUpdateDoctor`, `useUpdatePatient`, `useUploadAdminPatientMedicalFile`, `useWorkingHours` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 9, GlassModal: 16, Modal: 1, Menu: 12 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Операционное расписание клиники на выбранный день/месяц: агрегированная сетка по врачам, записи на приём, лист ожидания (`WaitlistPanel`), создание записи из слота, перенос/отмена через карточку записи, быстрый просмотр пациента и врача в боковых панелях.

## Логика и данные

- **Хуки (основные):** `useAdminSchedule`, `useAdminBookings`, `useCreateAdminBooking`, `useRescheduleBookingAdmin`, `useCancelBookingAdmin`, `useAdminWaitlist`, `useDoctors`, `useAdminClinicServices`, `usePatients`, `usePatient`, `useDoctor`, `useQueryClient`; навигация по дате — `useSearchParams`, `CompactMonthPicker`.
- **Вложенные компоненты:** `ScheduleCalendarGrid`, `WaitlistPanel`, `BookingEntityDrawer`, `PatientEntityDrawer`, `DoctorEntityDrawer`, `ClinicSelector`, локальная форма `ScheduleCreateBookingForm`.
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/clinics/{clinicId}/schedule?date=&doctor_ids=...`
  - `GET /v1/admin/bookings?...` · `POST /v1/admin/bookings` · `PUT /v1/admin/bookings/{id}/reschedule` · `PUT .../cancel` / статусы (см. `useAdminBookings.ts`)
  - waitlist / queue-policy: `GET|POST|PATCH|DELETE` под `/v1/admin/clinics/{clinicId}/waitlist...` и `queue-policy` (`useAdminWaitlist.ts`)
  - `GET /v1/doctors?...` · `GET /v1/doctors/{id}`
  - `GET /v1/patients?...` · `GET /v1/patients/{id}`
  - услуги клиники: через `useAdminClinicServices` (`/v1/admin/clinics/{clinicId}/services`)

## RBAC / entitlements / edition

- **fact:** Сегмент `schedule` **не** в `SEGMENT_ENTITLEMENT` — отдельного ключа SaaS-entitlement в карте навигации нет.
- **fact:** Права на операции с записями и waitlist задаются бэкендом; на странице много действий завязано на доступность UI в `BookingEntityDrawer` и мутациях.

## UI-скелет (as-built)

- `ContextBar`, переключение клиники/даты, `ScheduleCalendarGrid` + панель листа ожидания.
- Внутренние формы создания записи в `GlassModal` (слот, пациент, услуга).

### Evidence / QA (скриншоты)

- URL **`/admin/schedule`**, блок навигации **«КЛИЕНТЫ»** → **«Расписание»**. Заголовок **«Расписание»** + выбор филиала клиники.
- Фильтр **«Врачи»** (мультивыбор), навигация по дате: **«Вчера»**, **«Сегодня»**, **«Завтра»**, стрелки, поле даты.
- Сетка: колонка **«Время»**, далее колонки по выбранным врачам; свободные слоты — **«Свободен»**; занятые — карточка с бейджем статуса (**«Ожидает»** / **«Подтверждён»**), ФИО пациента, название услуги.
- **`GlassModal` «Новая запись»** (`size="lg"`): подстановка врача и даты/времени слота; поиск пациента (**«Найдите пациента по телефону или ФИО»**), поля телефона/ФИО, выбор пациента и услуги, комментарий; **«Отмена»** / **«Создать запись»**.
- **`BookingEntityDrawer`** (по умолчанию `presentation` как центрированная модалка): заголовок **«Запись»**, вкладки **«Детали»**, **«Услуги и чек»**, **«Расходники»**, **«Задачи»**; в деталях сводка со статусом, пациент, врач, дата/время, услуга, селектор **«Статус»**.
- **`PatientEntityDrawer`** с **`presentation="modal"`** с расписания: заголовок — ФИО; вкладки **«Основное»**, **«Визиты»**, **«Финансы»**, **«Абонементы»**, **«Медкарта / Заметки»**, **«Коммуникации»**; в шапке телефон, email, строка **«LTV — при наличии API»**; на части вкладок контент или заглушки зависят от API (**fact:** пустые блоки и кнопка **«Загрузить AI-обзор»** — ожидаемо при отсутствии данных/интеграции).

### Размер и поведение модалок (известное расхождение)

- На одном экране смешаны **`GlassModal`** разного `size` (напр. создание записи — `lg`) и **сущностные** окна **`BookingEntityDrawer` / `PatientEntityDrawer`** в режиме `modal` с собственной вёрсткой и фиксированной высотой области вкладок у записи (`BOOKING_MODAL_TABS_SCROLL_H` в коде — чтобы уменьшить «прыжки» при смене вкладки). Визуально итоговая ширина/высота окон **не унифицирована одним токеном** — при полировке UI имеет смысл свести к одному паттерну (`GlassModal` + общие отступы) или задокументировать дизайн-токены (**gap** для дизайна).

## Инвентарь поверхностей UI (ось H)

- **Несколько `GlassModal`:** создание записи из слота — **`size="lg"`**; отмена/перенос DnD — без явного xl/lg (дефолт компонента); см. последовательность `opened` в `SchedulePage.tsx`.
- **`BookingEntityDrawer`:** по умолчанию центрированный **`GlassModal` `size="xl"`** с вкладками; опционально боковой **`AdminDrawer`** (`presentation="drawer"`). На расписании проп `presentation` не задаётся — режим **modal**.
- **`PatientEntityDrawer` / `DoctorEntityDrawer`:** на расписании **`presentation="modal"`** (центрированное окно поверх сетки; не путать с боковым drawer в других местах).
- **Popover / Select / MultiSelect:** фильтры и вспомогательный UI в формах.

## Целевой UX (target vs as-built)

- *target:* единый экран «кто когда занят» + запись без переключения разделов.
- *as-built:* плотный UI с несколькими модалками и тремя паттернами drawer (запись, пациент, врач).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** автотестов страницы не найдено.

## Gap scan (вторая редакция)

- Высокая связность модалок и drawer’ов — регрессии без e2e дороги в сопровождении; имеет смысл выделить сценарии «создать запись», «перенести», «waitlist → запись».
- Отдельные кнопки/подсказки в карточке пациента и смежных экранах могут выглядеть «заглушками» (LTV, AI, часть вкладок) — это не баг маршрута расписания, а **зависимость от API и roadmap**; для QA фиксировать ожидаемое поведение по задаче.
