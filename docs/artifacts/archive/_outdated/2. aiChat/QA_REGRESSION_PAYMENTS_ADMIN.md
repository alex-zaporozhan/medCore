# Регрессия: оплаты и админские маршруты

Набор тестов для проверки оплат и админских эндпоинтов (по желанию @QA).

**Полный пакет тестов (архитектура, QA, security):** `docs/ARCH_QA_SEC_BACKEND_TEST_PACKAGE.md`. Промпты для реализации: `docs/DEV_PROMPTS_BACKEND_TEST_PACKAGE.md`.

## Оплаты

- `tests/api/test_payments.py` — webhook платежей (YooKassa)
- `tests/api/test_admin_payment_gateway_credentials.py` — сохранение credentials касс (admin)
- `tests/services/test_clinic_payment_gateway_service.py` — сервис шифрования credentials
- `tests/e2e/test_booking_to_payment.py` — поток: запись → создание платежа (мок)
- `tests/api/test_pricing_and_ai.py` — цены, скидки, создание платежа, отчёты

## Админские маршруты

- `tests/api/test_admin_payment_gateway_credentials.py` — см. выше
- `tests/api/test_admin_omni_chat.py` — единый чат (список, сообщения, AI-режим)
- `tests/api/test_owner_omni_channels.py` — омниканальные каналы (owner)
- `tests/api/test_owner_omni_audit.py` — аудит омниканалов
- `tests/api/test_owner_omni_ai_settings.py` — AI-настройки омниканалов
- `tests/api/test_pricing_and_ai.py` — админские цены, AI summary/suggest/insight, отчёты
- `tests/api/test_frontend_integration.py` — health, auth, admin bookings, reports, admin schedule
- `tests/test_admin_create_doctor_patient.py` — создание врача/пациента (админ)

## Запуск

Полный пакет тестов (архитектура, QA, security): см. `docs/ARCH_QA_SEC_BACKEND_TEST_PACKAGE.md` и `docs/DEV_PROMPTS_BACKEND_TEST_PACKAGE.md`. Отдельно: `pytest tests/security/ -v` или `pytest -m security -v`.

Из корня проекта:

```bash
poetry run pytest \
  tests/api/test_payments.py \
  tests/api/test_admin_payment_gateway_credentials.py \
  tests/services/test_clinic_payment_gateway_service.py \
  tests/e2e/test_booking_to_payment.py \
  tests/api/test_admin_omni_chat.py \
  tests/api/test_owner_omni_channels.py \
  tests/api/test_owner_omni_audit.py \
  tests/api/test_owner_omni_ai_settings.py \
  tests/api/test_pricing_and_ai.py \
  tests/api/test_frontend_integration.py \
  tests/test_admin_create_doctor_patient.py \
  -v
```

Кратко (те же файлы):

```bash
poetry run pytest tests/api/test_payments.py tests/api/test_admin_payment_gateway_credentials.py tests/services/test_clinic_payment_gateway_service.py tests/e2e/test_booking_to_payment.py tests/api/test_admin_omni_chat.py tests/api/test_owner_omni_channels.py tests/api/test_owner_omni_audit.py tests/api/test_owner_omni_ai_settings.py tests/api/test_pricing_and_ai.py tests/api/test_frontend_integration.py tests/test_admin_create_doctor_patient.py -v
```

---

## Результат прогона (пример)

При запуске полного набора возможны:

- **23 passed** — оплаты (webhook, credentials, сервис), админ-чаты, owner-каналы/аудит, часть pricing, frontend-integration (health, doctors, services, schedule, reports, patients, admin_doctor_schedule), создание врача/пациента.
- **9 failed** — см. ниже.
- **3 errors** — падение на setup фикстуры `admin_auth` (429 Too Many Requests при частых логинах в одном прогоне).

### Типичные причины падений

| Что | Причина |
|-----|--------|
| `test_admin_*` в test_pricing_and_ai, test_frontend_integration::test_admin_bookings_list | 401: тест не передаёт заголовок авторизации (нет `admin_auth` в параметрах). |
| `test_owner_omni_ai_settings_*` | ERROR: фикстура `admin_auth` получает 429 (rate limit на admin login). |
| `test_create_payment_pricing_fields_without_discount` | ERROR: та же фикстура `admin_auth` (429). |
| `test_auth_send_code` | 500: реальный вызов SMS-провайдера; в тестах нужен мок или отключение отправки. |
| `test_owner_cannot_access_foreign_channel` | В seed админ привязан к той же клинике; нужен «чужой» clinic_id (аналогично test_admin_payment_gateway_credentials). |
| `test_booking_to_payment_flow` | E2E: зависит от Redis, мока платежа и/или окружения. |

### Ядро для быстрой проверки

Тесты из перечисленных ниже модулей покрывают оплаты и ключевые админские маршруты. Часть из них использует фикстуру `admin_auth` (логин админа); при частых прогонах возможен **429 Too Many Requests** на `/admin/auth/login`. Решение: один прогон за раз, либо отключение/ослабление rate-limit в тестовом окружении.

```bash
poetry run pytest tests/api/test_payments.py tests/api/test_admin_payment_gateway_credentials.py tests/services/test_clinic_payment_gateway_service.py tests/api/test_admin_omni_chat.py tests/api/test_owner_omni_audit.py tests/test_admin_create_doctor_patient.py -v
```

Минимальный набор **без вызова admin login** (только оплаты и сервис credentials):

```bash
poetry run pytest tests/api/test_payments.py tests/services/test_clinic_payment_gateway_service.py -v
```
