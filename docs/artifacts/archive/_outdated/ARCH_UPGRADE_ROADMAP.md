## ARCH_UPGRADE_ROADMAP — Дорожная карта апгрейда Business OS (V2)

> Роли: @LEAD, @ARCH, @DEV, @QA, @SEC, @FRONTEND.  
> Этот документ переводит выводы аудита (`ARCH_AUDIT_FINDINGS.md`, `DEV_TODOS_*_GAPS.md`) в поэтапный план запуска V2.

---

## 1. Принципы планирования

- **Никаких “чёрных ящиков”**: каждый модуль V2 (AI, CRM, ERP, RBAC/Tasks, Loyalty, Paperless, Attribution, UX) имеет:
  - ARCH‑док (что и почему);
  - DEV_PROMPTS (как сделать);
  - GAPS (что доделать/улучшить).
- **Фазы независимы, но согласованы через кросс‑слой**:
  - Events, RequestContext, AiConfig, RBAC — must‑have до глубокой интеграции модулей.
- **Definition of Done**: фазу считаем завершённой только при:
  - реализованном коде;
  - покрытии тестами;
  - обновлённых UX‑частях (где релевантно);
  - учёте безопасности (RBAC/PII).

---

## 2. Phase A — Crosscut (Events, Context, AI‑config, RBAC backbone)

**Цель:** укрепить “стыковочные шины”, не меняя бизнес‑логики.

- **A.1. Events / EventBus**
  - Реализовать фабрики и контракты событий (`BookingCreated`, `BookingCompleted`, `PaymentSuccess`, `ContactCreated`).
  - Обновить публикации в сервисах на использование фабрик.
  - Покрыть EventBus diagnostic‑тестами.

- **A.2. RequestContext в модулях V2**
  - Обновить сигнатуры ключевых сервисов (ERP, CRM, Loyalty, Tasks, Attribution, AI‑модули) на приём `RequestContext`/`AdminContext`.
  - Описать и протестировать поведение для Celery/системных задач.

- **A.3. AiConfigService + AiSanitizer**
  - Перевести все AI‑потоки на `AiConfigService`.
  - Включить `AiSanitizer` для всех LLM‑запросов с ПДн.
  - Добавить security‑тесты payload для mock‑LLM.

**DoD Phase A:**

- Все события V2 создаются только через фабрики;
- RequestContext используется во всех новых публичных сервисах;
- Ни один AI‑запрос не уходит в LLM, минуя AiConfig+AiSanitizer;
- Тесты EventBus/RequestContext/AiConfig/AI‑security зелёные.

---

## 3. Phase B — ERP + Loyalty (деньги и лояльность без ошибок)

**Цель:** гарантировать корректный учёт выручки и связку с лояльностью.

- **B.1. ERP расчёт сумм и статусов**
  - Уточнить правила расчёта сумм (услуги/скидки/частичные оплаты).
  - Доработать ERP‑узел с учётом этих правил.

- **B.2. Интеграция Loyalty ↔ Payments/ERP**
  - Покупка пакета:
    - включить `purchase_subscription` в PaymentSuccess flow;
    - связать с `FinancialTransaction`.
  - Использование пакета:
    - интегрировать `use_subscription_for_booking` в поток Booking/ERP;
    - помечать визиты “оплачено подпиской”.
  - Оплата баллами:
    - реализовать spend‑flow и корректный пересчёт суммы для ERP.

- **B.3. Интеграционные тесты ERP+Loyalty**
  - E2E‑кейсы:
    - полная оплата пакетом;
    - частичная оплата баллами;
    - начисление кэшбэка по политике.

**DoD Phase B:**

- Ни один сценарий пакета/баллов не приводит к “удвоению” выручки;
- ERP‑отчёты и LTV‑расчёты согласованы;
- Тесты ERP+Loyalty покрывают ключевые сценарии.

---

## 4. Phase C — CRM Kanban + Tasks + Smart‑recall

**Цель:** прозрачная воронка продаж и управляемые задачи.

- **C.1. CRM**
  - Формализовать матрицу стадий и обновление `estimated_value`/`actual_value`;
  - улучшить привязку лидов к бронированиям/платежам;
  - внедрить CRM‑виджет в OmniChat.

- **C.2. Tasks (RBAC & System/AI Tasks)**
  - Ввести DTO задач/комментариев, расширенные фильтры и видимость по ролям;
  - подкрутить TaskService+admin API;
  - дописать системные tasks‑handlers (ERP‑ошибки, лиды без движения, cancel‑слоты).

