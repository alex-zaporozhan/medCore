## 💜 ARCH_LOYALTY_SUBSCRIPTIONS — Лояльность, абонементы и кошелёк

> Роли: @ARCH, @BIZ, @LEAD.  
> Цель: спроектировать модуль лояльности (абонементы/пакеты, виртуальный кошелёк, умный recall) поверх текущих доменов Booking/Payments/CRM.  
> На этом этапе — только архитектура, без правок кода.

---

## 1. Цели модуля

- **Рост LTV**: клиенты покупают не разовые визиты, а пакеты и возвращаются, чтобы использовать баланс.
- **Привязка к системе**: кэшбэк‑кошелёк и абонементы повышают вероятность повторной записи.
- **Автоматический recall**: система (и AI) видят, кто «сгорел» или давно не был, и инициируют контакт.

Модуль должен работать **поверх** уже существующих:

- домена пациентов (`Patient`);
- записей (`Booking`);
- платежей (`Payment`);
- CRM‑воронки (`LeadCard`).

---

## 2. Сущности абонементов и пакетов

### 2.1. SubscriptionPackage

- Назначение: коммерческий продукт — что именно покупает клиент.
- Поля (проектно):
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `code: str` (внутренний код);
  - `name: str` («Курс из 10 процедур чистки»);
  - `description: str | None`;
  - тип:
    - `kind: str` (`visits`, `balance`, `mixed`):
      - `visits` — фиксированное количество визитов/услуг;
      - `balance` — денежный баланс, который списывается за услуги;
      - `mixed` — комбинация.
  - `services_included: list[UUID]` (какие услуги покрывает пакет);
  - `total_visits: int | None`; // для `visits`;
  - `total_amount: Decimal | None`; // для `balance`;
  - `price: Decimal`; // сколько платит клиент при покупке;
  - `validity_days: int | None`; // срок действия (с момента активации);
  - `is_active: bool`.

### 2.2. CustomerSubscription

- Назначение: конкретный купленный пакет клиента.
- Связи и поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `patient_id: UUID`;
  - `subscription_package_id: UUID`;
  - `status: str` (`active`, `expired`, `used_up`, `cancelled`);
  - `purchased_at: datetime`;
  - `activated_at: datetime | None`;
  - `expires_at: datetime | None`;
  - остатки:
    - `remaining_visits: int | None`;
    - `remaining_amount: Decimal | None`;
  - связь с оплатой:
    - `payment_id: UUID | None` (если покупка была онлайн);
  - мета:
    - `notes: str | None`.

### 2.3. SubscriptionUsage

- Назначение: учёт использования пакета по визитам.
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `customer_subscription_id: UUID`;
  - `booking_id: UUID`;
  - `used_visits: int | None`;
  - `used_amount: Decimal | None`;
  - `used_at: datetime`.

---

## 3. Виртуальный кошелёк (кэшбэк)

### 3.1. Wallet

- Назначение: виртуальный баланс бонусов/кэшбэка.
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `patient_id: UUID`;
  - `balance: Decimal`;
  - `currency: str` (обычно `RUB` или «баллы»);
  - `updated_at: datetime`.

### 3.2. WalletTransaction

- Назначение: движение бонусов.
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `wallet_id: UUID`;
  - `type: str` (`earn`, `spend`, `expire`, `adjustment`);
  - `amount: Decimal`; // положительное число, знак определяется типом;
  - `happened_at: datetime`;
  - связи:
    - `booking_id: UUID | None`;
    - `subscription_id: UUID | None`;
  - `description: str | None`.

### 3.3. Политики лояльности

**LoyaltyPolicy** (может войти в настройки клиники, отдельная сущность не обязательна на старте):

- параметры:
  - `cashback_percent: Decimal` (например, 0.05 = 5% от чека);
  - `min_check_for_cashback: Decimal`;
  - `allow_pay_with_points: bool`;
  - `max_points_share: Decimal` (максимальная доля чека, покрываемая баллами);
  - `points_expire_days: int | None`.

---

## 4. Потоки работы с пакетами и кошельком

### 4.1. Покупка пакета

1. Пациент (через админа или PWA) выбирает `SubscriptionPackage`.
2. Оплата:
   - онлайн через YooKassa (создаётся `Payment` и, после успешного webhook, — `CustomerSubscription`);
   - офлайн (наличными/переводом) — создаётся `CustomerSubscription` + финансовое движение в ERP (через `FinancialTransaction`).
