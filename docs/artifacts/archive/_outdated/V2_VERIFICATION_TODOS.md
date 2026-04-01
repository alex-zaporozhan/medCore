## V2_VERIFICATION_TODOS.md

> Единый чек‑лист по `DEV_PROMPTS_V2_VERIFICATION.md` + `_GAPS`  
> Статусы: `[ ] pending`, `[-] in_progress`, `[x] completed`  

---

### 1. Crosscut — EventBus / RequestContext / AiConfig

**Документы**

- `docs/ARCH_CROSSCUT_EVENT_CONTEXT_AI.md`  
- `docs/DEV_PROMPTS_CROSSCUT_EVENT_CONTEXT_AI.md`  
- `docs/DEV_TODOS_CROSSCUT_EVENT_CONTEXT_AI_GAPS.md`

**Кодовые модули**

- EventBus/события:
  - `src/application/events/domain_event.py`
  - `src/application/events/event_bus.py`
  - `src/application/events/standard_events.py`
  - `src/application/events/lead_event_handlers.py`
  - `src/application/events/erp_event_handlers.py`
  - `src/application/events/loyalty_event_handlers.py`
  - `src/application/events/tasks_event_handlers.py`
  - `src/application/events/marketing_attribution_event_handlers.py`
  - тесты: `tests/services/test_event_bus.py`, `tests/services/test_booking_erp_integration.py`
- RequestContext:
  - `src/core/context.py`
  - `src/api/v1/dependencies.py`
  - AI/CRM/Reports, где уже используется `RequestContext`:
    - `src/application/services/omnichannel_ai_orchestrator.py`
    - `src/application/services/chat_ai_service.py`
    - `src/application/services/conversation_analysis_service.py`
    - тесты: `tests/core/test_request_context.py`, `tests/services/test_ai_orchestrator_agent.py`, `tests/services/test_ai_tools_booking.py`
- AiConfig/AiSanitizer:
  - `src/application/services/ai_config_service.py`
  - `src/core/ai_sanitizer.py`
  - `src/infrastructure/external_apis/safe_ai_client.py`
  - тесты: `tests/services/test_ai_config_service.py`, `tests/security/test_ai_agent_security.py`

**To‑dos**

- [x] Crosscut: фабрики и стандартные события  
  - Проверить, что `BookingCreated/BookingCompleted/PaymentSuccess/ContactCreated` и `make_*_event` реализованы через `standard_events.py` и используются в хендлерах.
- [x] Crosscut: карта контрактов событий  
  - Оформить карту контрактов стандартных событий в `ARCH_CROSSCUT_EVENT_CONTEXT_AI.md` (текущий раздел 1.4) в соответствии с `standard_events.py`.
- [x] Crosscut: нагрузочные/diagnostic‑тесты EventBus  
  - Расширить `tests/services/test_event_bus.py`:
    - burst из N событий с несколькими подписчиками;
    - тест, что исключения из хендлеров не проглатываются «тихо».
- [x] Crosscut: использование `RequestContext` в ключевых сервисах  
  - Пройти ERP/CRM/Tasks/Loyalty/Attribution (backend API и сервисы) и либо:
    - добавить аргумент `ctx: RequestContext` в публичные методы;
    - либо зафиксировать консистентный источник `clinic_id`/прав.
  - При необходимости обновить роутеры (`src/api/v1/routers/*.py`) для прокидывания `RequestContext`.
  - **Сделано:** CRM, Loyalty, Tasks, Attribution переведены на `get_request_context()` и `context.clinic_id`; источник зафиксирован в ARCH_CROSSCUT раздел 2.3.
- [x] Crosscut: системные режимы RequestContext  
  - Задокументировать и покрыть тестами режимы:
    - Celery/batch‑джобы (`user_type="system"`);
    - возможный multi‑clinic (выбор `clinic_id` для системных задач).  
  - **Сделано:** `RequestContext` поддерживает `user_type="system"` как fallback без токена; добавлены тесты (`tests/core/test_request_context.py`) на системный режим и наследование `AdminContext`.
