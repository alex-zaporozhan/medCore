## ✅ DEV_TODOS_V2_OVERVIEW — План работ для @DEV (Business OS)

> Этот файл — чек-лист для @DEV по реализации V2 (Business OS).  
> Архитектурные решения уже зафиксированы в `ARCH_*` и `BUSINESS_LOGIC_V2.md`; здесь — только порядок и состав задач.

---

## 1. Базовая инфраструктура (до модулей)

**Документы:** `ARCH_CROSSCUT_EVENT_CONTEXT_AI.md`, `DEV_PROMPTS_CROSSCUT_EVENT_CONTEXT_AI.md`

- [ ] **1.1. RequestContext**
  - Тип `RequestContext` в `src/core/context.py`.
  - Dependency `get_request_context` в `api/v1/dependencies.py`.
- [ ] **1.2. AiConfigService**
  - `src/application/services/ai_config_service.py` с `AiProviderConfig`.
  - Обновление `AiClient` на использование этого сервиса.
- [ ] **1.3. EventBus / доменные события**
  - In‑process EventBus в `src/application/events/`.
  - События: `BookingCreated`, `BookingCompleted`, `PaymentSuccess`, `ContactCreated`.
  - Подключение генерации событий в существующие сервисы (`BookingService`, `PaymentService`, Omnichannel).

---

## 2. Модуль AI Agent (Function Calling)

**Документы:** `ARCH_AI_AGENT.md`, `DEV_PROMPTS_AI_AGENT.md`

- [ ] **2.1. Слой инструментов (`tools_registry`)**
  - `src/application/ai/tools_base.py`, `tools_booking.py`, `tools_registry.py`.
  - Инструменты `get_available_slots` и `create_booking`.
- [ ] **2.2. Расширение AiClient**
  - Метод `chat_with_tools(...)` с поддержкой tool calls.
- [ ] **2.3. Orchestrator loop**
  - Реализация `run_ai_agent` в `OmnichannelAiOrchestrator`.
  - Интеграция с Omnichannel‑чатом.
- [ ] **2.4. Политика ПД**
  - Подключение `AiSanitizer` + `AiConfigService`.
- [ ] **2.5. Тесты**
  - Unit‑тесты инструментов.
  - Интеграционные тесты цикла.
  - Security‑тесты на ПД и clinic_id.

---

## 3. Модуль CRM Kanban (Sales Pipeline)

**Документы:** `ARCH_CRM_KANBAN.md`, `DEV_PROMPTS_CRM_KANBAN.md`

- [ ] **3.1. Модели и миграции**
  - `LeadPipeline`, `LeadStage`, `LeadCard`, `LeadNote`.
- [ ] **3.2. Репозитории и LeadService**
  - CRUD по лидам/стадиям.
  - Методы `create_lead_from_contact`, `attach_booking`, `attach_payment`, `update_stage`.
- [ ] **3.3. Обработка событий**
  - Подписчики на `ContactCreated`, `BookingCreated`, `PaymentSuccess`, `BookingCompleted`.
- [ ] **3.4. API `admin_crm`**
  - Листинг/детали лидов, смена стадии, заметки.
- [ ] **3.5. Frontend: `AdminSalesPipelinePage`**
  - Kanban‑доска + боковая панель деталей.
  - Интеграция с OmniChat (отображение стадии/сумм).
- [ ] **3.6. Тесты**
  - Backend + frontend.

---

## 4. Модуль ERP (финансы, ЗП, склад)

**Документы:** `ARCH_ERP_FINANCE_AND_INVENTORY.md`, `DEV_PROMPTS_ERP_FINANCE_AND_INVENTORY.md`

- [ ] **4.1. Модели и миграции**
  - `Cashbox`, `FinancialTransaction`, `PayrollPolicy`, `SalaryTransaction`, `Product`, `Warehouse`, `InventoryTransaction`, `ServiceConsumable`.
- [ ] **4.2. Сервисы**
  - `finance_service`, `payroll_service`, `inventory_service`, `booking_erp_service`.
- [ ] **4.3. Узел `Booking.completed`**
  - `process_booking_completed` + подписчик на событие `BookingCompleted`.
- [ ] **4.4. API `admin_finance`, `admin_payroll`, `admin_inventory`**
  - Управление кассами, политиками ЗП, складом и движениями.
- [ ] **4.5. Frontend: раздел «Финансы»**
  - вкладки «Кассы», «Транзакции», «Зарплаты», «Склад».
- [ ] **4.6. Тесты**

---

## 5. Модуль RBAC и Tasks

**Документы:** `ARCH_RBAC_AND_TASKS.md`, `DEV_PROMPTS_RBAC_AND_TASKS.md`

