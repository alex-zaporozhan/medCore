# DEV_PROMPTS: Отмена записи в расписании

> План действий для @DEV по документу `docs/ARCH_SCHEDULE_CANCEL_FLOW.md`. Задачи на верификацию и доработку цепочки «Отменить запись».

---

## Контекст

Цепочка: кнопка «Отменить запись» в модалке «Детали записи» (расписание) → модалка подтверждения → `PUT /v1/admin/bookings/{id}/cancel` → обновление БД, инвалидация кэша расписания, refetch на фронте, фильтр отменённых в сетке. Архитектура и риски описаны в `ARCH_SCHEDULE_CANCEL_FLOW.md`.

---

## Задача 1. Верификация фронтенда (расписание)

**Цель:** убедиться, что отмена из расписания вызывает API, закрывает модалки и обновляет сетку.

### Шаги

1. **Проверить вызов API**  
   В `SchedulePage.tsx` кнопка «Отменить запись» в модалке «Подтверждение отмены» вызывает `cancelBookingMutation.mutate(idToCancel, { onSuccess, onSettled })`. Убедиться, что:
   - передаётся корректный `idToCancel` (из `pendingCancelBookingId`);
   - в `onSuccess` вызываются `queryClient.refetchQueries({ queryKey: ["admin-bookings"] })` и `queryClient.refetchQueries({ queryKey: ["admin-schedule"] })`.

2. **Проверить фильтр для сетки**  
   В сетку передаётся `bookingsForGrid = useMemo(() => bookings?.filter(b => b.status !== "cancelled") ?? [], [bookings])`. Убедиться, что в `ScheduleCalendarGrid` передаётся именно `bookingsForGrid`, а не `bookings`.

3. **Проверить закрытие модалок**  
   В `onSuccess`: `setPendingCancelBookingId(null)`, `setSelectedBooking(null)`, `setEditingBooking(null)`. В `onSettled`: снова `setPendingCancelBookingId(null)`. Убедиться, что оба колбэка присутствуют.

**Критерий готовности:** после нажатия «Отменить запись» в подтверждении уходит один запрос `PUT .../cancel`, модалка закрывается, запись исчезает из сетки на выбранный день.

**Файлы:** `frontend/src/admin/pages/SchedulePage.tsx`.

---

## Задача 2. Верификация хука useCancelBookingAdmin

**Цель:** убедиться, что инвалидация кэша и оптимистичное обновление не конфликтуют с refetch из страницы.

### Шаги

1. **Проверить mutationFn**  
   `api.put<Booking>(`/v1/admin/bookings/${id}/cancel`)` — без тела. Один аргумент — строка `id`.

2. **Проверить onSettled**  
   Вызовы: `invalidateQueries({ queryKey: ["admin-bookings"] })`, `invalidateQueries({ queryKey: ["reports-dashboard"] })`, `invalidateQueries({ queryKey: ["admin-schedule"] })`. Оставить как есть; refetch на странице расписания дополняет инвалидацию.

3. **Опционально: показ ошибки**  
   Если в продукте нужен явный тост при ошибке отмены, в `SchedulePage` в колбэке мутации добавить `onError: (err) => { ... toast/notify(err.message) }`. Не обязательно для минимальной реализации.

**Критерий готовности:** хук вызывает правильный URL, после успеха/ошибки инвалидируются перечисленные ключи.

**Файлы:** `frontend/src/hooks/useAdminBookings.ts`.

---

## Задача 3. Верификация бэкенда (отмена и кэш)

**Цель:** убедиться, что запись переводится в `cancelled`, транзакция коммитится и кэш расписания инвалидируется.

### Шаги

1. **Роутер**  
   `PUT /admin/bookings/{booking_id}/cancel` → `cancel_booking_admin` → `service.cancel_booking(current_admin.clinic_id, booking_id)`. Ошибки: `LookupError` → 404, `ValueError` → 400. Ответ: `BookingRead`.

2. **Сервис**  
   В `BookingService.cancel_booking`: проверка клиники, запрет при `status in {"completed", "cancelled"}`, присвоение `booking.status = "cancelled"`, `repository.update(booking)`, затем `schedule_service.invalidate_daily_schedule_cache(doctor_id, appointment_date)`. Порядок не менять.

3. **Репозиторий**  
   `update(booking)` выполняет `session.flush()` и `session.refresh(booking)`. Коммит сессии выполняется в `get_db()` после выхода из эндпоинта. Убедиться, что в тестах или при ручной проверке запись в БД переходит в `cancelled`.

4. **Расписание**  
   В `_build_daily_schedule` слот помечается занятым только если `booking.status != "cancelled"`. После инвалидации кэша следующий запрос к расписанию пересобирает слоты из БД — отменённая запись не должна занимать слот.

**Критерий готовности:** отмена через API меняет запись в БД на `cancelled`; при запросе расписания на этот день слот отменённой записи приходит свободным (без `booking_id`).

**Файлы:** `src/api/v1/routers/bookings.py`, `src/application/services/booking_service.py`, `src/infrastructure/database/booking_repo_impl.py`, `src/application/services/schedule_service.py`.

---

## Задача 4. (Опционально) Подтверждение отмены на странице «Записи»

**Цель:** единообразие с расписанием: перед отменой показывать модалку подтверждения.

### Шаги

1. В `AdminBookingsPage.tsx` завести состояние `pendingCancelId: string | null`.
2. Вместо прямого `cancelMutation.mutate(b.id)` по клику «Отменить» устанавливать `setPendingCancelId(b.id)`.
3. Добавить модалку (GlassModal) с текстом «Вы действительно хотите отменить запись?» и кнопками «Нет» / «Отменить запись». При подтверждении вызывать `cancelMutation.mutate(pendingCancelId, { onSuccess: () => setPendingCancelId(null) })`.
4. После успеха при необходимости вызывать `refetchQueries` для списка записей (если не срабатывает инвалидация из хука).

**Критерий готовности:** на странице «Записи» отмена возможна только после подтверждения в модалке.

**Файлы:** `frontend/src/admin/pages/AdminBookingsPage.tsx`.

---

## Итог для @DEV

1. Выполнить **задачи 1–3** (верификация фронта, хука, бэкенда) по чек-листу выше.
2. По результату: либо зафиксировать «реализация соответствует ARCH», либо внести правки (например, доп. refetch, обработка ошибок, порядок вызовов).
3. Задачу **4** выполнять по решению продукта (единообразие подтверждения отмены на всех экранах).

Архитектурный контекст и чек-лист QA: **`docs/ARCH_SCHEDULE_CANCEL_FLOW.md`**.