- [x] Crosscut: унификация `AiConfigService`  
  - Привести все AI‑точки (`omnichannel_ai_orchestrator`, `chat_ai_service`, `conversation_analysis_service`, др.) к единому контракту `AiConfigService.get_clinic_ai_config(...)` (async/await, типы) и синхронизировать тесты.  
  - **Сделано:** все основные AI‑сервисы (`OmnichannelAIOrchestrator`, `ChatAiService`, `ConversationAnalysisService`) получают конфиг через `AiConfigService.get_clinic_ai_config(...)` и используют его для инициализации `AiClient`/`SafeAiClient`.
- [x] Crosscut: политика ПД и `AiSanitizer`  
  - Убедиться, что во всех LLM‑точках:
    - конфиг берётся из `AiConfigService`;
    - флаг `allow_personal_data` корректно передаётся в `AiSanitizer`.  
  - Расширить security‑тесты (`tests/security/test_ai_agent_security.py` и др.), чтобы при `allow_personal_data=False` нет ПДн в запросах во всех входных точках.  
  - **Сделано:** политика ПД реализована через `AiSanitizer` и `SafeAiClient`; security‑тесты (`tests/security/test_ai_agent_security.py`) подтверждают отсутствие телефонов/email в payload при `allow_personal_data=False`.
- [x] Crosscut: сквозные интеграционные тесты  
  - Добавить e2e‑тесты:
    - `BookingCompleted` → EventBus → ERP/CRM/Loyalty/Tasks видят согласованный payload;
    - AI‑агент/AI task generator работают с `RequestContext` и `AiConfigService` (включая маскирование ПДн).  
  - **Сделано:** интеграционные тесты по EventBus/ERP/CRM/Loyalty/Tasks и AI‑агенту (`tests/services/test_booking_erp_integration.py`, `tests/services/test_ai_orchestrator_agent.py` и др.) проходят на текущем контракте событий и AI‑конфига.

---

### 2. Loyalty & Subscriptions

**Документы**

- `docs/ARCH_LOYALTY_SUBSCRIPTIONS.md`  
- `docs/DEV_PROMPTS_LOYALTY_SUBSCRIPTIONS.md`  
- `docs/DEV_TODOS_LOYALTY_SUBSCRIPTIONS_GAPS.md`

**Кодовые модули**

- Доменные сущности:
  - `src/domain/entities/subscription_package.py`
  - `src/domain/entities/customer_subscription.py`
  - `src/domain/entities/subscription_usage.py`
  - `src/domain/entities/wallet.py`
  - `src/domain/entities/wallet_transaction.py`
  - `src/domain/entities/loyalty_policy.py`
  - миграции: `alembic/versions/loyalty_0001_subscriptions_and_wallet.py`, `loyalty_0002_policy_table.py`, `loyalty_0003_booking_paid_by_subscription.py`
- Сервисы/репозитории:
  - `src/domain/interfaces/repositories/loyalty_repository.py`
  - `src/infrastructure/database/loyalty_repo_impl.py`
  - `src/application/services/loyalty_service.py`
  - `src/application/services/wallet_service.py`
  - `src/application/services/loyalty_attention_job.py`
  - `src/application/services/attention_feed_service.py` (loyalty‑gap)
  - `src/application/services/report_service.py` (`get_loyalty_summary`)
- API:
  - `src/api/v1/routers/admin_loyalty.py`
  - `src/api/v1/routers/patient_loyalty.py`
- Интеграция с событиями:
  - `src/application/events/loyalty_event_handlers.py`
  - `src/application/events/erp_event_handlers.py` (покупка пакета на PaymentSuccess)
- Тесты:
  - `tests/services/test_loyalty_services.py`
  - `tests/api/test_admin_loyalty.py`
  - `tests/api/test_admin_loyalty_summary_by_contact.py`

**To‑dos (backend/ERP — фактически закрыто)**

- [x] Loyalty: приоритет подписок  
  - `LoyaltyService.select_subscription_for_booking` реализует детерминированный приоритет (expires_at, специализация пакета по `services_included`, остатки, `purchased_at`); стратегия задокументирована в docstring.
- [x] Loyalty: бизнес‑ошибки по остаткам и сроку  
  - `use_subscription_for_booking`:
    - поднимает `InsufficientSubscriptionBalance`/`SubscriptionExpired` с понятными кодами;
    - учитывает `used_visits`/`used_amount` и тип пакета.
