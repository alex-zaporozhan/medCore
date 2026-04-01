# ARCH_DENTAL_BOOKING — Часть 1: Схема БД и структура проекта (историческая версия)

**Проект:** Dental Booking System MVP | **Режим:** SAAS  
**Статус:** этот документ фиксирует одну из ранних версий схемы БД и структуры проекта.

> Актуальная архитектура и срез по коду сейчас описаны в  
> `HANDOFF_AI_PRODUCT_AND_TECH_CURRENT.md` и `HANDOFF_AI_ONEPAGER.md`.
> При расхождениях между этим файлом и кодом/актуальным HANDOFF приоритет у кода и HANDOFF.

---

## 1. Схема БД (таблицы, поля, индексы, связи)

### 1.1 Общие принципы

- Одна клиника на инстанс (multi-tenancy за скобками MVP).
- Везде soft delete: `deleted_at TIMESTAMPTZ NULL`.
- Таймстемпы: `created_at`, `updated_at` (TIMESTAMPTZ, по UTC).
- Все внешние ключи с индексами.
- Все id — `UUID` (генерируются на backend).

### 1.2 Таблица `clinics`

Используется даже при одной клинике, чтобы упростить возможный рост.

- `id UUID PK`
- `name TEXT NOT NULL`
- `phone TEXT`
- `email TEXT`
- `address TEXT`
- `workday_start TIME NOT NULL DEFAULT '09:00'`
- `workday_end TIME NOT NULL DEFAULT '21:00'`
- `slot_duration_minutes INT NOT NULL DEFAULT 30`
- `prepayment_amount NUMERIC(10,2) NOT NULL DEFAULT 500`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `deleted_at TIMESTAMPTZ NULL`

Индексы:
- `idx_clinics_deleted_at`

### 1.3 Таблица `admins`

Один админ в MVP, но схема поддерживает больше.

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)`
- `email TEXT NOT NULL UNIQUE`
- `password_hash TEXT NOT NULL`
- `full_name TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `deleted_at TIMESTAMPTZ NULL`

Индексы:
- `idx_admins_clinic_id`

### 1.4 Таблица `doctors`

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)`
- `full_name TEXT NOT NULL`
- `specialization TEXT NOT NULL`
- `photo_url TEXT`
- `rating NUMERIC(2,1) DEFAULT 0.0` (0.0–5.0)
- `experience_years INT`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `deleted_at TIMESTAMPTZ NULL`

Индексы:
- `idx_doctors_clinic_id`
- `idx_doctors_is_active`

### 1.5 Таблица `services`

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)`
- `name TEXT NOT NULL`
- `category TEXT NOT NULL` (терапия/хирургия/ортодонтия/...)
- `description TEXT`
- `price NUMERIC(10,2) NOT NULL`
- `duration_minutes INT NOT NULL DEFAULT 30`
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `deleted_at TIMESTAMPTZ NULL`

Индексы:
- `idx_services_clinic_id`
- `idx_services_is_active`

### 1.6 Таблица `patients`

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)`
- `phone TEXT NOT NULL`
- `full_name TEXT`
- `email TEXT`
- `birth_date DATE`
- `telegram_chat_id TEXT NULL`
- `preferred_channel TEXT NOT NULL DEFAULT 'sms'` (`sms`|`telegram`|`email`)
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `deleted_at TIMESTAMPTZ NULL`

Индексы:
- `ux_patients_clinic_phone UNIQUE (clinic_id, phone)` — быстрый поиск по телефону.
- `idx_patients_clinic_id`

### 1.7 Таблица `patient_auth_codes`

Для входа по SMS-коду.

- `id UUID PK`
- `patient_id UUID NOT NULL FK → patients(id)`
- `code TEXT NOT NULL`
- `expires_at TIMESTAMPTZ NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `consumed_at TIMESTAMPTZ NULL`

Индексы:
- `idx_auth_codes_patient_id`
- `idx_auth_codes_expires_at`

### 1.8 Таблица `doctor_working_hours`

Базовое расписание по дням недели (шаблон).

