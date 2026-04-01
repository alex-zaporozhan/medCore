### 5. Статус ERP‑1 после DEV_PROMPT_BKG_CORE_001

- **Что реализовано:**  
  - единая точка входа ERP‑узла завершения визита `ErpVisitNodeService.process_visit_completion`, вызываемая из фасада `BookingCompletionService.complete_visit`;  
  - при ошибках конфигурации ERP (`ERPConfigurationError`) фасад не переводит визит в `completed`, проставляет `booking.erp_error_code` и создаёт системный `Task` для владельца/админа с описанием проблемы;  
  - метрики и логи по цепочке `booking_to_erp` фиксируют попытки завершения визита, типы ошибок и длительность шагов;  
  - ERP‑узел формирует агрегированное резюме по движению ERP‑обязательств Loyalty (через `ErpLoyaltyWriteOffSummary`), которое попадает в `BookingCompletionResult.erp_summary`.  

- **Что остаётся на следующие DEV_PROMPT:**  
  - декомпозиция ERP‑узла на отдельные Finance/Payroll/Inventory‑процессоры и богатые ERP‑отчёты — `DEV_PROMPT_ERP_NODE_010`, `DEV_PROMPT_ERP_REPORTS_012`;  
  - строгая двусторонняя связь ERP ↔ Loyalty‑обязательств (включая сложные сценарии пакетов/депозитов) — `DEV_PROMPT_ERP_LOYALTY_011`;  
  - расширенные Attribution/ROI‑агрегаты поверх ERP‑выручки — частично закрыто связкой `lead_id` на `financial_transactions` и CRM `actual_value` (v1 `DEV_PROMPT_CRM_MONEY_008`); полнота ATT‑2 — в `BACKEND_GAPS_Attribution_NEXT.md` и follow‑up промптах.
## BACKEND_GAPS_ERP_NEXT — домен ERP (Finance, Payroll, Inventory)

### 1. Текущее состояние в коде

- **Сущности:**
  - `Cashbox`, `FinancialTransaction`, `PayrollPolicy`, `SalaryTransaction`,
  - `Product`, `Warehouse`, `InventoryTransaction`, `ServiceConsumable`,
  - связки с `Booking`, `Payment`, `CustomerSubscription`, `Wallet` (по коду и бизнес‑логике).
- **Сервисы:**
  - `FinanceService` — операции над кассами/движениями;
  - сервисы склада/зарплат (по роутерам `admin_inventory.py`, `admin_payroll.py`).
- **API:**
  - `admin_finance.py` — liability, список/создание/обновление/удаление касс, транзакции;
  - `admin_inventory.py`, `admin_payroll.py` — управление складом, начислениями.
- **Frontend:**
  - `AdminFinancePage.tsx` — вкладки «Кассы», «Транзакции», «Зарплаты», «Склад».

### 2. Сравнение с ARCH_ERP_NEXT и BUSINESS_LOGIC_V2

- ARCH/V2 ожидают:
  - единый транзакционный узел при `Booking.status → completed` с созданием всех ERP‑объектов;
  - строгую согласованность между продажей пакетов (Loyalty) и ERP (обязательства/авансы);
  - богатую ERP‑панель для владельца.
- По коду:
  - все сущности/эндпоинты ERP уже есть;
  - AttentionFeedService учитывает ERP‑ошибки по визитам (`erp_error_code`).

### 3. Выявленные GAP’ы

- **ERP-1 — нет явного фасада завершения визита (S1–S2)**  
  - ARCH_ERP_NEXT требует единый `BookingCompletion`‑фасад, а текущая логика ERP распределена.  
  - Риск: разные ветки изменений могут обрабатывать визит неполно или в разное время.

- **ERP-2 — частично формализована интеграция с Loyalty (S2)**  
  - V2 описывает строгую связь покупки пакетов/депозитов с Cashbox/liability и дальнейшим погашением при визитах.  
  - Реализация требует допроверки и более жёсткой формализации в коде/схемах.

- **ERP-3 — отчётность владельца может не полностью отражать ERP‑логику (S2)**  
  - Отчёты по выручке/ЗП/складу есть, но их полнота/детализация относительно новой ERP‑модели vNext требует дополнительного анализа.

### 4. Оценка сложности исправления

- **ERP-1:** высокая — потребуется аккуратная миграция к фасаду, затрагивающая Booking, ERP‑сервисы и AttentionFeed.
- **ERP-2:** средняя — можно реализовывать инкрементально, усиливая связи между существующими сущностями.
- **ERP-3:** средняя — доработка отчётов и агрегаций поверх уже существующей ERP‑модели.

### 5. Синхронизация с QA_ARCH (W1/W2 unified backlog, 2026-03)

- **Наблюдаемость L2 / цепочка Booking→ERP:** пороги алертов и кардинальность метрик зафиксированы в **`docs/artifacts/NONFUNCTIONAL_AUDIT_NEXT.md`** (§6); правила Prometheus — **`deploy/prometheus/dental_booking_alerts.yml`**. Метрики цепочки completion используют **`clinic_bucket`** (32 корзины), nightly failures — **`aggregate_kind`** без `clinic_id` в лейблах.
- **Миграции watermark / event refresh:** **`docs/MIGRATION_UPGRADE.md`** (блок ERP витрины).

