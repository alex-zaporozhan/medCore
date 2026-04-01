## DEV_PROMPTS_ERP_FINANCE_AND_INVENTORY — Финансы, ЗП и склад

> Роли: @DEV, @ARCH, @QA.  
> Читается после: `BUSINESS_LOGIC_V2.md`, `ARCH_ERP_FINANCE_AND_INVENTORY.md`, `ARCH_CROSSCUT_EVENT_CONTEXT_AI.md`, `TECH_PASSPORT_BACKEND.md`, `FUNCTIONAL_MAP_CURRENT.md`.

---

## 1. Цели реализации

- Добавить ERP‑слой:
  - учёт денег по кассам (`Cashbox`, `FinancialTransaction`);
  - учёт зарплат врачей (`PayrollPolicy`, `SalaryTransaction`);
  - учёт склада и техкарт (`Product`, `Warehouse`, `InventoryTransaction`, `ServiceConsumable`).
- Сделать завершение визита (`Booking.status = completed`) **единым транзакционным триггером**:
  - при успехе создаются все нужные ERP‑записи;
  - при ошибке — откат, визит остаётся незавершённым, показывается понятная ошибка.

---

## 2. Backend — модель данных и миграции

### 2.1. Доменные сущности

- Добавить в `src/domain/entities/`:
  - `cashbox.py`
  - `financial_transaction.py`
  - `payroll_policy.py`
  - `salary_transaction.py`
  - `product.py`
  - `warehouse.py`
  - `inventory_transaction.py`
  - `service_consumable.py`

Следовать полям и инвариантам из `ARCH_ERP_FINANCE_AND_INVENTORY.md`:

- у всех сущностей — `clinic_id`.
- ключевые индексы:
  - `clinic_id + happened_at` для транзакций;
  - `clinic_id + doctor_id + period` для ЗП;
  - `clinic_id + product_id + warehouse_id` для склада.

### 2.2. Alembic‑миграции

- Создать новую версию:
  - таблицы для всех сущностей;
  - дефолтные значения:
    - `is_default` для склада/кассы можно оставить `False` и настраивать через UI;
  - внешние ключи:
    - `financial_transactions.cashbox_id → cashboxes.id`;
    - `salary_transactions.doctor_id → doctors.id`;
    - `inventory_transactions.product_id → products.id`, `warehouse_id → warehouses.id`.

---

## 3. Backend — сервисы ERP

### 3.1. Репозитории

- В `src/domain/interfaces/repositories/`:
  - `finance_repository.py` (кассы и финтранзакции);
  - `payroll_repository.py` (политики и ЗП);
  - `inventory_repository.py` (склад и движения).
- Реализации в `src/infrastructure/database/*_repo_impl.py`.

### 3.2. Сервисы

- В `src/application/services/`:
  - `finance_service.py`:
    - CRUD для `Cashbox`;
    - создание `FinancialTransaction` (приватные методы, вызываемые ERP‑узлом).
  - `payroll_service.py`:
    - CRUD для `PayrollPolicy`;
    - расчёт и запись `SalaryTransaction` по визиту.
  - `inventory_service.py`:
    - CRUD `Product`, `Warehouse`, `ServiceConsumable`;
    - приход/расход (`InventoryTransaction`), проверка остатков.
  - `booking_erp_service.py` (или расширение `BookingService`):
    - основной метод: `process_booking_completed(booking_id, ctx: RequestContext, db: AsyncSession)`.

### 3.3. Узел `process_booking_completed`

- Логика:
  1. Загрузить `Booking` + связанные `Clinic`, `Doctor`, `Patient`, услуги.
  2. Определить:
     - используемую `Cashbox` (по настройкам клиники или явно из `Booking`/UI).
     - актуальную `PayrollPolicy` для врача (`doctor_id`/роли).
     - список `ServiceConsumable` для услуг.
  3. В одной транзакции:
     - создать `FinancialTransaction` типа `income` по сумме визита;
     - рассчитать и создать `SalaryTransaction` врачу;
     - создать `InventoryTransaction` расхода материалов;
     - обновить `booking.status = completed` и пометить `erp_processed = True`.
  4. При любой ошибке:
     - откатить транзакцию;
     - НЕ менять статус `Booking`;
     - вернуть управляемую бизнес‑ошибку (например, `ERPConfigurationError` с кодом `missing_cashbox` / `missing_payroll_policy` / `insufficient_stock`), чтобы UI отобразил понятное сообщение.

---

## 4. Интеграция с доменными событиями