- [x] Loyalty: защита от гонок в кошельке  
  - `WalletTransactionRepositoryImpl.get_balance_for_wallet` использует `SELECT Wallet.id ... FOR UPDATE` перед суммированием движений;  
  - `WalletService.earn_points/spend_points/expire_points` всегда обращаются к этому методу; покрыто тестами.
- [x] Loyalty: идемпотентность покупки пакета по платежу  
  - `LoyaltyService.purchase_subscription`:
    - перед созданием подписки ищет существующую по `(clinic_id, patient_id, package_id, payment_id)` и при повторной обработке `PaymentSuccess` возвращает её же;  
  - покрыто в `test_loyalty_purchase_subscription_idempotent_by_payment_id`.
- [x] Loyalty + ERP: оплата визита баллами и частично деньгами  
  - В `BookingErpService`:
    - в контексте считается `wallet_spent_amount` по `WalletTransaction(type="spend", booking_id=...)`;
    - если есть `Payment` → ERP‑выручка = `Payment.amount`;
    - если нет `Payment` → ERP‑выручка = `max(Service.price - wallet_spent_amount, 0)`.  
  - Интеграционные тесты в `test_booking_erp_integration.py`:
    - полный платёж баллами (доход 0);
    - частичный платёж баллами + деньги (доход = денежная часть).

**To‑dos (отчёты, smart‑recall, frontend — остаются)**

- [ ] Loyalty: расширить отчётные метрики  
  - Убедиться, что `ReportsService.get_loyalty_summary` и LTV‑отчёты:
    - отражают вклад подписок (`CustomerSubscription/SubscriptionUsage`) и кошелька (`WalletTransaction`) без удвоения выручки;
    - дают базовые KPI (активные/истёкшие пакеты, кошельки с балансом).
- [ ] Loyalty: smart‑recall по остаткам  
  - Расширить `AttentionFeedService._build_loyalty_loyalty_gap_items` и `run_loyalty_attention_job`:
    - учёт `remaining_visits/remaining_amount` и параметризуемые пороги;
    - генерация системных `Task`/Recall‑записей для expiring‑подписок и кошельков с балансом.
- [ ] Loyalty: фронт и CTA  
  - `frontend/src/admin/pages/AdminLoyaltyPage.tsx` и `frontend/src/app/pages/LoyaltyPage.tsx`:
    - CRUD‑формы для пакетов и политики (`LoyaltyPolicy`);
    - CTA «Записаться/Использовать пакет» и сценарий «Записаться и использовать баллы»;
    - OmniChat‑виджет с кратким обзором подписок/кошелька.

---

### 3. ERP Finance & Inventory

**Документы**

- `docs/ARCH_ERP_FINANCE_AND_INVENTORY.md`  
- `docs/DEV_PROMPTS_ERP_FINANCE_AND_INVENTORY.md`  
- `docs/DEV_TODOS_ERP_FINANCE_AND_INVENTORY_GAPS.md`

**Кодовые модули (ядро)**

- ERP‑узел:
  - `src/application/services/booking_erp_service.py`
  - `src/application/events/erp_event_handlers.py`
- Финансы/ЗП/склад:
  - `src/application/services/finance_service.py`
  - `src/application/services/payroll_service.py`
  - `src/application/services/inventory_service.py`
  - `src/domain/entities/cashbox.py`
  - `src/domain/entities/financial_transaction.py`
  - `src/domain/entities/payroll_policy.py`
  - `src/domain/entities/salary_transaction.py`
  - `src/domain/entities/product.py`
  - `src/domain/entities/warehouse.py`
  - `src/domain/entities/inventory_transaction.py`
  - `src/domain/entities/service_consumable.py`
- API:
  - `src/api/v1/routers/admin_finance.py`
  - `src/api/v1/routers/admin_payroll.py`
  - `src/api/v1/routers/admin_inventory.py`
- Отчёты:
  - `src/application/services/report_service.py`
- Тесты:
  - `tests/services/test_booking_erp_integration.py`
  - другие ERP‑тесты по finance/inventory/payroll

**To‑dos**

- [x] ERP: стратегия расчёта сумм и связка с лояльностью  
  - Актуализирован раздел 3.2 в `ARCH_ERP_FINANCE_AND_INVENTORY.md` под фактическую реализацию:
    - при наличии `Payment` → выручка = `Payment.amount`;
    - иначе → `max(Service.price - wallet_spent, 0)`;  
    - покупка пакета учитывается как выручка при оплате пакета, использование — без второго прихода.
