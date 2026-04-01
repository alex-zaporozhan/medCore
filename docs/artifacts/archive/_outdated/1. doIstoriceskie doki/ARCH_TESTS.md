# ARCH_TESTS — Архитектура автотестов Dental Booking MVP

**Проект:** Dental Booking System  
**Ссылки:** [ARCH_DENTAL_BOOKING.md](ARCH_DENTAL_BOOKING.md) | [ARCH_DENTAL_BOOKING_02_API.md](ARCH_DENTAL_BOOKING_02_API.md)

Документ задаёт структуру тестов, фикстуры, список smoke-эндпоинтов и один E2E-сценарий. По нему @DEV может реализовать фикстуры и тесты без уточнений по структуре и списку.

---

## 1. Стек

- **API-тесты:** pytest + pytest-asyncio + httpx (async).
- **Клиент:** `httpx.AsyncClient` с `ASGITransport(app=app)` для вызова FastAPI без реального HTTP.
- **UI-тесты:** не в MVP; при необходимости позже — pytest-playwright или React Testing Library для одного критичного сценария.

Конфигурация pytest (asyncio mode, маркеры) — в `pyproject.toml` в секции `[tool.pytest.ini_options]`.

---

## 2. Структура каталогов

```
<корень проекта>/
  tests/
    __init__.py
    conftest.py          # общие фикстуры: app, client, БД, seed, моки
    api/
      __init__.py
      test_health.py     # health (вне /api/v1)
      test_auth.py       # send-code, verify-code
      test_doctors.py    # GET /doctors
      test_services.py   # GET /services
      test_schedule.py   # GET /doctors/{id}/schedule
      test_bookings.py   # POST /patient/bookings, GET /patient/bookings
      test_payments.py   # POST /payments, POST /payments/webhook
    e2e/
      __init__.py
      test_booking_to_payment.py   # один E2E: запись → оплата (URL/статус)
```

- Корень тестов — `tests/` в корне проекта (рядом с `src/`).
- `conftest.py` — фикстуры приложения, клиента, тестовой БД, seed-данных, моков ЮKassa (и при необходимости SMS/Telegram).
- При необходимости позже: `tests/services/` для unit-тестов сервисов (сейчас не обязательно).

В `pyproject.toml` добавить (или продублировать в `pytest.ini`):

```ini
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
asyncio_default_fixture_loop_scope = "function"
```

---

## 3. Тестовая БД и фикстуры

### 3.1 Выбор: Testcontainers PostgreSQL + Redis

- **Вариант A (рекомендуемый):** Testcontainers — поднимаем PostgreSQL и Redis в контейнерах, перед тестами выставляем `DATABASE_URL` и `REDIS_URL`, применяем миграции (Alembic), делаем seed. Плюсы: полная совместимость с продакшеном (asyncpg, Redis), изоляция, не нужен внешний сервер. Минус: зависимость `testcontainers` + время старта контейнеров.
- **Вариант B:** Отдельная БД на уже запущенном PostgreSQL (например `dental_booking_test`), те же миграции и seed. Проще, но требует поднятого Postgres и Redis при запуске тестов.

Для MVP достаточно **одного** варианта; в документе описан вариант A. Если выбран B — в conftest вместо контейнеров подставляются URL из env (например `DATABASE_URL_TEST`, `REDIS_URL_TEST`).

### 3.2 Фикстуры (conftest.py)

- **`event_loop`** — одна петля на тест (стандартно для pytest-asyncio).
- **`test_db_url` / `test_redis_url`** — либо из Testcontainers (session scope), либо из env.
- **`app`** — экземпляр FastAPI. Важно: при использовании Testcontainers переменные `DATABASE_URL` и `REDIS_URL` должны быть установлены **до** первого импорта приложения (например, в session-scoped фикстуре, которая поднимает контейнеры и выставляет `os.environ`), затем `from src.main import app`.
- **`client`** — `httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")`.
- **`db_session`** — сессия БД для тестового кода (создание данных, проверки). Либо через `AsyncSessionLocal` с тестовым engine, либо через dependency override в app.
- **`seed_data`** — создаёт минимум: одну клинику, одного врача (с рабочими часами на завтра), одну услугу, одного пациента. Может возвращать словарь `{ "clinic_id", "doctor_id", "service_id", "patient_id" }` для использования в тестах.
- **Мок ЮKassa:** в тестах, где вызывается создание платежа, подменить вызов к внешнему API (patch `PaymentService.create_payment` или HTTP-клиент внутри `YooKassaClient`), чтобы возвращать фиксированный `payment_url` и не слать запросы в ЮKassa.
- **Мок SMS/Telegram:** для тестов уведомлений при необходимости подменять отправителей (например, patch `send_with_fallback` или конкретных sender’ов), чтобы не слать реальные сообщения.