- Подписаться на `BookingCompleted` Event (см. ARCH_CROSSCUT_EVENT_CONTEXT_AI.md):
  - хендлер вызывает `process_booking_completed`:
    - если успех — ничего больше не делает;
    - если ошибка —:
      - логирует;
      - пишет в `AttentionFeed` (новое событие для раздела Tasks/Reports).
- Важно:
  - **не** вызывать ERP‑узел напрямую из контроллеров — только через событие/сервис, чтобы сохранить единый вход.

---

## 5. Backend — API для управления ERP

### 5.1. Finance API

- Новый роутер `admin_finance.py`:
  - `GET /api/v1/admin/finance/cashboxes` / `POST` / `PATCH` / `DELETE` — управление кассами.
  - `GET /api/v1/admin/finance/transactions` — список транзакций по фильтрам (период, касса, тип).

### 5.2. Payroll API

- `admin_payroll.py`:
  - `GET/POST/PATCH` для `PayrollPolicy`.
  - `GET /api/v1/admin/payroll/transactions` — список `SalaryTransaction` по врачам/периодам.

### 5.3. Inventory API

- `admin_inventory.py`:
  - CRUD для `Product`, `Warehouse`, `ServiceConsumable`.
  - `GET /api/v1/admin/inventory/transactions` — история движений.
  - `GET /api/v1/admin/inventory/stock` — текущие остатки по продуктам.

RBAC:

- доступ к этим роутам только ролям `Owner`/`Manager` (см. `ARCH_RBAC_AND_TASKS.md`).

---

## 6. Frontend — раздел «Финансы»

### 6.1. Структура раздела

- В админке добавить раздел (sidebar) «Финансы»:
  - вкладка «Кассы»:
    - таблица касс (название, тип, баланс, активность);
    - создание/редактирование кассы (drawer‑форма).
  - вкладка «Транзакции»:
    - таблица `FinancialTransaction` с фильтрами по периоду/кассе/типу;
  - вкладка «Зарплаты»:
    - таблица `SalaryTransaction` по врачам и периодам;
  - вкладка «Склад»:
    - таблица продуктов и остатков;
    - просмотр движений и техкарт услуг.

### 6.2. Типы и хуки

- В `frontend/src/api/types.ts` добавить DTO для:
  - Cashbox, FinancialTransaction, PayrollPolicy, SalaryTransaction, Product, Warehouse, InventoryTransaction, ServiceConsumable.
- В `frontend/src/hooks/`:
  - `useCashboxes`, `useFinanceTransactions`, `usePayrollPolicies`, `useSalaryTransactions`, `useInventoryStock`, `useInventoryTransactions`, `useServiceConsumables`.

---

## 7. Тестирование

### 7.1. Backend

- Юнит‑тесты:
  - для `finance_service`, `payroll_service`, `inventory_service`:
    - корректность расчётов;
    - проверки ограничений (отрицательные суммы, недостаток остатков).
- Интеграционные тесты:
  - сценарий `Booking.completed`:
    - при корректной конфигурации:
      - создаются FinancialTransaction, SalaryTransaction, InventoryTransaction;
      - статус визита изменяется;
    - при отсутствии кассы/политики:
      - статус остаётся прежним;
      - отдаётся бизнес‑ошибка;
      - создаётся запись в AttentionFeed.

### 7.2. Интеграционные тесты с модулем лояльности

- **TODO:**
  - добавить отдельные сценарии для связки ERP + Loyalty:
    - визит, полностью оплаченный пакетом (`CustomerSubscription`):
      - проверка, что выручка не «удваивается» (движение по деньгам учитывает факт покупки пакета, а не создаёт вторичный приход);
    - визит с частичной оплатой баллами кошелька (`Wallet`):
      - корректное отражение скидки в `FinancialTransaction`;
      - корректное начисление/неначисление кэшбэка в зависимости от бизнес‑правил.

### 7.3. Frontend

- Проверить:
  - загрузку и отображение данных в разделах «Кассы», «Транзакции», «Зарплаты», «Склад»;
  - валидацию форм создания/редактирования.

---

## 8. Порядок выполнения для @DEV

1. Добавить доменные сущности и выполнить миграции.
2. Реализовать репозитории и сервисы `finance_service`, `payroll_service`, `inventory_service`, `booking_erp_service`.
3. Подключить ERP‑узел к событию `BookingCompleted`.
4. Добавить админские API (finance/payroll/inventory) с RBAC.
5. Реализовать раздел «Финансы» на frontend (кассы, транзакции, ЗП, склад).
6. Написать unit‑ и интеграционные тесты для ERP‑узла, включая сценарии с лояльностью, и фронта.