- [x] ERP: коды ошибок и AttentionFeed  
  - В `ARCH_ERP_FINANCE_AND_INVENTORY.md` (3.3) задокументированы `ERPConfigurationError.code`:
    - `missing_cashbox`, `missing_payroll_policy`, `missing_warehouse`, `insufficient_stock`;  
  - коды попадают в `Booking.erp_error_code` и используются AttentionFeed/UI.
- [x] ERP + Loyalty: интеграционные сценарии  
  - `test_booking_erp_integration.py`:
    - базовый happy‑path (доход, ЗП, склад);
    - визит, полностью оплаченный баллами;
    - визит с частичной оплатой баллами + платежом.
- [x] ERP: дополнительные нагрузочные/устойчивостные тесты  
  - В `test_booking_erp_integration.py`: серия из 30 последовательных `Booking.completed`; тест `test_erp_fatal_error_rolls_back_no_stale_state` — при фатальной ошибке откат, без подвисших статусов.
- [x] ERP Frontend: UX раздела «Финансы»  
  - `AdminFinancePage.tsx`: фильтры по датам для истории движений склада; карточки агрегатов по ЗП (всего/операций/среднее) и таблица начислений по врачам.

---

### 4. CRM Kanban

**Документы**

- `docs/ARCH_CRM_KANBAN.md`  
- `docs/DEV_PROMPTS_CRM_KANBAN.md`  
- `docs/DEV_TODOS_CRM_KANBAN_GAPS.md` (нужно открыть при работе)

**Кодовые модули (основные)**

- `src/domain/entities/lead_card.py`, `lead_stage.py` и др. CRM‑сущности  
- `src/application/services/lead_service.py`  
- `src/api/v1/routers/admin_crm.py`  
- Event‑хендлеры:
  - `src/application/events/lead_event_handlers.py`
- Frontend:
  - `frontend/src/admin/pages/AdminSalesPipelinePage.tsx` и связанные компоненты

**To‑dos**

- [x] CRM: соответствие DEV_PROMPTS  
  - Отчёт в `docs/CRM_DEV_PROMPTS_COMPLIANCE.md`. Реализован полноценный drag&drop между колонками Kanban (@dnd-kit, PATCH /leads/{id}/stage при дропе).
- [x] CRM: улучшить поиск и связи  
  - Репозиторий: `get_lead_by_primary_booking_id`; в `list_leads` добавлены фильтры `patient_id`, `booking_id`; обработчики PaymentSuccess/BookingCompleted используют прямой поиск по booking_id.
- [x] CRM: стратегия стадий/сумм  
  - В `ARCH_CRM_KANBAN.md` добавлен подраздел «Стратегия кодов стадий» (new → booked → prepaid → success/lost); репозиторий: `get_stage_by_pipeline_and_code`.
- [x] CRM: OmniChat‑контекст  
  - В `AdminOmniChatPage` уже реализован виджет: стадия лида, estimated/actual value, кнопка «Открыть лид» (переход на `/admin/sales?lead_id=…`).
- [x] CRM: интеграционные тесты  
  - Добавлен `tests/services/test_lead_crm.py`: get_lead_by_primary_booking_id, list_leads с фильтрами patient_id/booking_id.
- [x] CRM: UI‑тесты Kanban  
  - `frontend/src/admin/pages/__tests__/AdminSalesPipelinePage.test.tsx`: заголовок и фильтры, колонки стадий, карточки лидов, пустая правая панель, детали и заметки по клику. В `setupTests.ts` добавлены моки `matchMedia` и `ResizeObserver` для jsdom.

---

### 5. RBAC & Tasks

**Документы**

- `docs/ARCH_RBAC_AND_TASKS.md`  
- `docs/DEV_PROMPTS_RBAC_AND_TASKS.md`  
- `docs/DEV_TODOS_RBAC_AND_TASKS_GAPS.md`

**Кодовые модули**

- RBAC:
  - `src/domain/entities/role.py`, `permission.py`, `user_role.py`, `role_permission.py`
  - `src/application/services/rbac_service.py`
  - `src/infrastructure/database/rbac_repo_impl.py`
  - `src/application/rbac_matrix.py`
