## DEV_TODOS_MARKETING_ATTRIBUTION_GAPS — хвосты по Marketing Attribution (UTM → деньги → ROI)

> Основано на `ARCH_MARKETING_ATTRIBUTION.md` и фактическом коде (entities/migrations/service/admin API + frontend UTM tracking).

---

## 1. Связка UTM/session → VisitAttribution (сбор и сохранение)

- [ ] **1.1. Бэкенд‑точка входа для записи UTM**
  - На фронте есть `utmTracking.ts`, но нужен надёжный backend‑flow:
    - создание `VisitAttribution` по `session_id` + utm + landing_page + anchor;
    - идемпотентность (повторный вызов не плодит записи).

- [ ] **1.2. Связывание с Patient/Lead**
  - По ARCH: при конверсии контакт → пациент/лид, `VisitAttribution` должен получить `patient_id`/`lead_id`.
  - Сейчас связывание частично делается в CRM handler (через поиск attribution по contact), но нужен единый контракт:
    - что является ключом (session_id vs contact_id vs patient_id);
    - как выбирается first‑touch attribution, если есть несколько сессий.

---

## 2. Связка VisitAttribution → FinancialTransaction (деньги)

- [ ] **2.1. Заполнение `FinancialTransaction.visit_attribution_id`**
  - Миграция добавила поле, но нужно гарантировать, что при создании `FinancialTransaction`:
    - проставляется `visit_attribution_id` (и при необходимости `lead_id`) для правильной атрибуции выручки.
  - Особо важны edge‑кейсы:
    - повторные визиты пациента спустя месяцы;
    - пациенты без attribution (offline/referral).

- [ ] **2.2. Конфликт “CRM actual_value vs ERP revenue”**
  - Требуется договориться, что источник правды по выручке — ERP (`FinancialTransaction`), а CRM хранит кэш/оценку.
  - Тогда отчёты attribution должны опираться на ERP‑суммы, а CRM — только для воронки.

---

## 3. Отчёты ROI и качество трафика

- [ ] **3.1. Корректность метрик `completed_bookings_count`**
  - В текущем `MarketingAttributionService` `completed_bookings_count` считается тем же выражением, что и `bookings_count` (distinct по `ft.booking_id`).
  - Нужен источник “completed”:
    - либо join с `Booking.status == completed`;
    - либо отдельный критерий в ERP/Finance.

- [ ] **3.2. Учёт затрат на рекламу (ad_spend)**
  - Есть поля budgets в `Campaign`/`TrafficSource`, но нужна бизнес‑модель:
    - план/факт, период, валюта, возможность ручного ввода;
    - расчёт ROI и CAC.

- [ ] **3.3. Drill‑down в детали**
  - Для премиального UX требуются эндпоинты/страницы:
    - список лидов/визитов/транзакций по выбранному каналу/кампании;
    - экспорт для владельца (CSV).

---

## 4. Frontend — Analytics / Marketing

- [ ] **4.1. Админ‑страницы атрибуции**
  - В админке нужно добавить:
    - страницу отчёта ROI (таблица по каналам/кампаниям + фильтр периода);
    - управление кампаниями и бюджетами (CRUD + валидация).

- [ ] **4.2. Сквозная интеграция с лендингом**
  - Убедиться, что:
    - лендинг при отправке `/api/leads` реально включает `session_id` и utm‑данные;
    - при логине/регистрации пациента `session_id` пробрасывается в backend для связывания attribution.

---

## 5. RBAC и безопасность

- [ ] **5.1. Ограничение доступа**
  - Проверить:
    - отчёты доступны только ролям с `view_marketing_analytics`;
    - управление кампаниями — `manage_marketing_campaigns`.
  - Добавить тесты 401/403 для каждого эндпоинта attribution.

- [ ] **5.2. PII‑политика**
  - Attribution‑данные не содержат ПДн, но drill‑down может выводить пациентов.
  - Нужно:
    - определить, какие поля пациента показывать в отчётах владельца/менеджера;
    - гарантировать маскировку/минимизацию (например, телефон частично).

