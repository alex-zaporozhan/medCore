# DEV_PROMPTS_DASHBOARD_SCOPE — Выбор области дашборда (одна клиника / все клиники)

> Роли: @DEV.  
> Читается после: `docs/ARCH_DASHBOARD_SCOPE.md`.

---

## 1. Цель

Реализовать на дашборде выбор: показывать метрики по **одной выбранной клинике** или **по всем клиникам** (агрегат). Бэкенд — новый эндпоинт агрегата; фронт — селектор и второй запрос.

---

## 2. Backend — to-do по порядку

### 2.1. ReportsService: агрегат по всем клиникам

**Файл:** `src/application/services/report_service.py`

- Добавить метод `get_dashboard_report_all_clinics(self, day: date) -> DashboardReport`:
  - Те же запросы, что в `get_dashboard_report(day, clinic_id)`, но **без** фильтра по `Booking.clinic_id` / `Patient.clinic_id` / `Payment.clinic_id`.
  - Bookings: `select(Booking.status, func.count()).where(Booking.appointment_date == day, Booking.deleted_at.is_(None)).group_by(Booking.status)`.
  - New patients: `select(func.count()).select_from(Patient).where(Patient.created_at >= ..., Patient.created_at < ..., Patient.deleted_at.is_(None))`.
  - Revenue: суммы по Payment (join Booking) и по Booking.prepayment_amount для completed без payment_id — без условия по clinic_id.
  - Вернуть `DashboardReport(date=day, bookings_*=..., new_patients=..., revenue=...)`.

- Добавить метод `get_dashboard_report_period_all_clinics(self, day: date, period: str) -> DashboardReport`:
  - Аналогично `get_dashboard_report_period`, но без фильтра по clinic_id (те же периоды: day/week/month и те же границы дат через `_period_bounds`).

### 2.2. Эндпоинт GET /admin/reports/dashboard-aggregate

**Вариант A (рекомендуется):** отдельный маленький роутер.

- Создать файл `src/api/v1/routers/admin_reports_aggregate.py`:
  - `router = APIRouter(prefix="/admin", tags=["admin-reports"])`
  - GET `"/reports/dashboard-aggregate"`, query-параметры: `date`, `period` (day|week|month).
  - Зависимости: `get_session`, `get_current_admin`.
  - Вызов `ReportsService(session).get_dashboard_report_all_clinics(date_param)` при `period == "day"`, иначе `get_dashboard_report_period_all_clinics(date_param, period)`.
  - Ответ: `DashboardReport` (тот же DTO, что для одной клиники).

- В `src/api/v1/router.py`: `api_router.include_router(admin_reports_aggregate.router)` (после или рядом с `admin_reports.router`).

**Вариант B:** добавить маршрут в существующий роутер, у которого есть префикс без `{clinic_id}` — если такой есть. Сейчас `admin_reports` имеет префикс `/admin/clinics`, поэтому путь без clinic_id туда не вписывается; вариант A предпочтительнее.

### 2.3. Проверка

- Ручной вызов: `GET /api/v1/admin/reports/dashboard-aggregate?date=2026-03-14&period=day` с заголовком Authorization. Ожидание: 200, тело — как у отчёта по одной клинике (те же поля).

---

## 3. Frontend — to-do по порядку

### 3.1. Хук для агрегата

**Файл:** `frontend/src/hooks/useAdminReports.ts` (или рядом)

- Добавить хук `useAdminReportsDashboardAggregate(dateStr: string | null, period: "day" | "week" | "month" = "day")`:
  - `queryKey`: например `["admin", "reports", "dashboard-aggregate", dateStr, period]`.
  - `queryFn`: `api.get<DashboardReport>(`/v1/admin/reports/dashboard-aggregate?date=${dateStr}&period=${period}`)`.
  - `enabled: !!dateStr`.

### 3.2. Селектор области на странице Дашборда

**Файл:** `frontend/src/admin/pages/AdminDashboardPage.tsx`

- Добавить состояние области: например `dashboardScope: "clinic" | "all"` (useState, по умолчанию `"clinic"`).
- Над блоком с карточками — селектор:
  - Варианты: «Одна клиника» / «Все клиники» (например Mantine `SegmentedControl` или `Radio.Group` с двумя опциями).
  - При выборе «Одна клиника» показывать текущую логику: `useAdminReportsDashboard(currentClinicId, date, "day")`; при отсутствии `currentClinicId` — подсказка «Выберите клинику в шапке».
  - При выборе «Все клиники» вызывать `useAdminReportsDashboardAggregate(date, "day")` и отображать те же карточки от этого ответа.
- Под заголовком «Дашборд» при scope «Все клиники» вывести подзаголовок: «Сводка по всем клиникам» (или аналогичный текст).
- Один и тот же разметка карточек для обоих режимов; различаются только источник данных и подпись.

### 3.3. Проверка

- Переключение «Одна клиника» ↔ «Все клиники» обновляет данные без ошибок.
- При одной клинике в БД числа в обоих режимах совпадают; при нескольких — «Все клиники» показывает суммы по всем.

---

## 4. Критерий готовности

- [ ] Backend: GET `/api/v1/admin/reports/dashboard-aggregate?date=...&period=day` возвращает сводку по всем клиникам.
- [ ] Frontend: на Дашборде есть выбор «Одна клиника» / «Все клиники», данные и подпись меняются соответственно.
- [ ] Нет регрессии: при выборе «Одна клиника» поведение как до изменений (в т.ч. при одной клинике в системе).
