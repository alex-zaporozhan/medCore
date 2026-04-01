# ARCH: Область дашборда — одна клиника или все клиники

> Роли: @ARCH, @FRONTEND, @DEV.  
> Цель: дать пользователю выбор — дашборд показывает одну выбранную клинику или сводку по всем клиникам сразу.

---

## 1. Требование

- В админке на странице **Дашборд** пользователь может выбрать:
  - **Одна клиника** — метрики (записи, выручка, новые пациенты и т.д.) только по выбранной в шапке клинике; поведение как сейчас.
  - **Все клиники** — те же метрики, агрегированные по всем клиникам в системе (суммы записей, выручки, новых пациентов за день/неделю/месяц).

- Расписание и остальные разделы по‑прежнему работают в контексте **одной** выбранной клиники.

---

## 2. Контракт API

### 2.1. Одна клиника (существующий контракт)

- **GET** `/api/v1/admin/clinics/{clinic_id}/reports/dashboard?date=YYYY-MM-DD&period=day|week|month`
- Ответ: `DashboardReport` (date, bookings_*, new_patients, revenue).
- Доступ: только если `current_admin.clinic_id == clinic_id` (админ видит только свою клинику).

### 2.2. Все клиники (новый контракт)

- **GET** `/api/v1/admin/reports/dashboard-aggregate?date=YYYY-MM-DD&period=day|week|month`
- Ответ: тот же DTO `DashboardReport` — агрегат по всем клиникам (суммы по статусам записей, сумма выручки, сумма новых пациентов).
- Доступ: любой авторизованный админ (в будущем можно ограничить ролью owner).
- Тело ответа совпадает с отчётом по одной клинике, чтобы фронт мог использовать один и тот же UI.

---

## 3. Бэкенд

- **ReportsService**: добавить методы без фильтра по клинике:
  - `get_dashboard_report_all_clinics(day: date) -> DashboardReport`
  - `get_dashboard_report_period_all_clinics(day: date, period: str) -> DashboardReport`
- Запросы те же (bookings by status, new patients, revenue), но без условия `Booking.clinic_id == clinic.id` / `Patient.clinic_id == clinic.id` (и без join по clinic в подзапросах, где нужно).
- Новый роутер или маршрут под префиксом `/admin` (не под `/admin/clinics/{id}`): GET `/admin/reports/dashboard-aggregate`, зависимость `get_current_admin`, вызов сервиса и возврат `DashboardReport`.

---

## 4. Фронтенд

- На странице **Дашборд**:
  - Селектор области: два варианта — «Одна клиника» / «Все клиники» (например, `SegmentedControl` или `Select`/радио).
  - Состояние выбора можно хранить в `useState` (при желании позже — в localStorage или контексте).
- Запросы:
  - При «Одна клиника» — текущий хук `useAdminReportsDashboard(currentClinicId, date, period)` → GET `/admin/clinics/{id}/reports/dashboard`.
  - При «Все клиники» — новый хук `useAdminReportsDashboardAggregate(date, period)` → GET `/admin/reports/dashboard-aggregate`.
- Отображение карточек без изменений; при выборе «Все клиники» можно показывать подзаголовок вида «Сводка по всем клиникам», чтобы было понятно, что данные агрегированы.

---

## 5. Безопасность и ограничения

- Агрегат по всем клиникам доступен любому залогиненному админу. При появлении ролей (owner vs clinic admin) доступ к `dashboard-aggregate` можно ограничить только для owner.
- Расписание, записи, пациенты, финансы по‑прежнему привязаны к одной клинике (текущий выбор в шапке).

---

## 6. Связь с другими артефактами

- Реализация по шагам: `docs/DEV_PROMPTS_DASHBOARD_SCOPE.md`.
- Текущий отчёт по одной клинике: `src/api/v1/routers/admin_reports.py`, `ReportsService.get_dashboard_report` / `get_dashboard_report_period`.
