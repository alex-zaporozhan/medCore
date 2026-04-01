## DEV_PROMPTS_V2_VERIFICATION — Регрессионная проверка модулей V2

> Роли: @DEV, @QA, @ARCH.  
> Цель: не реализовывать модули с нуля (они уже сделаны по `DEV_PROMPTS_*`), а **проверить и дожать хвосты** по `_GAPS` и убедиться, что система стабильно работает как Business OS V2.
>
> Читать после: `ARCH_AUDIT_FINDINGS.md`, `ARCH_UPGRADE_ROADMAP.md`, всех `DEV_PROMPTS_*` и соответствующих `DEV_TODOS_*_GAPS.md`.

---

## 1. Общий подход для @DEV/@QA

1. Для каждого модуля:
   - считать законченной **базовую реализацию** по `DEV_PROMPTS_*`;
   - рассматривать `DEV_TODOS_*_GAPS.md` только как **список точечных доработок/проверок**;
   - не менять архитектуру, если на это нет прямого указания в `ARCH_*`.
2. Для каждого пункта `_GAPS`:
   - либо реализовать недостающую часть;
   - либо явно зафиксировать, почему она не нужна (комментарий в коде/доках, обсуждение с @ARCH/@LEAD);
   - в конце проставить чек‑боксы в самом `_GAPS` (если договоритесь использовать их как living‑беклог).
3. После завершения модуля прогнать:
   - unit + integration тесты модуля;
   - smoke/e2e (если есть фронт‑часть);
   - короткий ручной чек‑лист из соответствующего DEV_PROMPTS.

---

## 2. Crosscut: EventBus / RequestContext / AiConfig

**Документы:**
- `ARCH_CROSSCUT_EVENT_CONTEXT_AI.md`
- `DEV_PROMPTS_CROSSCUT_EVENT_CONTEXT_AI.md`
- `DEV_TODOS_CROSSCUT_EVENT_CONTEXT_AI_GAPS.md`

**Задачи для @DEV (проверка + доработка):**

1. Пройти по `DEV_TODOS_CROSSCUT_EVENT_CONTEXT_AI_GAPS.md` и:
   - реализовать фабрики событий (`make_*_event(...)`) и заменить ручные `DomainEvent(...)`;
   - убедиться, что `RequestContext` используется в ключевых сервисах V2 (ERP, CRM, Tasks, Loyalty, Attribution, AI‑сервисы);
   - перевести все AI‑точки на `AiConfigService` + `AiSanitizer`.
2. Добавить/проверить интеграционные тесты, моделирующие:
   - `BookingCompleted` → ERP+CRM+Loyalty+Tasks хендлеры видят корректный payload;
   - AI‑агент и AI‑таск‑генератор работают с конфигом и политикой ПД.

---

## 3. Loyalty & Subscriptions

**Документы:**
- `ARCH_LOYALTY_SUBSCRIPTIONS.md`
- `DEV_PROMPTS_LOYALTY_SUBSCRIPTIONS.md`
- `DEV_TODOS_LOYALTY_SUBSCRIPTIONS_GAPS.md`

**Задачи для @DEV (проверка + доработка):**

1. Свериться с `DEV_PROMPTS_LOYALTY_SUBSCRIPTIONS.md`:
   - убедиться, что все разделы 2–8 реально покрыты кодом (сущности, миграции, сервисы, API, фронт, базовые тесты).
2. По `DEV_TODOS_LOYALTY_SUBSCRIPTIONS_GAPS.md`:
   - реализовать/проверить:
     - приоритет выбора подписки, бизнес‑ошибки при недостаточном остатке;
     - защиту от гонок в `WalletService`;
     - интеграцию покупки/использования пакетов и оплаты баллами с ERP/Finance;
     - отчётные метрики по лояльности и связку с LTV;
     - CRUD/CTA/OmniChat‑виджет на фронте;
     - интеграционные тесты ERP+Loyalty, оплата баллами и UI‑тесты.

---

## 4. ERP Finance & Inventory

**Документы:**
- `ARCH_ERP_FINANCE_AND_INVENTORY.md`
- `DEV_PROMPTS_ERP_FINANCE_AND_INVENTORY.md`
- `DEV_TODOS_ERP_FINANCE_AND_INVENTORY_GAPS.md`

**Задачи для @DEV:**