- `id UUID PK`
- `doctor_id UUID NOT NULL FK → doctors(id)`
- `weekday INT NOT NULL` (0=Пн, 6=Вс)
- `start_time TIME NOT NULL`
- `end_time TIME NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

Индексы:
- `idx_working_hours_doctor_weekday (doctor_id, weekday)`

### 1.9 Таблица `bookings`

Основная бизнес-сущность.

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)`
- `patient_id UUID NOT NULL FK → patients(id)`
- `doctor_id UUID NOT NULL FK → doctors(id)`
- `service_id UUID NOT NULL FK → services(id)`
- `appointment_date DATE NOT NULL`
- `appointment_time TIME NOT NULL`
- `status TEXT NOT NULL` (`pending`|`confirmed`|`cancelled`|`completed`|`no_show`)
- `prepayment_amount NUMERIC(10,2) NOT NULL DEFAULT 0`
- `payment_id UUID NULL FK → payments(id)`
- `notes TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `deleted_at TIMESTAMPTZ NULL`

Индексы (из @PERF):
- `idx_bookings_patient_date (patient_id, appointment_date)` — история пациента.
- `idx_bookings_doctor_date (doctor_id, appointment_date)` — расписание врача.
- `idx_bookings_status_date (status, appointment_date)` — фильтры по статусу.
- `idx_bookings_clinic_date (clinic_id, appointment_date)` — отчёты.

Ограничения:
- Уникальность слота на врача:
  `UNIQUE (doctor_id, appointment_date, appointment_time)`
  (админские override операции делают soft delete / перезапись с логированием).

### 1.10 Таблица `payments`

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)`
- `booking_id UUID NOT NULL FK → bookings(id)`
- `provider TEXT NOT NULL` (в MVP всегда `yookassa`)
- `provider_payment_id TEXT NOT NULL` (ID платежа в ЮKassa)
- `amount NUMERIC(10,2) NOT NULL`
- `currency TEXT NOT NULL DEFAULT 'RUB'`
- `status TEXT NOT NULL` (`pending`|`succeeded`|`canceled`|`refunded`)
- `metadata JSONB` (сырой ответ провайдера)
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

Индексы:
- `ux_payments_provider_id UNIQUE (provider, provider_payment_id)`
- `idx_payments_booking_id`

### 1.11 Таблица `notifications`

Хранит историю отправленных уведомлений.

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)`
- `patient_id UUID NULL FK → patients(id)`
- `admin_id UUID NULL` (для уведомлений администратору; в текущем MVP без FK, так как таблица `admins` будет добавлена позже)
- `booking_id UUID NULL FK → bookings(id)`
- `channel TEXT NOT NULL` (`telegram`|`sms`|`email`)
- `template TEXT NOT NULL` (`reminder_24h`|`reminder_2h`|`new_booking_admin`|`custom`)
- `payload JSONB NOT NULL` (готовый текст, параметры)
- `status TEXT NOT NULL` (`pending`|`sent`|`failed`)
- `error TEXT NULL`
- `sent_at TIMESTAMPTZ NULL`
- `created_at TIMESTAMPTZ NOT NULL`

Индексы:
- `idx_notifications_booking_id`
- `idx_notifications_patient_id`

### 1.12 Таблица `csv_import_jobs`

Для отслеживания CSV-импорта расписания.

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)`
- `file_name TEXT NOT NULL`
- `status TEXT NOT NULL` (`pending`|`processing`|`completed`|`failed`)
- `total_rows INT`
- `processed_rows INT`
- `error TEXT`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

Индексы:
- `idx_csv_jobs_clinic_id`

---

## 2. Структура проекта (Clean Architecture)

Корень backend-проекта:

```text
src/
  domain/
    entities/
      clinic.py
      admin.py
      doctor.py
      service.py
      patient.py
      booking.py
      payment.py
      notification.py
      csv_import_job.py
    interfaces/
      repositories/
        clinic_repository.py
        admin_repository.py
        doctor_repository.py
        service_repository.py
        patient_repository.py
        booking_repository.py
        payment_repository.py
        notification_repository.py
        csv_import_job_repository.py
      notification_sender.py  # абстракция каналов уведомлений
      payment_provider.py     # абстракция платёжного провайдера
    exceptions/
      domain_exceptions.py

  application/
    dto/
      clinic_dto.py
      admin_dto.py
      doctor_dto.py
      service_dto.py
      patient_dto.py
      booking_dto.py
      payment_dto.py
      notification_dto.py
      auth_dto.py
    services/
      clinic_service.py
      auth_service.py
      doctor_service.py
      service_service.py
      patient_service.py
      booking_service.py
      schedule_service.py
      payment_service.py
      notification_service.py
      report_service.py
      csv_import_service.py

  infrastructure/
    database/
      base.py          # AsyncSession, engine, session factory
      clinic_repo_impl.py
      admin_repo_impl.py
      doctor_repo_impl.py
      service_repo_impl.py
      patient_repo_impl.py
      booking_repo_impl.py
      payment_repo_impl.py
      notification_repo_impl.py
      csv_import_job_repo_impl.py
    external_apis/
      yookassa_client.py
      telegram_client.py
      sms_client.py
      email_client.py
    messaging/
      celery_app.py
      tasks/
        notifications.py
        reminders.py
        csv_import.py

  api/
    v1/
      dependencies.py
      routers/
        auth.py
        clinics.py
        admins.py
        doctors.py
        services.py
        patients.py
        bookings.py
        schedule.py
        payments.py
        notifications.py
        reports.py
        csv_sync.py
    middleware.py

  core/
    config.py
    logging.py

  main.py
```

Ключевые моменты:
- `domain` ничего не знает о FastAPI/SQLAlchemy — только модели и интерфейсы.
- `application` — бизнес-логика на уровне use-cases.
- `infrastructure` — конкретные реализации репозиториев, клиентов к внешним API, Celery.
- `api` — HTTP слой (FastAPI), только преобразует HTTP → DTO → services.
