## DEV_PROMPTS_MARKETING_ATTRIBUTION — Сквозная аналитика и UTM

> Роли: @DEV, @ARCH, @QA.  
> Читается после: `ARCH_MARKETING_ATTRIBUTION.md`, `ARCH_CRM_KANBAN.md`, `ARCH_ERP_FINANCE_AND_INVENTORY.md`, `LANDING_WEB_FRONTEND.md`, `TECH_PASSPORT_BACKEND.md`, `TECH_PASSPORT_FRONTEND.md`.

---

## 1. Цели реализации

- Связать путь клиента от источника трафика до денег:
  - UTM/канал/кампания → `VisitAttribution` → `LeadCard` → `Booking` → `FinancialTransaction`.
- Дать владельцу клиники отчёты:
  - выручка и ключевые конверсии по каналам/кампаниям;
  - базовый ROI (с возможностью указать рекламные затраты).

---

## 2. Backend — модель данных и миграции

### 2.1. TrafficSource и Campaign

- В `src/domain/entities/`:
  - `traffic_source.py`
  - `campaign.py`

Поля — по `ARCH_MARKETING_ATTRIBUTION.md` (clinic_id, code, name, external_id, budget_planned, даты начала/конца).

### 2.2. VisitAttribution

- В `src/domain/entities/`:
  - `visit_attribution.py`:
    - clinic_id, patient_id | None, lead_id | None;
    - utm_* поля, `landing_page`, `session_id`, timestamps;
    - связи с `TrafficSource`/`Campaign`.

### 2.3. Расширения LeadCard и FinancialTransaction

- В сущностях CRM/ERP:
  - `LeadCard`:
    - поле `visit_attribution_id: UUID | None` (+ опциональный кэш utm‑полей);
  - `FinancialTransaction`:
    - поля `lead_id: UUID | None`, `visit_attribution_id: UUID | None`.

### 2.4. Alembic‑миграции

- Создать таблицы:
  - `traffic_sources`, `campaigns`, `visit_attributions`;
  - добавить недостающие поля в `lead_cards`, `financial_transactions`.
- Индексы:
  - по `clinic_id` на все новые таблицы;
  - на `visit_attributions`: `clinic_id + created_at`, `clinic_id + session_id`;
  - на `financial_transactions`: `clinic_id + visit_attribution_id`.

---

## 3. Потоки атрибуции

### 3.1. Лендинг → лид (создание VisitAttribution)

- Расширить backend‑эндпоинт, принимающий лиды с лендинга (см. `LANDING_WEB_FRONTEND.md` и текущий API `/api/leads`):
  - добавить поля:
    - utm_source/medium/campaign/content/term;
    - `landing_page`, `anchor`, session‑идентификатор.
- При создании `LeadCard`:
  - создавать `VisitAttribution`:
    - сразу заполнять `lead_id`;
    - `patient_id` пока `NULL`.

### 3.2. PWA/чат → пациент

- В PWA/OmniChat:
  - при первой авторизации/общении клиента, пришедшего с лендинга:
    - пробрасывать session‑ID/utm‑данные в backend.
- Backend:
  - находить соответствующий `VisitAttribution` по session_id/utm;
  - проставлять `patient_id` при создании `Patient`.

### 3.4. Правила атрибуции (first touch)

- Для первой версии зафиксировать **first touch**:
  - `VisitAttribution`, созданный при первом обращении (лендинг/первый лид), считается источником для:
    - всех последующих лидов, записей и визитов пациента, пока не появится иное требование бизнеса;
  - последующие utm‑события могут логироваться, но не меняют основную связь выручки с источником.

### 3.3. Оплата/ERP → привязка к выручке

- В ERP‑узле `process_booking_completed`:
  - при создании `FinancialTransaction`:
    - если у `Booking.patient_id` или `LeadCard` есть `VisitAttribution`:
      - заполнять `financial_transaction.visit_attribution_id` и `lead_id`.

---

## 4. Backend — агрегирующие отчёты

### 4.1. Сервис атрибуции