### 3.3 Зависимости

- В `pyproject.toml` (dev): `pytest`, `pytest-asyncio`, `httpx` (уже есть в основном проекте).
- Для Testcontainers: `testcontainers` (пакеты `testcontainers[postgres]` или отдельно `tc-postgres`, плюс Redis при наличии образа).

---

## 4. Список smoke-эндпоинтов

Проверка: один тест на эндпоинт, ожидаемый HTTP-статус и при необходимости минимум полей в ответе.

| № | Метод | Путь | Ожидаемый статус | Проверка (минимум) |
|---|--------|------|-------------------|----------------------|
| 1 | GET | `/health` | 200 | Тело: `status == "ok"`, есть `service` |
| 2 | POST | `/api/v1/auth/send-code` | 204 | Body: `{"phone": "+79001234567"}` |
| 3 | POST | `/api/v1/auth/verify-code` | 200 | Body: `{"phone": "+79001234567", "code": "<код из Redis или мок>"}`; в ответе: `access_token`, `token_type`, `patient_id` |
| 4 | GET | `/api/v1/doctors` | 200 | Ответ — список; хотя бы один элемент с полями `id`, `full_name`, `is_active` |
| 5 | GET | `/api/v1/services` | 200 | Ответ — список; хотя бы один элемент с полями `id`, `name`, `price` |
| 6 | GET | `/api/v1/doctors/{doctor_id}/schedule?from=YYYY-MM-DD&to=YYYY-MM-DD` | 200 | Ответ — список слотов (например, поля `time`, `available` или аналог по текущей схеме) |
| 7 | POST | `/api/v1/patient/bookings` | 201 | Query/body: `patient_id`, `doctor_id`, `service_id`, `date`, `time`; в ответе: `id`, `status` (например `pending`) |
| 8 | POST | `/api/v1/payments/webhook` | 200 | Body — мок payload ЮKassa (например `{"type": "notification", "event": "payment.succeeded", "object": {"id": "...", "status": "succeeded", "metadata": {"booking_id": "..."}}}` или по актуальной схеме webhook); ответ: `{"status": "ok"}` |

Примечания:

- **verify-code:** в тестах код либо подставляется через мок Redis (записать код в Redis перед запросом), либо тест отправляет send-code и читает код из ответа/мока (если API отдаёт код в dev-режиме).
- **schedule:** `doctor_id` и диапазон дат взять из `seed_data`.
- **patient/bookings:** `patient_id`, `doctor_id`, `service_id` из seed; дата/время — из расписания (свободный слот) или фиксированные из seed.
- **payments:** создание платежа (POST `/api/v1/payments`) требует авторизации пациента (Bearer token); webhook — без авторизации, но с валидным телом.

---

## 5. Один E2E-сценарий: запись на приём до редиректа на оплату

**Цель:** убедиться, что цепочка от входа пациента до получения ссылки на оплату выполняется без ошибок.

**Шаги:**

1. **Health** — `GET /health` → 200, `status == "ok"`.
2. **Send code** — `POST /api/v1/auth/send-code` с `{"phone": "+79001234567"}` → 204.
3. **Verify code** — получить код из Redis (по ключу `auth:code:{clinic_id}:{phone}`) или из мока/заглушки; `POST /api/v1/auth/verify-code` с `{"phone": "+79001234567", "code": "..."}` → 200, сохранить `access_token` и `patient_id`.
4. **Doctors** — `GET /api/v1/doctors` → 200, взять первый `doctor_id` (или из seed).
5. **Services** — `GET /api/v1/services` → 200, взять первый `service_id` (или из seed).
6. **Schedule** — `GET /api/v1/doctors/{doctor_id}/schedule?from=...&to=...` (например завтра) → 200, выбрать первый свободный слот (дата + время).
7. **Create booking** — `POST /api/v1/patient/bookings` с заголовком `Authorization: Bearer {access_token}` и телом `{ "doctor_id", "service_id", "date", "time" }` (и при необходимости `patient_id` в query). Ожидание: 201, в ответе `id` записи, `status` (например `pending`).
8. **Create payment** — `POST /api/v1/payments` с `Authorization: Bearer {access_token}` и телом `{"booking_id": "<id из шага 7>"}` (и при необходимости `return_url`). Ожидание: 200, в ответе `payment_url` (строка) и при необходимости `provider_payment_id`. Проверка: `payment_url` непустой и (опционально) содержит ожидаемый домен (например test ЮKassa или мок-URL).

**Ожидаемый результат:** все запросы возвращают указанные коды; после шага 8 клиент может перенаправить пользователя по `payment_url` на оплату. В тесте достаточно проверить наличие и непустоту `payment_url` (и при использовании мока — что мок был вызван с нужным `booking_id`).

---

