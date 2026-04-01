## 🧱 ARCH_REMASTER_PLAN_V2 — План перехода к Business OS

> Роли: @LEAD, @ARCH, @BIZ, @FRONTEND.  
> Цель: зафиксировать общий план ремастеринга Dental Booking → Business OS и карту всех архитектурных документов V2.

---

## 1. Фаза 0 — Текущее состояние (готово)

- **Документы:**
  - `TECH_PASSPORT_BACKEND.md`
  - `TECH_PASSPORT_FRONTEND.md`
  - `TECH_PASSPORT_PROJECT.md`
  - `BUSINESS_LOGIC_CURRENT.md`
  - `FUNCTIONAL_MAP_CURRENT.md`
  - `STACK_SELECTION.md`
- **Смысл:** зафиксировано, что реально работает в коде (backend, frontend, БД, интеграции, домены).

---

## 2. Фаза 1 — Видение V2 и AI Agent

- **Модуль:** Business Logic V2 + AI Agent (Function Calling).
- **Документы:**
  - `BUSINESS_LOGIC_V2.md` — видение Business OS и модульная карта (AI, CRM, ERP, RBAC/Tasks, Loyalty, Paperless, Attribution).
  - `ARCH_AI_AGENT.md` — архитектура AI‑агента и tools_registry.
- **Цели фазы:**
  - перевести AI из режима текста в режим инструментов;
  - не ломая текущий Omnichannel, добавить новый слой оркестрации и инструментов.

---

## 3. Фаза 2 — CRM Kanban (Sales Pipeline)

- **Модуль:** Sales & Kanban.
- **Документы:**
  - `ARCH_CRM_KANBAN.md` — LeadPipeline/LeadStage/LeadCard + связи с Omnichannel, Booking, Payments.
- **Цели фазы:**
  - каждая переписка/лид проходит через явную воронку;
  - владелец видит «думают / записаны / успешно завершено» и суммы по этапам.

---

## 4. Фаза 3 — ERP: Финансы, зарплаты, склад

- **Модуль:** Finance & Inventory.
- **Документы:**
  - `ARCH_ERP_FINANCE_AND_INVENTORY.md` — Cashbox, FinancialTransaction, PayrollPolicy, SalaryTransaction, Product, Warehouse, InventoryTransaction, ServiceConsumable.
- **Цели фазы:**
  - сделать завершение визита (`Booking.completed`) единым триггером:
    - учёт денег в кассах;
    - начисление ЗП врачу;
    - списание материалов со склада.

---

## 5. Фаза 4 — RBAC и Tasks

- **Модуль:** Роли, права и задачи.
- **Документы:**
  - `ARCH_RBAC_AND_TASKS.md` — Role, Permission, RolePermission, UserRole, Task, TaskComment, AI Task Generator.
- **Цели фазы:**
  - формализовать роли (Owner/Manager/Admin/Doctor) и матрицу прав;
  - добавить управляемые задачи (ручные + системные + AI‑генерируемые).

---

## 6. Фаза 5 — Модули роста (Loyalty, Paperless, Attribution)

- **Модуль 5.1: Loyalty & Subscriptions**
  - Документ: `ARCH_LOYALTY_SUBSCRIPTIONS.md`.
  - Сущности: SubscriptionPackage, CustomerSubscription, SubscriptionUsage, Wallet, WalletTransaction.

- **Модуль 5.2: Paperless Office**
  - Документ: `ARCH_PAPERLESS_OFFICE.md`.
  - Сущности: DigitalFormTemplate, DigitalFormSubmission, ESignature, VisitNote/PatientProfile.

- **Модуль 5.3: Marketing Attribution**
  - Документ: `ARCH_MARKETING_ATTRIBUTION.md`.
  - Сущности: TrafficSource, Campaign, VisitAttribution + связи с LeadCard и FinancialTransaction.

---

## 7. Фаза 6 — Frontend Business OS UX

- **Модуль:** UX/UI админки и лендинга.
- **Документы:**
  - `ARCH_FRONTEND_BUSINESS_OS_UX.md` — структура разделов админки, трёхколоночные layout‑ы, согласование с лендингом.
  - `TEMPLATE_DESIGN_UX.md` — шаблон дизайн‑решений (токены, layout, hero, premium‑UI).
  - `Gemini_UX_frontend.md` — конкретные предложения по OmniChat и дашборду.
  - `LANDING_WEB_FRONTEND.md` + `SITE_CONTENT_TEXT.md` — фактический лендинг и тексты.
- **Цели фазы:**
  - привести UI к единой дизайн‑системе Premium SaaS;
  - сделать OmniChat, CRM, ERP, Tasks и другие ключевые экраны визуально и функционально согласованными.

