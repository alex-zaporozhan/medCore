# ARCH_TESTS_FULL — Полная архитектура тестов Dental Booking

**Проект:** Dental Booking System MVP  
**Связь:** [ARCH_TESTS.md](ARCH_TESTS.md) (базовый список smoke/E2E), [ARCH_DENTAL_BOOKING_01_DB_AND_STRUCTURE.md](ARCH_DENTAL_BOOKING_01_DB_AND_STRUCTURE.md), [BUSINESS_LOGIC.md](BUSINESS_LOGIC.md)

Документ задаёт **полную карту тестирования** всех систем продукта: сущности, связи, эндпоинты, сценарии. По нему @DEV реализует тесты пошагово по файлу DEV_PROMPT_TESTS_FULL.md.

---

## 1. Сводка систем и связей

### 1.1 Ядро (клиника, врачи, пациенты, услуги)

| Сущность    | Связи | Критичные API |
|-------------|-------|----------------|
| **clinics** | —     | GET/POST/PUT/DELETE /api/v1/clinics |
| **doctors** | clinic_id | GET/POST/PUT/DELETE /api/v1/doctors, GET /api/v1/doctors/{id} |
| **patients**| clinic_id | GET/POST/PUT/DELETE /api/v1/patients, GET /api/v1/patients/{id} |
| **services**| clinic_id | GET/POST/PUT/DELETE /api/v1/services, GET /api/v1/public/{clinic_id}/services |

### 1.2 Аутентификация и SMS

| Сущность / система | Связи | Критичные API |
|--------------------|-------|----------------|
| **patient_auth_codes** | patient_id | POST /api/v1/auth/send-code, POST /api/v1/auth/verify-code |
| Redis (код по телефону) | clinic_id, phone | Код для verify-code хранится в Redis |

### 1.3 Запись и оплата

| Сущность    | Связи | Критичные API |
|-------------|-------|----------------|
| **bookings**| clinic_id, patient_id, doctor_id, service_id | GET/POST/DELETE /api/v1/patient/bookings, PUT status |
| **payments**| booking_id | POST /api/v1/payments, POST /api/v1/payments/webhook |
| **schedule**| doctor_id, working_hours, absence | GET /api/v1/doctors/{id}/schedule, GET /api/v1/schedule/slots |

### 1.4 Чат пациент ↔ администрация

| Сущность         | Связи | Критичные API (пациент) |
|------------------|-------|---------------------------|
| **conversations**| clinic_id, patient_id | GET /api/v1/patient/chat/conversation?patient_id= |
| **chat_messages**| conversation_id, clinic_id | GET /api/v1/patient/chat/conversation/messages?patient_id=, **POST /api/v1/patient/chat/conversation/messages?patient_id=** (отправка сообщения), POST mark-read |

| Критичные API (админ) |
|------------------------|
| GET /api/v1/admin/chat/conversations |
| GET/POST /api/v1/admin/chat/conversations/{id}/messages |
| POST assign, POST mark-read |

### 1.5 Админка: расписание, предоплата, очередь, отчёты

| Система     | Эндпоинты |
|-------------|-----------|
| **admin_schedule** | GET /api/v1/admin/schedule |
| **admin_doctor_schedule** | GET/POST/PUT/DELETE working-hours, GET/POST/DELETE absence |
| **admin_prepayment** | GET/POST/PUT/DELETE /api/v1/admin/{clinic_id}/prepayment/policies |
| **admin_waitlist** | GET/POST/PUT/DELETE waitlist, GET/PUT queue-policy |
| **admin_reports** | GET dashboard, no-show, revenue, owner-dashboard, plan |

### 1.6 Recall и маркетинг

| Система     | Эндпоинты |
|-------------|-----------|
| **admin_recall** | CRUD recall-шаблоны, CRUD recall-кампании, run/status |
| **admin_marketing** | CRUD posts, CRUD stories по clinic_id |
| **public_marketing** | GET /api/v1/public/{clinic_id}/feed, GET /api/v1/public/{clinic_id}/stories |

### 1.7 Синхронизация и прочее

| Система     | Эндпоинты |
|-------------|-----------|
| **csv_sync** | POST import, GET jobs |
| **reports** (patient) | GET /api/v1/patient/reports/... (если есть) |

---

## 2. Матрица тестов (что покрыть)

### 2.1 Уже есть (tests/)