- В `src/application/services/marketing_attribution_service.py`:
  - методы для выборок/агрегаций:
    - `get_channel_summary(clinic_id, period, filters)`:
      - группировка по `TrafficSource`/`Campaign`:
        - `leads_count`, `bookings_count`, `completed_bookings_count`,
        - `unique_patients_count`,
        - `revenue_sum` (по `FinancialTransaction` с типом `income`),
        - `avg_check`,
        - `ad_spend` (рекламные затраты по кампании/каналу),
        - `roi` (рассчитанный как `revenue_sum / ad_spend` при наличии затрат).
    - API/механизм для учёта рекламных затрат (`ad_spend`):
      - хранение планового/фактического бюджета в `Campaign`;
      - возможность обновлять фактические затраты через админский интерфейс или импорт.

### 4.2. Новый роутер `admin_marketing_attribution.py`

- Эндпоинты:
  - `GET /api/v1/admin/attribution/summary`:
    - параметры: период, фильтры по источнику/кампании;
    - ответ — агрегированные метрики по каналам.
  - `GET /api/v1/admin/attribution/campaigns`:
    - список кампаний и базовых метрик.
  - `POST /api/v1/admin/attribution/campaigns`:
    - создание/обновление кампаний и плановых бюджетов.
- RBAC:
  - доступ только ролям `Owner`/`Manager` (через `require_permissions`, напр. `view_marketing_analytics`, `manage_marketing_campaigns`).

---

## 5. Frontend — лендинг и админка

### 5.1. Лендинг

- На основе `LANDING_WEB_FRONTEND.md`:
  - реализовать единый helper/hook для работы с utm:
    - например, `useUtmTracking` + утилиту `getCurrentUtm()`:
      - при монтировании hero секции:
        - читать utm‑параметры из URL и сохранять в `localStorage`/state через helper;
      - при отправке форм (`submitLead`/`/api/leads`):
        - добавлять utm‑поля и `landing_page`/`anchor` в payload, переиспользуя один и тот же helper;
  - не дублировать логику чтения/записи utm по разным компонентам.

### 5.2. PWA

- При первой авторизации пациента:
  - отправлять сохранённый utm/session идентификатор в backend;
  - после связывания с `VisitAttribution` данные можно удалить из локального хранилища.

### 5.3. Админка: раздел «Analytics»

- В разделе `Analytics` (см. ARCH_FRONTEND_BUSINESS_OS_UX):
  - вкладка «Маркетинг и атрибуция»:
    - таблица/дашборд по каналам:
      - колонки: Лиды, Записи, Дошли, Выручка, Средний чек, ROI;
    - фильтры по периоду, источнику, кампании;
    - графики/чарты (по необходимости) для трендов.
- Типы/хуки:
  - DTO для сводного отчёта и кампаний;
  - `useMarketingAttributionSummary`, `useMarketingCampaigns`.

### 5.4. Связь с CRM/ERP отчётами

- Убедиться, что:
  - отчёты CRM (по лидам) и ERP (по выручке) могут:
    - фильтровать и группировать данные по `TrafficSource`/`Campaign`;
    - использовать `visit_attribution_id` и utm‑поля как дополнительные разрезы в существующих отчётах.

---

## 6. Тестирование

### 6.1. Backend

- Юнит‑тесты:
  - логика создания `VisitAttribution` и связывания с `LeadCard`/`Patient`;
  - агрегирующие функции `marketing_attribution_service`.
- Интеграционные:
  - полный сценарий:
    - переход с utm‑ссылкой → отправка лида → создание `VisitAttribution`/`LeadCard`;
    - регистрация пациента/запись → связь с атрибуцией;
    - успешная оплата/завершение визита → `FinancialTransaction` с привязкой к атрибуции;
    - запрос отчёта — корректные метрики по каналу.

### 6.2. Frontend

- Проверка:
  - корректного захвата и отправки utm‑данных с лендинга;
  - отображения отчётов в админке и базовой фильтрации.

---

## 7. Порядок выполнения для @DEV

1. Добавить сущности `TrafficSource`, `Campaign`, `VisitAttribution` и расширить `LeadCard`/`FinancialTransaction`.
2. Реализовать миграции Alembic.
3. Реализовать поток лендинг → `VisitAttribution` → `LeadCard`.
4. Реализовать связывание PWA/пациента с атрибуцией.
5. Интегрировать атрибуцию в ERP‑узел `Booking.completed` и финансовые транзакции.
6. Реализовать `marketing_attribution_service` и API `admin_marketing_attribution`.
7. Обновить лендинг и админку (раздел Analytics) под новый модуль.
8. Написать и прогнать backend и frontend тесты.

