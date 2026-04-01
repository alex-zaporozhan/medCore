## DEV_PROMPTS_LOYALTY_SUBSCRIPTIONS — Лояльность, абонементы и кошелёк

> Роли: @DEV, @ARCH, @QA.  
> Читается после: `ARCH_LOYALTY_SUBSCRIPTIONS.md`, `BUSINESS_LOGIC_V2.md`, `ARCH_ERP_FINANCE_AND_INVENTORY.md`, `ARCH_CRM_KANBAN.md`, `TECH_PASSPORT_BACKEND.md`, `TECH_PASSPORT_FRONTEND.md`.

---

## 1. Цели реализации

- Ввести модуль лояльности, который:
  - позволяет продавать **подписки/пакеты** (`SubscriptionPackage`, `CustomerSubscription`, `SubscriptionUsage`);
  - даёт **виртуальный кошелёк** (`Wallet`, `WalletTransaction`) для кэшбэка/баллов;
  - интегрирован с Booking/Payments/ERP/CRM и поддерживает smart‑recall.
- Обеспечить:
  - корректный финансовый учёт (без «удвоения» выручки);
  - возможность отображать пакеты и баллы в админке и PWA пациента.

---

## 2. Backend — модель данных и миграции

### 2.1. Сущности подписок

- В `src/domain/entities/`:
  - `subscription_package.py`
  - `customer_subscription.py`
  - `subscription_usage.py`

Поля — по `ARCH_LOYALTY_SUBSCRIPTIONS.md` (clinic_id, patient_id, status, остатки, `validity_days`, связи с `Payment`/`Booking` и т.д.).

### 2.2. Сущности кошелька

- В `src/domain/entities/`:
  - `wallet.py`
  - `wallet_transaction.py`
  - `loyalty_policy.py` — политика лояльности клиники (Phase 1 — можно хранить 1 запись на клинику).

Поля `LoyaltyPolicy` — по `ARCH_LOYALTY_SUBSCRIPTIONS.md`:

- `clinic_id`;
- `cashback_percent`;
- `min_check_for_cashback`;
- `allow_pay_with_points`;
- `max_points_share`;
- `points_expire_days`.

### 2.3. Alembic‑миграции

- Создать миграцию с таблицами:
  - `subscription_packages`, `customer_subscriptions`, `subscription_usages`;
  - `wallets`, `wallet_transactions`;
  - `loyalty_policies` (если политика выделена в отдельную таблицу, а не в настройки клиники).
- Для всех таблиц:
  - индексы по `clinic_id`;
  - `wallets`: уникальный индекс `(clinic_id, patient_id)` (один кошелёк на пациента в клинике на Phase 1);
  - `customer_subscriptions`: индексы по `patient_id`, `status`, `expires_at`.

---

## 3. Backend — сервисы лояльности

### 3.1. Репозитории

- В `src/domain/interfaces/repositories/`:
  - `loyalty_repository.py`:
    - работа с `SubscriptionPackage`, `CustomerSubscription`, `SubscriptionUsage`, `Wallet`, `WalletTransaction`.
- В `src/infrastructure/database/`:
  - реализации репозитория.

### 3.2. `loyalty_service`

- В `src/application/services/loyalty_service.py`:
  - операции:
    - управление пакетами:
      - CRUD по `SubscriptionPackage`;
    - покупка пакета:
      - `purchase_subscription(patient_id, package_id, payment_info, ctx)`:
        - создание `CustomerSubscription` с остатками и статусом;
        - связка с оплатой (через ERP/Payment);
    - активация и истечение:
      - методы для установки `activated_at`, расчёта `expires_at`;
    - использование пакета:
      - `use_subscription_for_booking(booking_id, subscription_id, ...)`:
        - создание `SubscriptionUsage`;
        - уменьшение `remaining_visits`/`remaining_amount`;
        - пометка `Booking` как оплаченной пакетом.

### 3.3. `wallet_service`

