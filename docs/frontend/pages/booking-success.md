# Booking Success

## Метаданные

- **Path:** `/booking/success` (`ROUTE_PATHS.other.bookingSuccess`)
- **Зона:** app (публичная страница после записи/оплаты; без обязательного layout shell в коде страницы)
- **Компонент(ы) в App.tsx:** `BookingSuccessPage`
- **Файл страницы:** `frontend/src/app/pages/BookingSuccessPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/app/pages/BookingSuccessPage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/app/pages/BookingSuccessPage.tsx` |
| Строк (сумма по фрагментам) | 234 |
| Хуки (эвристика, union) | `useClinics` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Подтверждение успешной записи (и при включённом предоплатном режиме клиники — намёк на успешную оплату); ссылки в историю записей и на главную PWA.

## Логика и данные

- **Хук:** `useClinics()` из `@/hooks` → `GET /v1/clinics` (через `api.get` в `useClinics`, см. `frontend/src/hooks/useClinics.ts`).
- **Локальный выбор клиники:** `localStorage` ключ `app.selectedClinicId`; если невалиден — первая клиника из списка (**fact**).
- **Условный текст:** `prepayment_enabled` у выбранной клиники → фраза про успешную оплату, иначе только «Ждём вас на приёме».

## RBAC / entitlements / edition

Страница не обёрнута в `AdminAuthGuard`; данные клиник идут через публичный/пациентский контур `useClinics` (как настроено в хуке и токене пациента) — при расхождении с продуктом зафиксировать **gap**.

## UI-скелет (as-built)

- Простой `Stack` с отступами: `Title`, один `Text`, два `Anchor` (`Link`) на `/app/history` и `/app`.

## Инвентарь поверхностей UI (ось H)

Модалок и drawer **нет**; только типографика и ссылки (**fact**).

## Целевой UX (target vs as-built)

- *as-built:* минималистичное завершение сценария бронирования.
- *target:* если клиник несколько и выбор из localStorage неверен, текст может не соответствовать фактической клинике записи (**gap** данных без `booking_id` в URL).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Маршрут в `routePaths`.
- Нет целевых тестов на ветвление `prepayment_enabled` (**gap**).

## Gap scan (вторая редакция)

- Нет параметра из потока бронирования (только эвристика по localStorage) — для строгой трассировки сценария см. связанные паспорта `app-booking` и платежи.
