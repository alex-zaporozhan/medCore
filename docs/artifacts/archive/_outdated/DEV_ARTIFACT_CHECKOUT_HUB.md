# DEV_ARTIFACT_CHECKOUT_HUB — Checkout Hub при завершении визита

> **Назначение:** Пошаговая реализация сценария «Завершить» в списке записей: открытие Drawer (Checkout Hub), запрос подходящих абонементов, выбор способа оплаты, вызов complete с опциональным `use_subscription_id`.  
> **Для кого:** @DEV. Контекст задаёт @ARCH / @LEAD. Задача запланирована в буфере `REV_IMPLEMENTATION_RUNBOOK.md`.

**Входы:** `docs/TPF_MODULE_FINANCE.md` (Checkout Hub), `docs/TPF_MODULE_LOYALTY.md` (Auto-Checkout), `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md` (Фаза B4.4 — контракты API).

---

## Контракты API (уже реализованы на бэкенде)

- **GET** `/api/v1/admin/bookings/{booking_id}/checkout-info`  
  Response 200: `{ "eligible_subscriptions": [ { "customer_subscription_id": "uuid", "package_name": "...", "remaining_visits": 5, "remaining_amount": null }, ... ] }`

- **PUT** `/api/v1/admin/bookings/{booking_id}/complete`  
  Body (optional): `{ "use_subscription_id": "uuid" | null }`  
  Response 200: BookingRead (status = completed). При переданном `use_subscription_id` — списание визита с пакета без дублирования оплаты.

---

## Шаги (выполнять по порядку)

### Шаг CH.1. Хуки: checkout-info и complete с телом

- **Файл:** `frontend/src/hooks/useAdminBookings.ts`
- Добавить тип `CheckoutInfoResponse` и хук `useCheckoutInfo(bookingId: string | null)` — запрос `GET /v1/admin/bookings/{id}/checkout-info`, enabled при наличии bookingId.
- Изменить `useCompleteBookingAdmin`: mutationFn принимает `{ bookingId: string; use_subscription_id?: string | null }`, при вызове API передавать body `{ use_subscription_id }` при PUT complete.

### Шаг CH.2. Drawer Checkout Hub на странице записей

- **Файл:** `frontend/src/admin/pages/AdminBookingsPage.tsx`
- Вместо прямого вызова `completeMutation.mutate(b.id)` по клику «Завершить»: устанавливать состояние «запись для чекаута» (например `checkoutBookingId`) и открывать Drawer.
- Drawer (position right, size md/lg): заголовок «Чекаут — Завершить визит» или аналог.

### Шаг CH.3. Содержимое Drawer: чек, абонементы, кнопки

- В Drawer при открытии по `checkoutBookingId` запрашивать `useCheckoutInfo(checkoutBookingId)`.
- Показать блок «Оплата»:
  - Если `eligible_subscriptions.length > 0`: для каждого пакета — карточка (название, остаток визитов/суммы) и кнопка «Списать с абонемента»; при клике вызывать complete с `use_subscription_id: customer_subscription_id`.
  - Всегда показывать вариант «Оплатить в кассу» (complete без `use_subscription_id`).
- После успешного complete закрывать Drawer, сбрасывать `checkoutBookingId`, инвалидировать список записей (уже делает mutation onSettled).

### Шаг CH.4. Обработка ошибок и загрузки

- При загрузке checkout-info показывать Skeleton или текст «Загрузка…» в Drawer.
- При ошибке API (checkout-info или complete) показывать уведомление/текст ошибки; при ошибке complete не закрывать Drawer до успеха или явной отмены пользователем.
- Кнопка «Отмена» в Drawer: закрыть без вызова complete.

---

## To-do

- [x] Хуки: `useCheckoutInfo(bookingId)`, `useCompleteBookingAdmin` с опциональным `use_subscription_id` в теле PUT.
- [x] Страница записей: по «Завершить» открывать Drawer (состояние checkoutBookingId).
- [x] Drawer: запрос checkout-info, отображение eligible_subscriptions и кнопок «Списать с абонемента» / «Оплатить в кассу».
- [x] Обработка загрузки и ошибок; закрытие Drawer после успешного complete.

**Критерий приёмки:** В списке записей по нажатию «Завершить» открывается Drawer; отображаются подходящие абонементы (если есть); выбор «Списать с абонемента» или «Оплатить в кассу» вызывает complete с соответствующим телом; после успеха Drawer закрывается и список обновляется.