- В `src/application/services/wallet_service.py`:
  - обеспечить:
    - idempotent‑политику создания кошелька (get_or_create_wallet);
    - защиту от гонок при одновременном списании/начислении (использовать транзакции и блокировки строк/оптимистичные версии);
    - операции:
      - `earn_points(patient_id, clinic_id, amount, booking_id | subscription_id, ctx)`;
      - `spend_points(patient_id, clinic_id, amount, ctx)` (с проверкой лимитов);
      - `expire_points(...)` — для периодического джоба.

### 3.4. Обработка конфликтных сценариев

- В логике сервисов предусмотреть и явно задокументировать поведение при:
  - нескольких активных `CustomerSubscription`, подходящих под один и тот же визит:
    - правила приоритета (например: сначала более «узкоспециализированный» пакет, затем общий баланс);
  - недостаточном остатке (`remaining_visits`/`remaining_amount`):
    - возврат управляемой бизнес‑ошибки (`InsufficientSubscriptionBalance`);
    - запрет частичного списания, если это не поддерживается бизнес‑логикой;
  - истёкшем пакете (`status="expired"` или `expires_at < now`):
    - запрет использования и предложение альтернатив (другой пакет/разовая оплата).

---

## 4. Интеграция с Booking/ERP/Payments

### 4.1. Покупка пакета

- При успешной оплате пакета:
  - через существующий Payment/ERP‑узел:
    - создать `CustomerSubscription` (внутри или из хендлера события платежа);
    - связать с `Payment`/`FinancialTransaction` (по `payment_id`).

### 4.2. Использование пакета при записи

- В `BookingService`/сервисе обработки записи:
  - при создании/подтверждении `Booking`:
    - при наличии активных `CustomerSubscription`:
      - дать возможность выбрать пакет (через API и фронт);
      - вызвать `loyalty_service.use_subscription_for_booking(...)`;
      - пометить `Booking` как «оплачено подпиской» (поле или флаг).

### 4.3. Начисление и списание кэшбэка

- В узле `Booking.completed` (см. DEV_PROMPTS_ERP_FINANCE_AND_INVENTORY):
  - после успешного ERP‑обработчика:
    - вызвать `wallet_service.earn_points(...)` с суммой по `LoyaltyPolicy`;
  - при оплате баллами:
    - списание происходит до создания финтранзакции (скидка учтена в ERP);
    - ERP‑узел должен опираться на факт оплаты пакета/баллами, чтобы не «удваивать» выручку (подробности — в `DEV_PROMPTS_ERP_FINANCE_AND_INVENTORY.md` и интеграционных тестах ERP+Loyalty).

---

## 5. Smart‑recall поверх лояльности

### 5.1. Новые триггеры для Recall/Tasks

- Реализовать обработчики/джобы, которые:
  - находят:
    - `CustomerSubscription` близкие к `expires_at`;
    - активные подписки с `remaining_visits > 0` при отсутствии визитов длительное время;
    - кошельки с балансом выше порога, где клиент давно не записывался.
- Для каждого кейса:
  - либо создавать записи в существующем `RecallCampaign`/`RecallAutomation`;
  - либо создавать `Task` (`source="system"` или `source="ai_auto"`, если подключён AI‑анализ).

---

## 6. Backend — API `admin_loyalty` и `patient_loyalty`

### 6.1. `admin_loyalty.py`

- Новый роутер:
  - `GET /api/v1/admin/loyalty/packages` / `POST` / `PATCH` / `DELETE` — CRUD по `SubscriptionPackage`;
  - `GET /api/v1/admin/loyalty/customer-subscriptions` — список с фильтрами по пациенту/статусу;
  - `GET /api/v1/admin/loyalty/subscription-usages` — история использования пакетов (по пациенту/периоду/клинике);
  - `GET /api/v1/admin/loyalty/wallets` — поиск по пациентам и балансу;
  - `GET /api/v1/admin/loyalty/wallets/{id}/transactions` — движения по кошельку.
  - `GET /api/v1/admin/loyalty/policy` / `POST` / `PATCH` — просмотр и изменение `LoyaltyPolicy` для клиники (или прокси к настройкам клиники, если политика хранится там).
- RBAC:
  - просмотр: `view_loyalty` (или `view_crm`/`view_analytics` в зависимости от матрицы);
  - управление пакетами, политиками и кошельками: `manage_loyalty`.

