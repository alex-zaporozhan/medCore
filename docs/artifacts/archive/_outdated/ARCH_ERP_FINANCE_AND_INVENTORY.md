## 💰 ARCH_ERP_FINANCE_AND_INVENTORY — Финансы, зарплаты, склад

> Роли: @ARCH, @BIZ, @LEAD.  
> Цель: спроектировать ERP‑слой (финансы, зарплаты, склад) поверх существующих доменов Booking/Payments так,  
> чтобы один визит (`Booking.completed`) автоматически отражал **деньги, зарплаты и списание материалов**.  
> На этом этапе — **только архитектура**, без изменения кода.

---

## 1. Задача и связь с текущей системой

- Сейчас:
  - есть `Booking`, `Payment`, базовые отчёты и маркетинг;
  - владельцы клиник/салонов всё ещё считают ЗП и списание материалов вручную (Excel).
- Цель ERP‑модуля:
  - сделать `Booking.status = completed` **единым триггером**:
    1. учёт выручки в кассах (`Cashbox`, `FinancialTransaction`);
    2. начисление зарплаты врачу (`PayrollPolicy`, `SalaryTransaction`);
    3. списание материалов (`Product`, `InventoryTransaction`, `ServiceConsumable`).
- Ограничение:
  - Phase 1: один склад на клинику; без сложной мультивалютности; только базовый НДС/налоги (как часть бизнес‑логики, а не налогового учёта).

---

## 2. Новые доменные сущности

### 2.1. Финансы: кассы и транзакции

**Cashbox**

- Назначение: логическая касса, где учитываются деньги:
  - `cash` — наличные;
  - `card` — эквайринг/терминал;
  - `bank_account` — расчётный счёт;
  - при необходимости — отдельные кассы по филиалам/креслам.
- Поля (проектно):
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `name: str`;
  - `type: str` (`cash`, `card`, `bank_account`, `other`);
  - `currency: str` (по умолчанию `RUB`);
  - `is_default: bool`;
  - `is_active: bool`.

**FinancialTransaction**

- Назначение: единичное движение денег.
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `cashbox_id: UUID`;
  - `type: str` (`income`, `expense`, `transfer`);
  - `amount: Decimal`;
  - `currency: str`;
  - `happened_at: datetime`;
  - `description: str | None`;
  - ссылки:
    - `booking_id: UUID | None`;
    - `payment_id: UUID | None`; // связь с YooKassa/другими платежами;
    - `source: str` (`manual`, `booking_completed`, `refund`, и т.п.).

### 2.2. Зарплаты: политики и начисления

**PayrollPolicy**

- Назначение: как считать ЗП врачу/сотруднику.
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `doctor_id: UUID | None` (если политика персональная);
  - `role: str | None` (если политика по роли/типу врача);
  - `fixed_per_shift: Decimal` (фикс за смену; может быть 0);
  - `percent_from_services: Decimal` (например, 0.3 для 30%);
  - `percent_from_products: Decimal` (доля от продажи товаров, если применимо);
  - дополнительные поля для сложных схем в будущем (например, пороговые значения, KPI).

**SalaryTransaction**

- Назначение: запись начисления/корректировки ЗП.
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `doctor_id: UUID`;
  - `booking_id: UUID | None`;
  - `amount: Decimal`;
  - `type: str` (`accrual`, `adjustment`, `payout`);
  - `period_start: date | None`;
  - `period_end: date | None`;
  - `created_at: datetime`;
  - `description: str | None`.

### 2.3. Склад: товары, склад и списания

**Product**

- Назначение: товар/материал.
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `sku: str` (опциональный код);
  - `name: str`;
  - `unit: str` (`pcs`, `ml`, `g`, и т.п.);
  - `is_active: bool`.

**Warehouse**

- Назначение: склад (Phase 1: один `default` на клинику).
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `name: str`;
  - `is_default: bool`.

**InventoryTransaction**