- **conftest.py:** event_loop, init_db, truncate_tables, seed_data (clinic, doctor, service, patient), redis_client, client.
- **api:** test_health, test_auth (send-code, verify-code), test_doctors, test_services, test_schedule, test_bookings, test_payments (webhook).
- **e2e:** test_booking_to_payment, test_frontend_pages (Playwright).
- **test_admin_create_doctor_patient.py:** создание врача/пациента с default clinic.

### 2.2 Обязательно добавить для диагностики и полноты

| № | Модуль | Тест | Ожидание |
|---|--------|------|----------|
| 1 | **patient_chat** | GET /api/v1/patient/chat/conversation?patient_id={seed} | 200, conversation_id |
| 2 | **patient_chat** | GET /api/v1/patient/chat/conversation/messages?patient_id={seed} | 200, items, next_cursor |
| 3 | **patient_chat** | POST /api/v1/patient/chat/conversation/messages?patient_id={seed} body={"body":"test"} | **201**, MessageDto (id, body, created_at, is_mine) |
| 4 | **patient_chat** | POST mark-read (опционально) | 204 |
| 5 | **admin_reports** | GET dashboard / no-show / revenue (если есть admin auth в тестах) | 200 или 401 |
| 6 | **public_marketing** | GET feed / stories для clinic_id из seed | 200, список или пустой |

При падении пункта 3 с 500 в выводе pytest будет полный traceback причины (connection is closed, ValidationError, отсутствие таблицы и т.д.).

### 2.3 Зависимости фикстур для чата

- **seed_data** уже создаёт clinic_id, patient_id. Этого достаточно для patient chat (get_default_clinic_id берёт первую клинику, patient_id передаётся в query).
- Таблицы **conversations**, **chat_messages** должны существовать в тестовой БД: либо через миграции (alembic upgrade head для test DB), либо через Base.metadata.create_all (если все модели зарегистрированы). В текущем conftest используется create_all — нужно убедиться, что в Base.metadata импортированы сущности Conversation и ChatMessage (через импорт entities или через миграции).

---

## 3. Тестовая БД и миграции

- **Вариант A:** Test DB с именем, содержащим `test` (dental_booking_test). Перед тестами: миграции `alembic upgrade head` к этой БД ИЛИ create_all. В conftest уже используется create_all; если таблицы чата не создаются (отдельные миграции), нужно либо импортировать модели чата в место, откуда собирается Base.metadata, либо применять миграции к тестовой БД.
- **Вариант B:** Явно в conftest после create_all выполнить создание таблиц conversations и chat_messages по схеме из ARCH_CHAT_PATIENT_ADMIN (если они не входят в Base.metadata при create_all).

Рекомендация: убедиться, что все доменные сущности (включая Conversation, ChatMessage) зарегистрированы в Base.metadata (например, импорт всех entity в conftest или в src.infrastructure.database.base), тогда create_all создаст и таблицы чата.

---

## 4. Критерий готовности

- Все smoke-тесты из ARCH_TESTS.md проходят.
- Тесты patient chat (GET conversation, GET messages, **POST message** — ключевой) добавлены и проходят при исправной реализации; при текущей ошибке 500 — pytest выдаёт точный traceback.
- При необходимости добавлены тесты admin_reports (smoke) и public_marketing (smoke) с использованием seed_data.

---

## 5. Запуск тестов (обязательное условие)

Тесты используют тестовую БД, имя которой **должно содержать "test"** (например `dental_booking_test`), иначе conftest откажет в TRUNCATE из соображений безопасности.

```powershell
# Создать тестовую БД (один раз): через psql или docker exec
# docker exec dental_booking_postgres psql -U postgres -c "CREATE DATABASE dental_booking_test;"

# Запуск (в корне проекта)
set DATABASE_URL_TEST=postgresql+asyncpg://postgres:ПАРОЛЬ@localhost:5432/dental_booking_test
set REDIS_URL_TEST=redis://localhost:6379/0
poetry run pytest tests/ -v --tb=short
```

Без `DATABASE_URL_TEST` будет ошибка: "Refusing to TRUNCATE: DATABASE_URL database name must contain 'test'".

---

## 6. Ссылка на промпт для @DEV

Пошаговое задание для реализации тестов: **[DEV_PROMPT_TESTS_FULL.md](DEV_PROMPT_TESTS_FULL.md)**. Выполнять to-dos по порядку; после реализации запуск с тестовой БД (п. 5).