### 6.2. `patient_loyalty.py`

- Новый роутер:
  - `GET /api/v1/patient/loyalty/me`:
    - активные/истёкшие `CustomerSubscription`;
    - текущий баланс кошелька и последние транзакции;
  - `GET /api/v1/patient/loyalty/history` — история использования.

### 6.3. Отчёты и аналитика по лояльности

- Подготовить данные так, чтобы:
  - в ERP‑отчётах по выручке:
    - покупка пакета всегда учитывалась как доход (через `FinancialTransaction`);
    - использование пакета **не** удваивало выручку (либо не создаёт новых приходов, либо учитывается отдельным типом движения);
  - в CRM/Marketing‑отчётах:
    - данные по пакетам/кошельку были доступны для расчёта LTV, повторных визитов и эффективности программ лояльности.

---

## 7. LTV и отчёты владельца

- **TODO:**
  1. Обеспечить, чтобы при расчёте LTV пациента:
     - учитывались как разовые платежи, так и покупки/использование подписок;
     - использование пакета не удваивало выручку (считать по факту оплаты пакета + доплатам, если есть).
  2. В отчётном слое/сервисах подготовить агрегаты по лояльности:
     - сколько выручки и повторных визитов даёт модуль подписок/кошелька;
     - базовые метрики по удержанию (кол‑во активных/истёкших пакетов, доля клиентов с балансом).
  3. Передавать эти метрики в разделы аналитики/CRM:
     - чтобы владелец видел вклад программ лояльности в LTV и возвраты.

---

## 8. Frontend — раздел «Лояльность» и PWA пациента

### 8.1. Админка

- Раздел `Loyalty` (sidebar):
  - вкладка «Пакеты»:
    - таблица `SubscriptionPackage` + форма создания/редактирования (drawer);
  - вкладка «Абонементы»:
    - список `CustomerSubscription` с фильтрами по пациенту/статусу;
  - вкладка «Кошельки»:
    - поиск по пациенту, отображение баланса, переход к транзакциям.
- Типы/хуки:
  - в `frontend/src/api/types.ts` — DTO для сущностей лояльности;
  - в `frontend/src/hooks/` — `useLoyaltyPackages`, `useCustomerSubscriptions`, `useWallets`, `useWalletTransactions`.

### 8.2. PWA пациента

- Экран «Мои абонементы и баллы»:
  - список активных и истёкших пакетов;
  - текущий баланс и история движений;
  - CTA‑кнопки «Записаться»/«Использовать пакет».

### 8.3. Интеграция с OmniChat/CRM

- В правой панели OmniChat (см. ARCH_FRONTEND_BUSINESS_OS_UX):
  - виджет с активными подписками и балансом кошелька пациента;
  - быстрая навигация к разделу «Лояльность».

---

## 9. Тестирование

### 9.1. Backend

- Юнит‑тесты:
  - `loyalty_service` (покупка/активация/использование подписок);
  - `wallet_service` (начисление/списание/сгорание баллов).
- Интеграционные:
  - сценарий покупки пакета и его использования в нескольких визитах;
  - сценарий начисления и списания кэшбэка при `Booking.completed`.

### 9.2. Frontend

- Проверка:
  - отображения пакетов, абонементов и кошельков в админке;
  - корректной загрузки «Мои абонементы и баллы» в PWA.

---

## 10. Порядок выполнения для @DEV

1. Добавить доменные сущности и миграции для подписок и кошелька.
2. Реализовать `loyalty_repository` и `loyalty_service`.
3. Реализовать `wallet_service` и интеграцию с ERP/Booking (`Booking.completed`).
4. Добавить API `admin_loyalty` и `patient_loyalty` с проверками RBAC.
5. Реализовать раздел «Лояльность» в админке и PWA‑экран пациента.
6. Добавить smart‑recall‑триггеры (через Recall/Tasks) на основе данных лояльности.
7. Реализовать расчёт и учёт LTV с учётом подписок и кошелька в отчётах владельца.
8. Написать и прогнать backend и frontend тесты.