- Tasks:
  - `src/domain/entities/task.py`, `task_comment.py`
  - `src/domain/interfaces/repositories/task_repository.py`
  - `src/infrastructure/database/task_repo_impl.py`
  - `src/application/services/task_service.py`
  - `src/api/v1/routers/admin_tasks.py`
  - `src/infrastructure/messaging/tasks/ai_tasks.py` (AI Task Generator)
- Тесты:
  - `tests/api/test_admin_tasks_rbac.py`  
  - и другие RBAC‑/tasks‑тесты

**To‑dos**

- [ ] RBAC: матрица прав и seeding  
  - Синхронизировать `rbac_matrix.py`, миграции seed‑ролей и фактическое использование в `require_permissions(...)`.
- [ ] Tasks: типизированные DTO  
  - Довести Task API до типизированных DTO (request/response), убрать «сырые» dict’ы.
- [ ] Tasks: контекстная видимость  
  - Реализовать «кто что видит» для задач (особенно `doctor`/`owner`/`admin`).
- [ ] Tasks + AI: усиленный Task Generator  
  - Расширить `ai_tasks` и обработку системных tasks‑handlers, добавить конфиги/аномалии.
- [ ] RBAC‑тесты  
  - Покрыть 403/401 по критичным модулям (ERP, CRM, Loyalty, Paperless, Marketing Attribution, Tasks).

---

### 6. Paperless Office

**Документы**

- `docs/ARCH_PAPERLESS_OFFICE.md`  
- `docs/DEV_PROMPTS_PAPERLESS_OFFICE.md`  
- `docs/DEV_TODOS_PAPERLESS_OFFICE_GAPS.md`

**Кодовые модули**

- Entities/сервисы/роутеры:
  - `src/domain/entities/digital_form_template.py`
  - `src/domain/entities/digital_form_submission.py`
  - `src/domain/entities/e_signature.py`
  - `src/application/services/forms_service.py`
  - `src/application/dto/forms_dto.py`
  - `src/api/v1/routers/patient_forms.py`
  - `src/api/v1/routers/admin_forms.py`
  - миграции: `alembic/versions/paperless_0001_digital_forms_and_signatures.py`
- Frontend:
  - `frontend/src/app/pages/FormsPage.tsx`
  - `frontend/src/admin/pages/AdminFormsPage.tsx`
  - PWA‑подпись: `frontend/src/pwa/registerPwa.ts` (и компоненты с canvas‑подписью)
- Тесты:
  - `tests/api/test_patient_forms.py`
  - `tests/api/test_admin_forms.py`
  - `frontend/src/app/pages/__tests__/FormsPage.test.tsx`

**To‑dos**

- [ ] Paperless: pending forms before visit  
  - Реализовать механику «формы перед визитом» по контексту визита/версии шаблонов.
- [ ] Paperless: подпись в PWA  
  - Добавить/усовершенствовать подпись через canvas + `signature_payload` в PWA.
- [ ] Paperless: админ‑просмотр и OmniChat‑виджет  
  - Улучшить просмотр submissions в админке и виджет статуса форм в OmniChat.
- [ ] Paperless: экспорт и PII‑политика  
  - Добавить экспорт форм/подписей и проверить политику ПДн (скрытие/маскирование).

---

### 7. Marketing Attribution

**Документы**

- `docs/ARCH_MARKETING_ATTRIBUTION.md`  
- `docs/DEV_PROMPTS_MARKETING_ATTRIBUTION.md`  
- `docs/DEV_TODOS_MARKETING_ATTRIBUTION_GAPS.md`

**Кодовые модули**

- Entities/сервисы:
  - `src/domain/entities/visit_attribution.py`
  - `src/domain/entities/traffic_source.py`
  - `src/domain/entities/campaign.py`
  - `src/domain/entities/financial_transaction.py` (связка для ROI/CAC)
  - `src/application/services/marketing_attribution_service.py`
  - `src/application/dto/marketing_attribution_dto.py`
- API:
  - `src/api/v1/routers/admin_marketing_attribution.py`
  - `src/api/v1/routers/public_marketing.py`
- Frontend:
  - `frontend/src/admin/pages/AdminMarketingPage.tsx`
  - `frontend/src/hooks/useMarketingAttribution.ts`