---

## 8. Поперечная фаза — Events, Context, AI‑config

- **Модуль:** Стыковочные шины для всех изменений V2.
- **Документы:**
  - `ARCH_CROSSCUT_EVENT_CONTEXT_AI.md` — EventBus/хуки, RequestContext и AiConfigService.
- **Цели фазы:**
  - ввести единый слой доменных событий (`on_booking_created`, `on_booking_completed`, `on_payment_success`, `on_contact_created`);
  - формализовать `RequestContext` (clinic_id + роли/permissions) для всех новых сервисов;
  - централизовать конфигурацию AI‑провайдера и политики ПД.

---

## 9. Фаза 7 — DEV Prompts и реализация

- **Модуль:** постановка задач для @DEV по каждому архитектурному блоку.
- **Контроль качества:** @QA использует `QA_CHECKLIST_V2_PREPROD_ARCH_DEV.md` (логика ARCH/DEV) и `QA_CHECKLIST_V2_MODULES.md` (Swiss‑level реализации модулей).
- **Планируемые документы (после согласования ARCH):**
  - `DEV_PROMPTS_AI_AGENT.md`
  - `DEV_PROMPTS_CRM_KANBAN.md`
  - `DEV_PROMPTS_ERP_FINANCE_AND_INVENTORY.md`
  - `DEV_PROMPTS_RBAC_AND_TASKS.md`
  - `DEV_PROMPTS_LOYALTY_SUBSCRIPTIONS.md`
  - `DEV_PROMPTS_PAPERLESS_OFFICE.md`
  - `DEV_PROMPTS_MARKETING_ATTRIBUTION.md`
  - `DEV_PROMPTS_FRONTEND_BUSINESS_OS_UX.md`

Каждый DEV‑промпт будет ссылаться на соответствующий `ARCH_*` и TECH_PASSPORT, чтобы обеспечить трассировку требований.

---

## 9. Нужны ли изменения в базовой архитектуре?

**Вывод:** текущая слоистая архитектура (FastAPI + Application Services + Domain + Infrastructure), описанная в TECH_PASSPORT\_\*, **подходит** для внедрения всех модулей V2.  
Большие переломы не требуются, но есть несколько точек, которые разумно укрепить до старта реализации:

1. **Единый слой доменных событий / хуков:**
   - Сейчас многие сценарии завязаны на прямые вызовы сервисов.
   - Для CRM/ERP/Tasks/Attribution удобно ввести:
     - либо лёгкий Event‑шлюз (например, `DomainEvents`/`EventBus` внутри backend);
     - либо чёткие application‑хуки (`on_booking_created`, `on_booking_completed`, `on_payment_success`, `on_contact_created`), через которые будут подписываться CRM, ERP, Loyalty и Tasks.

2. **Стандартизация контекста клиники и пользователя:**
   - Все новые сервисы/модули должны явно принимать `clinic_id` и контекст пользователя (роль/permissions), а не полагаться только на `AdminUser` внутри зависимости.
   - В `core` разумно зафиксировать общий `RequestContext`/`ClinicContext` (это уже частично есть через dependencies, но стоит оформить как явный тип).

3. **Консолидация AI‑конфигурации:**
   - `ClinicAiSettings` и `Settings` уже задают параметры AI, но:
     - стоит централизовать выбор провайдера и политику ПД (какой провайдер, какие типы запросов можно слать с ПД, какие — только обезличенные) в одном месте (например, `AiConfigService`).
   - Это облегчит подключение как внешних, так и «разрешённых» (Яндекс и т.п.) моделей без разбрасывания логики по сервисам.

4. **Чёткая multi‑tenancy для новых доменов:**
   - В TECH_PASSPORT\_\* multi‑tenancy уже выдержана (везде `clinic_id`);
   - важно сохранить это при добавлении CRM/ERP/RBAC/Loyalty/Paperless/Attribution:
     - вся новая схема БД должна явно содержать `clinic_id`;
     - все API‑роуты для админки — фильтровать по клинике из токена.

5. **Слой типизированных DTO для новых модулей:**
   - В `application/dto` уже есть богатый набор моделей;
   - для V2 стоит продолжить этот подход, а не «нести сырые dict»:
     - отдельные DTO для AI‑инструментов, CRM‑листинга, ERP‑отчётов и т.д.

Все эти пункты не меняют фундаментальную архитектуру, а лишь добавляют «стыковочные шины» (events/context/AI‑config), чтобы пакеты изменений V2 состыковались друг с другом без скрытых связей и продублированной логики.

