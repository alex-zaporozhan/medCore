## ARCH_AUDIT_FINDINGS — Консолидированные выводы архитектурного аудита V2

> Роли: @ARCH, @LEAD, @BIZ, @DEV, @QA, @SEC.  
> Источники: все `ARCH_*`, `TECH_PASSPORT_*`, `BUSINESS_LOGIC_V2.md`, `FUNCTIONAL_MAP_CURRENT.md`, `DEV_PROMPTS_*`, `DEV_TODOS_*_GAPS.md`.

---

## 1. Кросс‑модульные выводы (Events, Context, AI, RBAC)

- **1.1. Domain Events / EventBus**
  - Фактически: EventBus и handlers есть (`lead_event_handlers`, `erp_event_handlers`, `loyalty_event_handlers`, `tasks_event_handlers`), события `BOOKING_CREATED`, `BOOKING_COMPLETED`, `PAYMENT_SUCCESS`, `CONTACT_CREATED` используются.
  - Проблемы:
    - нет единого контракта и фабрик событий;
    - payload собирается вручную, формат проверяется неявно.
  - Решение:
    - ввести модуль `events_contracts.py` с описанными схемами событий;
    - добавить фабрики `make_*_event(...)`, запретить “сырой” `DomainEvent` в бизнес‑коде;
    - расширить тесты EventBus нагрузочными/diagnostic‑сценариями.

- **1.2. RequestContext и RBAC**
  - Фактически: `RequestContext` реализован, RBAC‑модель и `require_permissions` работают, но используются не во всех новых сервисах.
  - Проблемы:
    - часть сервисов V2 (ERP, Loyalty, Tasks, Attribution) явно не принимает `RequestContext`;
    - фоновые процессы (Celery/AI‑таски) не всегда имеют консистентный `clinic_id`/roles.
  - Решение:
    - стандартизировать: все новые публичные методы сервисов V2 принимают `ctx: RequestContext` или построенный из него `AdminContext`;
    - описать поведение для системных задач (user_type="system") и потенциального multi‑clinic.

- **1.3. AiConfigService и политика ПДн**
  - Фактически: `AiConfigService` и `AiSanitizer` реализованы и частично используются (AI‑агент, security‑тесты).
  - Проблемы:
    - отдельные AI‑точки (например, AI Task Generator) используют `AiClient` напрямую из `settings`;
    - не все LLM‑потоки проходят через `AiSanitizer`.
  - Решение:
    - все AI‑вызовы (агент, аналитика, таски) обязаны получать конфиг через `AiConfigService`;
    - для каждого потока зафиксировать, какие ПДн допустимы, и покрыть mock‑LLM security‑тестами.

---

## 2. Модульные выводы (CRM, ERP, Loyalty, Tasks, Paperless, Attribution)

- **2.1. CRM Kanban**
  - Реализованы: `LeadPipeline/LeadStage/LeadCard/LeadNote`, `LeadService`, `lead_event_handlers`, `admin_crm`, `AdminSalesPipelinePage`.
  - Проблемы:
    - поиск лидов по `primary_booking_id` через общие выборки, возможны неточности;
    - стратегия стадий и расчёта `estimated_value`/`actual_value` не до конца формализована;
    - OmniChat пока не показывает CRM‑контекст.
  - Решение:
    - добавить прямые методы в репозитории (поиск по booking_id и patient_id);
    - зафиксировать “матрицу стадий” и обновление сумм в ARCH/докстроках;
    - внедрить виджет CRM в правую панель OmniChat.

- **2.2. ERP (Finance/Payroll/Inventory)**
  - Реализован transactional ERP‑узел `BookingErpService.process_booking_completed` и API/фронт для finance/payroll/inventory.
  - Проблемы:
    - частичные оплаты (предоплата, подписки, баллы) не до конца отражены в расчётах сумм;
    - связь с Loyalty (избежание “удвоения” выручки) формально описана, но не полностью закреплена кодом и тестами.
  - Решение:
    - определить “источник правды” по сумме (ERP) и явно зафиксировать, как учитывать пакеты/баллы;
    - добавить интеграционные тесты ERP+Loyalty и LTV‑отчётов.

- **2.3. Loyalty & Subscriptions**
  - Сущности/миграции/сервисы и базовые API есть, начисление кэшбэка по `Booking.completed` реализовано.
  - Проблемы:
    - нет интеграции покупки пакета с payment/ERP (идемпотентный `purchase_subscription` не встраивается в PaymentSuccess);
    - нет использования подписки при записи и сценария оплаты баллами;
    - CRM/отчёты не видят вклад лояльности в LTV.
  - Решение:
    - внедрить `purchase_subscription` и `use_subscription_for_booking` в Payment/Booking flow;
    - добавить учёт баллов в ERP и LTV/отчётах.

- **2.4. RBAC & Tasks**
  - Модели RBAC и задач, сервис `TaskService`, `admin_tasks`, AI Task Generator и базовая матрица прав реализованы.
  - Проблемы:
    - DTO задач грубые (dict), фильтры ограничены;
    - не все системные события порождают задачи (ERP‑аномалии, лиды без движения и др.).
  - Решение:
    - ввести типизированные DTO задач/комментариев;
    - расширить обработчики событий и правила видимости задач по ролям.

- **2.5. Paperless Office**
  - Реализованы `DigitalFormTemplate/Submission/ESignature`, `FormsService`, admin/patient forms API и фронт (AdminFormsPage, FormsPage).
  - Проблемы:
    - “pending forms” не учитывает контекст визита/версии/срок действия;
    - нет полноценного потока подписи в PWA и интеграции статуса форм в OmniChat.
  - Решение:
    - доопределить бизнес‑правила pending‑форм для разных типов визитов;
    - добавить подпись на фронте и виджет форм в OmniChat.

- **2.6. Marketing Attribution**
  - Сущности (TrafficSource, Campaign, VisitAttribution, поля в FinancialTransaction) и `MarketingAttributionService` + admin API есть; на фронте реализован UTM‑tracking.
  - Проблемы:
    - не везде гарантировано заполнение `visit_attribution_id` и связи с пациентом/лидом;
    - некоторые метрики (completed bookings) считаются упрощённо.
  - Решение:
    - укрепить flow UTM/session → VisitAttribution → Lead/Patient → FinancialTransaction;
    - доработать отчёты ROI и drill‑down.

---

## 3. UX/Frontend выводы (Business OS)

- **3.1. OmniChat**
  - Базовый чат и AI‑интеграции есть, но command‑center‑паттерн (3 колонки, виджеты CRM/Loyalty/Forms/Tasks) реализован частично.

- **3.2. Единая дизайн‑система**
  - Токены/темы частично есть, но нет строго выдержанного премиум‑стиля на всех ключевых страницах.

- **3.3. Лендинг vs фактический продукт**
  - Содержимое лендинга должно быть синхронизировано с доступными модулями V2 (чтобы не обещать несуществующее).

---

## 4. Рекомендованные архитектурные артефакты

@ARCH рекомендуется опираться на этот документ и существующие `_GAPS` для формирования:

- `ARCH_UPGRADE_ROADMAP.md` — фазный план апгрейда (по модулям и кросс‑слоям).
- Обновлённые/дополнительные `ARCH_*` разделы (если для модулей появятся новые фичи).
- При необходимости — детализированные контракты:
  - `ARCH_EVENTS_CONTRACTS.md` — спецификация событий.
  - `ARCH_AI_PRIVACY_POLICY.md` — политика ПДн и AI.