3. Активация:
   - `CustomerSubscription.status = active`;
   - `remaining_visits`/`remaining_amount` устанавливаются по пакету;
   - `expires_at` = `activated_at + validity_days`.

### 4.2. Использование пакета при записи

- При создании/подтверждении `Booking`:
  - если у пациента есть **активные** `CustomerSubscription` для данной услуги/клиники:
    - backend предлагает (через API/фронт):
      - списать визит/баланс с пакета вместо разовой оплаты;
    - при выборе пакета:
      - создаётся `SubscriptionUsage` с `booking_id`;
      - уменьшаются `remaining_visits`/`remaining_amount`;
      - `Booking` помечается как «оплачено пакетом» (флаг или ссылка);
      - в ERP:
        - можно либо не создавать новый приход (если пакет оплачен ранее),
        - либо учитывать движение по отдельным ERP‑правилам (опционально на будущую фазу).

### 4.3. Начисление и списание кэшбэка

- Начисление:
  - при успешном завершении визита (`Booking.completed`) и наличии платежа:
    - сумма кэшбэка = `amount_paid * cashback_percent`;
    - создаётся/обновляется `Wallet`;
    - создаётся `WalletTransaction(type="earn")`;
  - при оплате пакета:
    - аналогичная логика (по решению бизнеса).
- Списание:
  - при оплате услуг/пакетов баллами:
    - клиент выбирает, сколько списать баллов (в пределах `max_points_share`);
    - создаётся `WalletTransaction(type="spend")`;
    - ERP/Payment‑логика учитывает скидку.
- Сгорание:
  - периодический процесс (Celery):
    - ищет устаревшие бонусы (по `points_expire_days`);
    - создаёт `WalletTransaction(type="expire")`.

---

## 5. Умный Recall поверх лояльности

Интеграция с уже существующими доменами `RecallCampaign`, `RecallAutomation`, `RecallLog`:

- Новые триггеры:
  - `customer_subscription` близок к `expires_at`;
  - `remaining_visits` > 0, но клиент давно не записывался;
  - баланс кошелька > порога (`min_points_for_recall`) и клиент долго не был.
- Сценарии:
  - система создаёт автоматизированные recall‑кампании:
    - сообщение: «У вас осталось 2 визита по абонементу, давайте подберём удобное время»;
    - или «У вас на балансе 500 бонусов, их можно потратить на услугу X».
- AI‑поддержка:
  - AI формирует тексты и сегменты для кампаний;
  - может предлагать персонализированные офферы на основе истории визитов и LTV.

---

## 6. API и UI (в общих чертах)

### 6.1. Backend API

Роутеры (проектно):

- `admin_loyalty.py`:
  - CRUD `SubscriptionPackage`;
  - просмотр `CustomerSubscription`, `SubscriptionUsage`;
  - настройка `LoyaltyPolicy`.
- `patient_loyalty.py`:
  - список активных пакетов и баланса кошелька для пациента;
  - история использования (PWA).

### 6.2. Frontend

- Админка:
  - раздел «Лояльность»:
    - вкладка «Пакеты» — настройки `SubscriptionPackage`;
    - вкладка «Абонементы клиентов» — список `CustomerSubscription` с фильтрами;
    - вкладка «Кошельки» — поиск по пациентам и балансу.
- PWA пациента:
  - экран «Мои абонементы и баллы»:
    - список активных/истёкших пакетов;
    - текущий баланс и история бонусов.

---

## 7. Инварианты и ограничения

1. **Однозначность финансового учёта**:
   - покупка пакета всегда ведёт к финансовой операции (ERP);
   - использование пакета не должно «удваивать» выручку.
2. **Простота Phase 1**:
   - только один активный `Wallet` на пациента в клинике;
   - ограниченный набор типов пакетов.
3. **Согласованность с CRM и ERP**:
   - данные по использованию пакетов и бонусов доступны в отчётах и CRM;
   - при расчёте LTV учитываются как разовые, так и пакетные платежи.

После согласования этого документа @LEAD может подготовить `DEV_PROMPTS_LOYALTY_SUBSCRIPTIONS.md` для реализации.

