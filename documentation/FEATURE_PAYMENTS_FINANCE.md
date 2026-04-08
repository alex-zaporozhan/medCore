# Платежи, платёжный шлюз и финансы

> **Версия:** 2026-04-02. **Роутеры:** `payments`, `admin_payment_gateway`, `admin_finance`, `admin_payroll`; сценарии записи см. `bookings`.

## Пациентские и публичные платежи

- Модуль `payments` — префикс `/payments`. Таблица методов: [router_surface/INDEX.md](./router_surface/INDEX.md).
- E2E-ориентир: `tests/e2e/test_booking_to_payment.py`.

## Платёжный шлюз (админка)

- Модуль `admin_payment_gateway` — префикс `/admin/clinics` с суффиксами в файле роутера (сверка с OpenAPI).
- UI: `/admin/payment-gateway` (`routePaths.ts`).

## Финансы, зарплата, склад

- Модули `admin_finance`, `admin_payroll`, `admin_inventory` — префикс `/admin/clinics`, разные подпути.
- UI: в том числе `/admin/finance`.

## Метрики

По каждому модулю — импорты в INDEX; глобально `GET /metrics` в `src/main.py`.

## Тесты

Списки в INDEX для перечисленных модулей; обзор: [TESTING_SURFACE.md](./TESTING_SURFACE.md).

---

Reference: [API_V1_ROUTER_MANIFEST.md](./API_V1_ROUTER_MANIFEST.md)