- [ ] **5.1. Модели RBAC**
  - `Role`, `Permission`, `RolePermission`, `UserRole`.
- [ ] **5.2. Модель Task**
  - `Task`, `TaskComment`.
- [ ] **5.3. Сервисы**
  - `rbac_service` (проверка прав), `task_service`.
- [ ] **5.4. API `admin_tasks`**
  - CRUD задач, комментарии, фильтры.
- [ ] **5.5. Интеграция с AttentionFeed и событиями**
  - автоматические задачи без AI.
- [ ] **5.6. AI Task Generator (Celery Beat)**
  - сбор аномалий → вызов AI → создание задач `source="ai_auto"`.
- [ ] **5.7. Frontend: `AdminTasksPage` + виджеты задач**

---

## 6. Модуль Loyalty & Subscriptions

**Документы:** `ARCH_LOYALTY_SUBSCRIPTIONS.md`, `DEV_PROMPTS_LOYALTY_SUBSCRIPTIONS.md`

- [ ] **6.1. Модели и миграции**
  - `SubscriptionPackage`, `CustomerSubscription`, `SubscriptionUsage`, `Wallet`, `WalletTransaction`, `LoyaltyPolicy`.
- [ ] **6.2. Сервисы**
  - покупка/активация пакетов;
  - использование при записи/завершении визита;
  - начисление/списание/сгорание бонусов.
- [ ] **6.3. API `admin_loyalty`, `patient_loyalty`**
- [ ] **6.4. Frontend: раздел «Лояльность» и экран PWA «Мои абонементы и баллы»**

---

## 7. Модуль Paperless Office

**Документы:** `ARCH_PAPERLESS_OFFICE.md`, `DEV_PROMPTS_PAPERLESS_OFFICE.md`

- [ ] **7.1. Модели и миграции**
  - `DigitalFormTemplate`, `DigitalFormSubmission`, `ESignature`, `VisitNote`/`PatientProfile`.
- [ ] **7.2. Сервисы и API**
  - `admin_forms`, `patient_forms`, привязка к Booking/Patient.
- [ ] **7.3. Frontend**
  - конструктор/список форм в админке;
  - PWA‑анкеты и согласия;
  - интеграция в OmniChat (виджет статуса форм).

---

## 8. Модуль Marketing Attribution

**Документы:** `ARCH_MARKETING_ATTRIBUTION.md`, `DEV_PROMPTS_MARKETING_ATTRIBUTION.md`

- [ ] **8.1. Модели и миграции**
  - `TrafficSource`, `Campaign`, `VisitAttribution` + поля в `LeadCard` и `FinancialTransaction`.
- [ ] **8.2. Сервисы и события**
  - захват utm на лендинге;
  - связка с лидами, пациентами и транзакциями.
- [ ] **8.3. API и отчёты**
  - `admin_marketing_attribution` + дашборды ROI.
- [ ] **8.4. Frontend**
  - раздел отчётов по каналам/кампаниям.

---

## 9. Frontend Business OS UX

**Документы:** `ARCH_FRONTEND_BUSINESS_OS_UX.md`, `DEV_PROMPTS_FRONTEND_BUSINESS_OS_UX.md`, `TEMPLATE_DESIGN_UX.md`, `Gemini_UX_frontend.md`, `LANDING_WEB_FRONTEND.md`

- [ ] **9.1. Обновление токенов и темы**
  - `index.css` и `theme.ts` по TEMPLATE_DESIGN_UX.
- [ ] **9.2. Общие layout‑ы**
  - трёхколоночный layout для OmniChat/CRM/Finance/Tasks.
- [ ] **9.3. OmniChat редизайн**
  - привести к структуре из `Gemini_UX_frontend.md`.
- [ ] **9.4. Приведение существующих страниц к новой дизайн‑системе**
- [ ] **9.5. Обновление лендинга под Business OS**

---

## 10. Рекомендуемый порядок реализации

1. **Базовая инфраструктура:** RequestContext, AiConfigService, EventBus.
2. **AI Agent:** DEV_PROMPTS_AI_AGENT.
3. **CRM Kanban:** DEV_PROMPTS_CRM_KANBAN.
4. **ERP:** DEV_PROMPTS_ERP_FINANCE_AND_INVENTORY.
5. **RBAC & Tasks:** DEV_PROMPTS_RBAC_AND_TASKS.
6. **Loyalty & Subscriptions.**
7. **Paperless Office.**
8. **Marketing Attribution.**
9. **Frontend Business OS UX** (частично можно делать параллельно с backend‑модулями, но финальная полировка — после).

> Этот файл не заменяет подробные DEV_PROMPTS\_* по каждому модулю, а служит «верхнеуровневым чек‑листом» для планирования спринтов и контроля завершения V2.