## 6. Готовые промпты для @DEV

Ниже — три отдельных промпта для пошаговой реализации.

---

### Промпт 1: Фикстуры

```
@DEV

Контекст: В проекте Dental Booking (FastAPI, asyncpg, Redis) нужно поднять автотесты. Архитектура тестов описана в docs/ARCH_TESTS.md.

Задача: Реализовать фикстуры в tests/conftest.py.

Сделай:
1. Тестовая БД и Redis: по ARCH_TESTS использовать Testcontainers (PostgreSQL + Redis) или тестовые URL из env (DATABASE_URL_TEST, REDIS_URL_TEST). Установить переменные окружения до импорта приложения (from src.main import app).
2. Приложение: фикстура app — экземпляр FastAPI (импорт после установки DATABASE_URL/REDIS_URL). При необходимости переопределить get_session так, чтобы сессия использовала тестовый engine.
3. Клиент: фикстура client — httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test").
4. Seed данных: фикстура seed_data — создаёт одну клинику, одного врача с рабочими часами на завтра, одну услугу, одного пациента; возвращает словарь с id (clinic_id, doctor_id, service_id, patient_id) для использования в тестах. Выполнять после применения миграций (Alembic upgrade или create_all для тестовой БД).
5. Мок ЮKassa: в тестах, где вызывается POST /payments, подменить вызов к внешнему API (patch YooKassaClient или PaymentService.create_payment), чтобы возвращать фиксированный payment_url и не слать запросы вовне.
6. Конфигурация pytest: asyncio_mode = "auto", testpaths = ["tests"] в pyproject.toml [tool.pytest.ini_options].

Код — полный, без TODO. Зависимости: при использовании Testcontainers добавить в dev-зависимости (например testcontainers).
```

---

### Промпт 2: Smoke-тесты

```
@DEV

Контекст: В docs/ARCH_TESTS.md задан список smoke-эндпоинтов для Dental Booking API.

Задача: Написать smoke-тесты по списку из раздела 4 ARCH_TESTS.md — один тест на эндпоинт.

Сделай:
1. tests/api/test_health.py — GET /health, статус 200, в теле status == "ok", есть поле service.
2. tests/api/test_auth.py — POST /api/v1/auth/send-code (тело {"phone": "+79001234567"}), ожидание 204. POST /api/v1/auth/verify-code: перед ним положить код в Redis (как в приложении) или использовать мок; запрос с phone и code, ожидание 200, в ответе access_token, token_type, patient_id.
3. tests/api/test_doctors.py — GET /api/v1/doctors, 200, список с полями id, full_name, is_active у элементов.
4. tests/api/test_services.py — GET /api/v1/services, 200, список с полями id, name, price.
5. tests/api/test_schedule.py — GET /api/v1/doctors/{doctor_id}/schedule?from=&to=, 200, структура слотов (по текущей API).
6. tests/api/test_bookings.py — POST /api/v1/patient/bookings с patient_id, doctor_id, service_id, date, time (данные из seed_data и расписания), ожидание 201, в ответе id, status.
7. tests/api/test_payments.py — POST /api/v1/payments/webhook с мок-телом ЮKassa (по формату из ARCH или текущей реализации), ожидание 200, в ответе status: ok.

Использовать фикстуры app, client, seed_data из conftest.py. Код — полный, без TODO.
```

---

### Промпт 3: Один E2E-тест

```
@DEV

Контекст: В docs/ARCH_TESTS.md описан E2E-сценарий «запись на приём до редиректа на оплату» (раздел 5).

Задача: Реализовать один E2E-тест в tests/e2e/test_booking_to_payment.py по шагам из ARCH_TESTS.md.

Сделай:
1. Последовательно выполнить: GET /health → POST auth/send-code → записать код в Redis или взять из мока → POST auth/verify-code, сохранить access_token и patient_id → GET /doctors → GET /services → GET /doctors/{id}/schedule → выбрать свободный слот → POST /patient/bookings с Bearer токеном → POST /payments с Bearer и booking_id (с моком ЮKassa).
2. Проверки: все запросы возвращают ожидаемые коды (200/201/204); ответ POST /payments содержит непустой payment_url.
3. Использовать фикстуры client, seed_data; при необходимости отдельная фикстура для кода в Redis (или мок AuthService).

Код — полный, один тестовый сценарий (один test_...), без TODO.
```

---

## Критерий готовности

По этому документу @DEV может реализовать:

1. Фикстуры (тестовая БД, app, client, seed_data, мок ЮKassa) без уточнений по структуре и списку.
2. Smoke-тесты по таблице эндпоинтов (раздел 4) — один тест на эндпоинт.
3. Один E2E-тест по сценарию из раздела 5.

Запуск: `poetry run pytest tests/` (или `pytest tests/`).