- Назначение: движение запасов (приход/расход).
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `warehouse_id: UUID`;
  - `product_id: UUID`;
  - `type: str` (`incoming`, `outgoing`, `adjustment`);
  - `quantity: Decimal`;
  - `happened_at: datetime`;
  - `description: str | None`;
  - `booking_id: UUID | None` (для расхода по визиту).

**ServiceConsumable**

- Назначение: техкарта услуги — какие материалы и в каком количестве списывать при одном выполнении услуги.
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `service_id: UUID`;
  - `product_id: UUID`;
  - `quantity_per_service: Decimal`; // «1 перчатка», «10 мл пасты».

---

## 3. Транзакционный узел: завершение визита

### 3.1. Событие и общий поток

**Событие:** `Booking.status` меняется на `completed` через `BookingService`/админский API.

- Требование:
  - Все ERP‑операции выполняются **внутри одной транзакции SQLAlchemy**:
    - любые ошибки → `rollback`, `Booking` остаётся в прежнем статусе (или пометка об ошибке).

**Поток (упрощённо):**

1. Загрузка контекста:
   - `booking` (+ связанные `clinic`, `doctor`, `services`, `payments`).
   - `clinic_default_cashbox` (или выбранный в UI).
   - `payroll_policy` по `doctor`/`role`.
2. Расчёт сумм:
   - выручка по услугам в визите (на старте — по ценам услуг, затем можно подтягивать данные Payments/ERP);
   - доля, подлежащая начислению врачу по политике;
   - объём материалов для списания по `ServiceConsumable`.
3. Создание ERP‑записей:
   - `FinancialTransaction` (приход в кассу/кассы);
   - `SalaryTransaction` (начисление врачу);
   - `InventoryTransaction` (расход материалов со склада).
4. Обновление статуса:
   - `booking.status = completed`;
   - возможное обновление связанных сущностей (например, LTV пациента).
5. Коммит транзакции.

Если на любом шаге возникает ошибка (нет кассы, нет политики, нет достаточного остатка материала) —:

- не менять статус `Booking`;
- писать событие в `AttentionFeed` + лог;
- отдавать в UI понятное бизнес‑сообщение («не настроены кассы», «не задана зарплатная политика», «недостаточно остатков на складе»).

### 3.2. Варианты источников суммы (актуальное поведение)

Phase 1 (минимально жизнеспособный вариант, с учётом лояльности и кошелька):

- если у визита есть успешный внешний платёж (`Payment.status = "succeeded"`):
  - ERP считает выручку по фактической сумме платежа `Payment.amount`;
- если внешнего платежа нет:
  - базовая сумма = цена услуги (`Service.price`);
  - если по визиту списаны баллы кошелька (`WalletTransaction.type = "spend", booking_id=<id>`):
    - ERP вычитает сумму списанных баллов из цены услуги: `max(price - wallet_spent, 0)`;
    - визит, полностью оплаченный баллами, даёт `FinancialTransaction.amount = 0`;
  - покупка пакета (`CustomerSubscription`) учитывается как выручка в момент покупки (движение денег при оплате пакета),  
    использование пакета **не создаёт вторичного доходного движения**.

Phase 2+:

- связать ERP‑движение с реальными `Payment`/`FinancialTransaction` уровня платёжных шлюзов (частичные оплаты, возвраты);
- при `Booking.completed` ERP будет только дополнять/сводить движения, не дублируя их.

### 3.3. Коды ошибок ERP‑узла и AttentionFeed

При невозможности обработать визит ERP‑узел поднимает `ERPConfigurationError` с кодом:

- `missing_cashbox` — не настроена дефолтная касса для клиники;
- `missing_payroll_policy` — не найдена подходящая `PayrollPolicy` для врача/роли;
- `missing_warehouse` — не найден дефолтный склад;
- `insufficient_stock` — недостаточно остатков по одному из `ServiceConsumable`.

Код ошибки сохраняется в `Booking.erp_error_code` и используется:

- в AttentionFeed (раздел «Проблемы ERP по визитам») для формирования задач владельцу;
- в UI для отображения понятных сообщений и ссылок на настройки (кассы, ЗП, склад).

---

## 4. Связь с существующими доменами

### 4.1. Booking и Service

- `Booking` уже содержит:
  - ссылку на `clinic`, `doctor`, `patient`, `service_id`/`service_ids`;
  - статус (`pending`, `confirmed`, `completed`, `cancelled`, `no_show`).
- Для ERP достаточно:
  - использовать текущие связи и расширить `Booking`:
    - флагами (`erp_processed: bool`, `erp_error_code: str | None`), чтобы не делать повторную обработку;
    - опциональной ссылкой на основную `FinancialTransaction`.

### 4.2. Payments

- `Payment` (YooKassa):
  - уже знает сумму, статус и `booking_id`.
- На Phase 1:
  - используется как справочная сущность:
    - для связывания оплат и визитов;
    - для CRM и Attribution.
- На Phase 2:
  - возможно сделать маппинг:
    - каждый успешный `Payment` создаёт один или несколько `FinancialTransaction` (приход);
    - при `Booking.completed` ERP только дополняет/сводит движение.

---

## 5. API и UI‑слой ERP (в общих чертах)

### 5.1. Backend API

Новые роутеры (проектно):

- `admin_finance.py`:
  - CRUD `Cashbox`;
  - просмотр `FinancialTransaction` по периодам/кассам;
  - отчёты по выручке.
- `admin_payroll.py`:
  - CRUD `PayrollPolicy`;
  - просмотр `SalaryTransaction` по врачам/периодам;
  - отчёт по ЗП (в том числе кнопка «Сформировать отчёт за период»).
- `admin_inventory.py`:
  - CRUD `Product`, `Warehouse`, `ServiceConsumable`;
  - операции прихода/списания (`InventoryTransaction`);
  - отчёт по остаткам.

### 5.2. Frontend (админка)

- Новый раздел «Финансы»:
  - вкладка «Кассы и выручка» (таблицы по Cashbox/FinancialTransaction);
  - вкладка «Зарплаты» (список врачей с начислениями, статусы выплат);
  - вкладка «Склад» (остатки, движения, техкарты).

UX‑принципы:

- Плотные таблицы с возможностью фильтров по периоду/врачу/типу операции;
- Интеграция с CRM‑канбаном и AI‑модулями:
  - отчёты и ленты внимания учитывают ERP‑данные (например, «Врач X имеет неоплаченную ЗП за период», «На складе заканчиваются перчатки»).

---

## 6. Инварианты и ограничения

1. **Атомарность:** все движения ERP по визиту — в одной транзакции; при ошибке визит остаётся незавершённым.
2. **Multi‑tenancy:** все новые сущности (Cashbox, FinancialTransaction, PayrollPolicy, SalaryTransaction, Product, Warehouse, InventoryTransaction, ServiceConsumable) имеют `clinic_id`.
3. **Независимость от платёжного провайдера:**
   - ERP работает с абстрактными `FinancialTransaction`, а не с YooKassa напрямую;
   - Payments используются как источники правды о фактических переводах, но не как единственный объект бухгалтерского учёта.
4. **Прозрачность для отчётов:**
   - все операции должны быть легко агрегируемыми по:
     - клинике, врачу, периоду, кассе, типу.

---

## 7. Следующие шаги для @ARCH/@BIZ

1. Уточнить:
   - минимальный набор полей для PayrollPolicy на старте (фикс + %);
   - формат сводного отчёта по ЗП и по складу.
2. Расписать сценарии edge‑кейсов:
   - предоплата меньше полной стоимости;
   - частичные возвраты;
   - несколько услуг/врачей в одном визите.
3. Согласовать с юристом/бухгалтером клиента:
   - какие отчёты нужны для реальной отчётности, а какие — только для управленческого учёта.
4. После согласования — подготовить `DEV_PROMPTS_ERP_FINANCE_AND_INVENTORY.md` с конкретными шагами реализации.