1. Проверить, что ERP‑узел (`BookingErpService`) и API/фронт реализованы строго по DEV_PROMPTS.
2. По `_GAPS`:
   - укрепить расчёты сумм (услуги, скидки, частичные оплаты);
   - связку ERP ↔ Loyalty (без двойной выручки);
   - тесты ERP‑узла (включая сценарии с лояльностью).

---

## 5. CRM Kanban

**Документы:**
- `ARCH_CRM_KANBAN.md`
- `DEV_PROMPTS_CRM_KANBAN.md`
- `DEV_TODOS_CRM_KANBAN_GAPS.md`

**Задачи для @DEV:**

1. Проверить соответствие сущностей/сервисов/роутеров/страниц требованиям DEV_PROMPTS.
2. По `_GAPS`:
   - улучшить поиск и связи лидов с бронированиями/платежами;
   - формализовать стратегию стадий и сумм;
   - встроить CRM‑контекст в OmniChat;
   - дополнить интеграционные и UI‑тесты Kanban.

---

## 6. RBAC & Tasks

**Документы:**
- `ARCH_RBAC_AND_TASKS.md`
- `DEV_PROMPTS_RBAC_AND_TASKS.md`
- `DEV_TODOS_RBAC_AND_TASKS_GAPS.md`

**Задачи для @DEV:**

1. Убедиться, что базовые сущности/миграции/сервисы/роутеры реализованы по DEV_PROMPTS.
2. По `_GAPS`:
   - синхронизировать матрицу прав и seeding‑миграции;
   - довести Task API до типизированных DTO;
   - реализовать контекстную видимость задач (особенно для `doctor`);
   - усилить AI Task Generator (аномалии, конфиги) и системные tasks‑handlers;
   - покрыть RBAC‑403/401 тестами для критичных модулей.

---

## 7. Paperless Office

**Документы:**
- `ARCH_PAPERLESS_OFFICE.md`
- `DEV_PROMPTS_PAPERLESS_OFFICE.md`
- `DEV_TODOS_PAPERLESS_OFFICE_GAPS.md`

**Задачи для @DEV:**

1. Сверить реализованный функционал форм/подписей/страниц с DEV_PROMPTS.
2. По `_GAPS`:
   - реализовать “pending forms before visit” по контексту визита/версии;
   - добавить подпись в PWA (canvas + signature_payload);
   - улучшить админ‑просмотр submissions и OmniChat‑виджет статуса форм;
   - реализовать экспорт форм/подписей и протестировать PII‑политику.

---

## 8. Marketing Attribution

**Документы:**
- `ARCH_MARKETING_ATTRIBUTION.md`
- `DEV_PROMPTS_MARKETING_ATTRIBUTION.md`
- `DEV_TODOS_MARKETING_ATTRIBUTION_GAPS.md`

**Задачи для @DEV:**

1. Проверить корректность реализации VisitAttribution/TrafficSource/Campaign и маркетинговых отчётов.
2. По `_GAPS`:
   - укрепить flow UTM/session → VisitAttribution → Lead/Patient → FinancialTransaction;
   - доработать метрики (completed bookings, ad_spend, ROI/CAC);
   - добавить admin UI и drill‑down;
   - покрыть атрибуцию тестами и RBAC.

---

## 9. Frontend Business OS UX

**Документы:**
- `ARCH_FRONTEND_BUSINESS_OS_UX.md`
- `DEV_PROMPTS_FRONTEND_BUSINESS_OS_UX.md`
- `DEV_TODOS_FRONTEND_BUSINESS_OS_UX_GAPS.md`

**Задачи для @DEV/@FRONTEND:**

1. Проверить, что ключевые страницы соответствуют архитектурным layout‑ам и токенам.
2. По `_GAPS`:
   - завершить трёхколоночный OmniChat Command Center (виджеты CRM/Loyalty/Forms/Tasks);
   - вынести единый 3‑колоночный layout и обновить CRM/Tasks/Finance;
   - синхронизировать лендинг с фактическими возможностями V2.

---

## 10. Как использовать этот файл

- Для запуска работы по модулю:
  - выбери фазу/модуль из `ARCH_UPGRADE_ROADMAP.md`;
  - открой соответствующие `DEV_PROMPTS_*` и `DEV_TODOS_*_GAPS.md`;
  - дай @DEV этот файл как “надмодульный” чек‑лист: «сначала сверяемся с DEV_PROMPTS, затем закрываем `_GAPS` по этому разделу».
- Для @QA:
  - использовать этот документ как карту того, какие проверки и тесты ожидать от модуля после “второго прохода”.

