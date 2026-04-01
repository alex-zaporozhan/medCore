## BACKEND_GAPS_Loyalty_NEXT — домен Loyalty & Wallets

### 1. Текущее состояние в коде

- **Сущности:**
  - `SubscriptionPackage`, `CustomerSubscription`, `SubscriptionUsage`,
  - `Wallet`, `WalletTransaction`, `LoyaltyPolicy`, `CustomerSegment` (по коду),
  - **`FamilyLink`**, **`PackageFamilyLink`** (семейный доступ к лояльности),
  - используются в `LoyaltyService` и AttentionFeed.
- **API:**
  - `admin_loyalty.py` — управление пакетами/кошельками/политиками;
  - `patient_loyalty.py` — доступ пациента к лояльности.

### 2. Сравнение с ARCH_LOYALTY_NEXT и BUSINESS_LOGIC_V2

- ARCH/V2 ожидают:
  - поддержку count‑based и balance‑based пакетов;
  - семейный шэринг (FamilyLink);
  - тесную связку с ERP (обязательства/авансы, списания при визитах);
  - AI‑триггеры для recall/retention.
- Фактически:
  - базовый движок пакетов/кошельков реализован;
  - **семейный шэринг v1** — в коде (`FamilyLink` + `PackageFamilyLink`, бенефициары в операциях);
  - полный ERP‑цикл и продуктовая полнота по LOY‑1/LOY‑2 — см. GAP’ы и **`ARCH_DEV_LOY_FAMILY_013_TASKS.md`** («На потом»).

### 3. Выявленные GAP’ы

- **LOY-1 — FamilyLink и семейный шэринг (S2)** — **частично закрыто (v1 backend, 2026‑03).**  
  - В коде: клинико‑уровневая сущность **`FamilyLink`**, сервисы, списания подписки/кошелька с бенефициаром, интеграция с booking и ERP movements, patient/admin API, метрики. Ранее существовавший **`PackageFamilyLink`** (привязка к конкретной подписке) сохранён; полная формализация в документации GAPS/UX, UI, Omni, AI‑триггеры и «идеальный» отчёт по obligation — **в работе / на потом** (см. **`ARCH_DEV_LOY_FAMILY_013_TASKS.md`** — «Выполнено», «На потом»).

- **LOY-2 — ERP‑интеграция для обязательств по пакетам недостаточно формализована (S2)**  
  - требуется гарантировать, что все покупки пакетов отражаются как обязательства в Cashbox/liability и погашаются при визитах.

- **LOY-3 — AI‑триггеры и кампании лояльности (S2)** — **частично закрыто (MVP rules + Tasks, 2026‑03).**  
  - В коде: **`loyalty_campaign_settings`**, **`run_campaigns_for_clinic`** (типы задач `LOYALTY_EXPIRING_PACKAGE`, `LOYALTY_HIGH_BALANCE_LOW_ACTIVITY`, `LOYALTY_REENGAGEMENT`), лимиты/ opt‑out / дедуп с SMS, Celery **`run_loyalty_campaign_engine_all_clinics`**, admin API и UI вкладка «Кампании».  
  - **Остаётся GAP:** подключение к **общему AI‑слою** (`ai_tools`/Orchestrator, персонализация, Omnichannel‑черновики) — см. `ARCH_DEV_LOY_AI_014.md` §8 и «На потом» в `ARCH_DEV_LOY_AI_014_TASKS.md`.  
  - Отдельно: Celery **`check_expiring_packages`** (SMS пациентам) по‑прежнему не объединён с AI‑Orchestrator — сосуществует с движком кампаний (операторские Tasks).

### 4. Оценка сложности исправления

- **LOY-1:** средняя → **снижена для ядра домена** (миграция и сервисы реализованы); остаётся доработка продуктовых сценариев, доков и отчётности.
- **LOY-2:** средняя — требует согласования с ERP‑моделью и внимательного обновления транзакций.
- **LOY-3:** **снижена для rule‑based MVP** (кампании и Tasks реализованы); остаётся средняя сложность для **полного** AI‑слоя и Omni‑интеграции.