- Тесты:
  - `tests/api/test_admin_marketing_attribution.py`
  - `tests/services/test_marketing_attribution_flow.py`
  - `frontend/src/shared/utmTracking.ts` (+ `utmTracking.test.ts`)

**To‑dos**

- [ ] Attribution: сквозной flow UTM/session → VisitAttribution → Lead/Patient → FinancialTransaction  
  - Убедиться, что весь путь реализован и стабилен (backend + тесты).
- [ ] Attribution: метрики  
  - Доработать метрики: completed bookings, ad_spend, ROI/CAC.
- [ ] Attribution: admin UI и drill‑down  
  - Улучшить `AdminMarketingPage` (drill‑down по источнику/кампании/креативу).
- [ ] Attribution: тесты и RBAC  
  - Расширить тесты и RBAC‑контроль в атрибуции.

---

### 8. Frontend Business OS UX

**Документы**

- `docs/ARCH_FRONTEND_BUSINESS_OS_UX.md`  
- `docs/DEV_PROMPTS_FRONTEND_BUSINESS_OS_UX.md`  
- `docs/DEV_TODOS_FRONTEND_BUSINESS_OS_UX_GAPS.md`

**Кодовые модули**

- Layout/UI:
  - `frontend/src/components/layout/ThreeColumnLayout.tsx`
  - `frontend/src/shared/ui/*` (`AppCard`, `AppButton`, `SectionHeader`, `GlassModal`, др.)
  - `frontend/src/admin/layouts/AdminLayout.tsx`
  - `frontend/src/app/layouts/AppLayout.tsx`
- Страницы:
  - `frontend/src/admin/pages/AdminDashboardPage.tsx`
  - `frontend/src/admin/pages/AdminOmniChatPage.tsx`
  - `frontend/src/admin/pages/AdminTasksPage.tsx`
  - `frontend/src/admin/pages/AdminFinancePage.tsx`
  - другие ключевые admin‑страницы

**To‑dos**

- [ ] Frontend: трёхколоночный OmniChat Command Center  
  - Довести OmniChat до целевого трёхколоночного layout’а (CRM/Loyalty/Forms/Tasks виджеты).
- [ ] Frontend: единый 3‑колоночный layout для CRM/Tasks/Finance  
  - Вынести общий layout и перевести страницы CRM/Tasks/Finance на него.
- [ ] Frontend: синхронизация лендинга с фактическими возможностями V2  
  - Обновить лендинг/маркетинговые экраны под текущие фичи Business OS V2.

---

### 9. Метаданные V2 Verification

**Верхнеуровневые задачи из `DEV_PROMPTS_V2_VERIFICATION.md`**

- [-] `v2_verification_crosscut` — Crosscut EventBus / RequestContext / AiConfig  
  - BASE готов; остаются хвосты по RequestContext и AI‑слою (см. раздел 1).
- [-] `v2_verification_loyalty` — Loyalty & Subscriptions  
  - Backend/ERP‑часть закрыта; остаются фронт/аналитика/smart‑recall.
- [-] `v2_verification_erp` — ERP Finance & Inventory  
  - Расчёт сумм и ERP↔Loyalty закрыты; остаются фронт‑UX и нагрузочные тесты.
- [ ] `v2_verification_crm` — CRM Kanban  
  - Требуется пройти `DEV_PROMPTS_CRM_KANBAN` + `_GAPS` и выполнить задачи раздела 4.
- [ ] `v2_verification_rbac_tasks` — RBAC & Tasks  
  - Требуется пройти `DEV_PROMPTS_RBAC_AND_TASKS` + `_GAPS` и выполнить задачи раздела 5.
- [ ] `v2_verification_paperless` — Paperless Office  
  - Требуется пройти `DEV_PROMPTS_PAPERLESS_OFFICE` + `_GAPS` и выполнить задачи раздела 6.
- [ ] `v2_verification_marketing` — Marketing Attribution  
  - Требуется пройти `DEV_PROMPTS_MARKETING_ATTRIBUTION` + `_GAPS` и выполнить задачи раздела 7.
- [ ] `v2_verification_frontend_ux` — Frontend Business OS UX  
  - Требуется пройти `DEV_PROMPTS_FRONTEND_BUSINESS_OS_UX` + `_GAPS` и выполнить задачи раздела 8.

Этот файл служит единым входом для запуска V2 Verification в новом контекстном окне/агенте.