- **C.3. Smart‑recall по CRM+Loyalty**
  - По данным CRM/Loyalty/ERP запускать:
    - Recall‑кампании;
    - автоматические задачи для удержания.

**DoD Phase C:**

- Kanban CRM работает end‑to‑end (от контакта до денег) и виден в OmniChat;
- Задачи создаются руками, по событиям и AI‑джобой, видимость по ролям работает;
- Smart‑recall сценарии протестированы (unit+integration).

---

## 5. Phase D — Paperless Office & Compliance

**Цель:** убрать бумагу и обеспечить юр/PII‑контроль.

- **D.1. Pending forms / checklists перед визитом**
  - Ввести правила “какие формы нужны перед визитом”;
  - обновить `/patient/forms/pending` + UX форм.

- **D.2. Подписи и экспорт**
  - Добавить подпись в PWA (canvas, meta);
  - реализовать экспорт form+signature (PDF/ZIP) и логировать доступы.

- **D.3. Интеграция с OmniChat и Tasks**
  - Виджет статуса форм/согласий в правой панели чата;
  - авто‑задачи при отсутствии критичных форм.

**DoD Phase D:**

- Для ключевых визитов есть цифровые формы и подписи;
- Админ видит статус форм в OmniChat/карточке пациента;
- PII‑политика Paperless отражена в security‑тестах и документации.

---

## 6. Phase E — Marketing Attribution & Revenue Intelligence

**Цель:** честный ROI по каналам и сегментам.

- **E.1. UTM/session → VisitAttribution → Patient/Lead**
  - Укрепить flow захвата и связывания;
  - задокументировать first‑touch/мульти‑touch политику (на старте достаточно first‑touch).

- **E.2. Attribution → FinancialTransaction**
  - Гарантировать заполнение `visit_attribution_id` для выручки;
  - доработать отчёты в `MarketingAttributionService`.

- **E.3. Frontend ROI & drill‑down**
  - Страница attribution в админке (каналы, кампании, ROI, CAC);
  - переход к лидам/пациентам/визитам по каналу.

**DoD Phase E:**

- Отчёт ROI по каналам совпадает с ERP/CRM по суммам;
- drill‑down работает и ограничен RBAC;
- UTM‑flow стабилен и покрыт тестами.

---

## 7. Phase F — Frontend Business OS UX (премиальный интерфейс)

**Цель:** привести UI к уровню Premium SaaS с единым опытом.

- **F.1. OmniChat Command Center**
  - Реализовать 3‑колоночный layout;
  - добавить виджеты CRM, Loyalty, Forms, Tasks, LTV.

- **F.2. Единые layout‑паттерны**
  - Вынести трёхколоночный layout и использовать для:
    - CRM Kanban,
    - Tasks,
    - Finance,
    - OmniChat.

- **F.3. Лендинг в стиле Business OS**
  - Обновить Hero/блоки под реальные возможности;
  - синхронизировать тексты с BUSINESS_LOGIC_V2 и roadmap.

**DoD Phase F:**

- OmniChat, CRM, Tasks, Finance визуально и UX‑структурно согласованы;
- лендинг честно отражает продукт и roadmap;
- e2e‑тесты основных маршрутов проходят.

---

## 8. Связь с DEV_PROMPTS и GAPS

Для каждой фазы @ARCH и @LEAD опираются на:

- `ARCH_*` (архитектурный контракт модуля);
- `DEV_PROMPTS_*` (пошаговая реализация);
- `DEV_TODOS_*_GAPS.md` (аудит‑хвосты).

Рекомендуемый порядок активации DEV‑работ внутри фаз:

1. **Crosscut:** `DEV_PROMPTS_CROSSCUT_EVENT_CONTEXT_AI.md` + `DEV_TODOS_CROSSCUT_EVENT_CONTEXT_AI_GAPS.md`.
2. **ERP+Loyalty:** `DEV_PROMPTS_ERP_FINANCE_AND_INVENTORY.md`, `DEV_PROMPTS_LOYALTY_SUBSCRIPTIONS.md` + их `_GAPS`.
3. **CRM+Tasks:** `DEV_PROMPTS_CRM_KANBAN.md`, `DEV_PROMPTS_RBAC_AND_TASKS.md` + `_GAPS`.
4. **Paperless:** `DEV_PROMPTS_PAPERLESS_OFFICE.md` + `_GAPS`.
5. **Attribution:** `DEV_PROMPTS_MARKETING_ATTRIBUTION.md` + `_GAPS`.
6. **Frontend UX:** `DEV_PROMPTS_FRONTEND_BUSINESS_OS_UX.md` + `_GAPS`.

