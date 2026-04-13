# Коммерческая ценность проекта (по реализованному коду)

> **Версия:** 2026-04-10 (усиление @LEAD: SaaS-контур, основатель, тарифы, маршрутизация)  
> **Короткая версия для демо/продаж (@QA_ARCH):** [`COMMERCIAL_VALUE_ONE_PAGER_RU.md`](./COMMERCIAL_VALUE_ONE_PAGER_RU.md)  
> **Ограничение:** документ фиксирует только то, что подтверждается артефактами репозитория (роутеры, сервисы, страницы, миграции, тесты). Это **не** TAM/SAM, не прогноз выручки и не конкурентный анализ.

---

## 1) Коротко: что именно продается как продукт

Продукт — это **SaaS Business OS для клиник** с тремя связанными контурами:

- **Публичный SaaS-контур подключения клиники**: `"/"`, `"/pricing"`, `"/signup"` + биллинг/провижининг платформы.
- **Операционный контур клиники**: `"/admin/*"` (запись, чаты, задачи, финансы, отчеты, ERP, CRM и т.п.).
- **Пациентский контур**: `"/c/:clinicSlug/*"` и `"/app/*"` (запись, коммуникация, профиль, формы, лояльность).

Отдельный управленческий контур — **кабинет основателя платформы** `"/platform/*"` (авторизация, внутренние SaaS-операции).

---

## 2) Для кого ценность (из UX и доменной модели)

- **Клиника/сеть клиник:** `Organization`, `Clinic`, админские роли и права, модульный доступ по edition и entitlement.
- **Пациент:** PWA/веб-контур self-service.
- **Платформа-владелец SaaS (основатель):** отдельный auth-realm и внутренние платформенные API.
- **Публичный входящий трафик:** маркетинг, тарифы, signup, SEO-страницы врачей.

---

## 3) SaaS-ценность как цепочка монетизации (от трафика до активации)

### 3.1. Вход в воронку: каталог и signup

- **Frontend:** `"/pricing"`, `"/signup"` (маркетинговый контур, отдельные страницы в SPA).
- **Backend:** `public_platform_catalog`, `public_platform_signup`, `platform_billing`.
- **Ценность:** клиника может пройти путь «выбор плана → оформление → оплата» без ручного пресейла на каждом шаге.

### 3.2. Платформенный биллинг (контур B)

- **Backend:** `platform_billing`, отдельный webhook YooKassa для платформы и отдельный секрет (`PLATFORM_BILLING_WEBHOOK_SECRET`), независимый от пациентских платежей.
- **Ценность:** разделение денежных контуров снижает риск смешения данных и инцидентов при эксплуатации.

### 3.3. Провижининг и выдача доступа владельцу

- **Backend:** `public_platform_owner_invite`, `platform_internal`, процессы платформенного провижининга.
- **Frontend:** маршрут очереди провижининга и founder-кабинет (`/platform/*`).
- **Ценность:** оплаченная подписка превращается в рабочую организацию/клинику и доступ owner без второго продукта/репозитория.

### 3.4. Модульное включение функций по entitlement

- **Backend:** `organization_entitlement`, `require_entitlement`.
- **Frontend:** снимок `entitlement_keys` в сессии + `adminEntitlementNav.ts` для скрытия/блокировки сегментов.
- **Ценность:** тарифная дифференциация и поэтапные апгрейды клиента без миграции на другую сборку.

---

## 4) Ценность по функциональным областям (код -> продаваемая возможность)

### 4.1. Онлайн-запись и расписание

- **Backend:** `schedule`, `bookings`, `services`, `doctors`, `admin_schedule`, `admin_doctor_schedule`, `admin_bookings`, `booking_service`, `schedule_service`.
- **Frontend:** `BookingWizardPage`, `SchedulePage`, `AdminBookingsPage`, staff calendar.
- **Ценность:** рост загрузки врачей и снижение ручной координации.

### 4.2. Платежи, предоплата, финконтур клиники

- **Backend:** `payments`, `admin_payment_gateway`, `admin_prepayment`, `admin_finance`, `payment_service`, `finance_service`, YooKassa client.
- **Frontend:** `AdminPaymentGatewayPage`, `AdminPrepaymentPage`, `AdminFinancePage`, `BookingSuccessPage`.
- **Ценность:** monetization визита и финансовая дисциплина внутри клиники.

### 4.3. Пациентский self-service (PWA)

- **Backend:** `patient_chat`, `patient_notification_settings`, `patient_loyalty`, `patient_forms`, `auth`, OAuth.
- **Frontend:** `HomePage`, `ChatPage`, `ProfilePage`, `FormsPage`, `LoyaltyPage`, `HistoryPage`, `FeedPage`.
- **Ценность:** удержание и снижение нагрузки на регистратуру через цифровой канал.

### 4.4. Омниканал и операторская консоль

- **Backend:** `admin_omni_chat`, `admin_omni_chat_closure_tags`, `owner_omni_channels`, `owner_omni_ai_settings`, `owner_omni_audit`, `integrations_gateway`, `omnichannel_*`, `realtime/omni_pubsub.py`.
- **Frontend:** `AdminOmniChatPage`, страницы каналов/интеграций/vault/AI.
- **Ценность:** единый inbox обращений и контроль SLA ответа.

### 4.5. Маршрутизация обращений и лидов

- **Backend:** `admin_lead_logs`, `admin_leads_log_routing`, сервисы lead routing/атрибуции, связанные migration-артефакты.
- **Frontend:** `AdminLeadsLogPage`, CRM/sales контур.
- **Ценность:** контролируемое распределение лидов и меньше потерь на ручной передаче.

### 4.6. Внутренняя коллаборация персонала

- **Backend:** `admin_staff_collab`, staff chat/feed/calendar, `staff_collaboration_service`, Celery `staff_collab_tasks`.
- **Frontend:** `AdminStaffChatPage`, `AdminDashboardPage` (лента), `AdminStaffCalendarPage`, `AdminKnowledgePage`, `AdminAttentionPage`.
- **Ценность:** отдельный внутренний контур коммуникаций (не смешан с пациентским омниканалом).

### 4.7. CRM, продажи, удержание (enterprise-контур)

- **Backend:** `admin_crm`, `admin_retention`, `admin_marketing*`, `require_crm_enterprise_edition`.
- **Frontend:** `AdminSalesPipelinePage`, `AdminRetentionPage`, `AdminMarketingPage`.
- **Ценность:** upsell до уровня revenue operations для клиники.

### 4.8. Задачи и операционная дисциплина

- **Backend:** `admin_tasks`, `admin_task_boards`, `admin_task_streams`, `admin_task_tags`, `task_service`, связи tasks<->attention.
- **Frontend:** `AdminTasksPage`, `AdminTaskDetailsPage` (Kanban/dnd-kit).
- **Ценность:** управляемое исполнение между чатами, CRM и расписанием.

### 4.9. ERP-витрины, отчеты, зарплата, склад

- **Backend:** `admin_reports`, `admin_reports_aggregate`, `admin_payroll`, `admin_inventory`, Celery `erp_tasks`, aggregate-сервисы/репозитории.
- **Frontend:** `AdminReportsPage`, `AdminFinancePage` + смежные ERP-экраны.
- **Ценность:** финансовая/операционная аналитика в одном продукте.

### 4.10. Лояльность, семьи, абонементы

- **Backend:** `admin_loyalty`, `patient_loyalty`, `loyalty_campaign_engine`, family links, wallet.
- **Frontend:** `AdminLoyaltyPage`, `LoyaltyPage`.
- **Ценность:** повторные визиты и рост lifetime value клиента клиники.

### 4.11. Формы, согласия, paperless

- **Backend:** `admin_forms`, `patient_forms`, `forms_service`, `form_status_service`, token-based form links.
- **Frontend:** `AdminFormsPage`, `FormsPage`, `AdminAgreementsPage`.
- **Ценность:** цифровой pre-visit/post-visit документооборот.

### 4.12. Медданные и доступ к чувствительной информации

- **Backend:** `admin_patient_medical`, медвизиты/диагнозы/файлы, S3 medical prefix, audit logs, permissions `patients.medical.*`, `patients.pii.read`.
- **Frontend:** пациентские сущности и медвкладки в админке через соответствующие хуки.
- **Ценность:** единое клиническое досье в рамках одной платформы.

### 4.13. AI-ассистент и автоматизация оператора

- **Backend:** `ai_agent`, `admin_ai_*`, `admin_patient_ai`, `omnichannel_ai_orchestrator`, `safe_ai_client`.
- **Frontend:** AI settings/reports и AI-элементы в операционных экранах.
- **Ценность:** ускорение обработки обращений и подготовки действий.

### 4.14. Embed, RAG KB, экспорт данных организации

- **Backend:** `public_embed`, `admin_embed`, `admin_rag_kb`, `admin_organization_data_export`, `organization_embed_*`, `organization_rag_kb_*`.
- **Frontend:** `AdminEmbedPage`, `AdminRagKbPage`, `AdminDataExportPage`.
- **Ценность:** внешние каналы, база знаний организации, управляемый offboarding.

### 4.15. Commerce (магазин/сеть)

- **Backend:** `admin_commerce`, `admin_commerce_network`, `public_commerce` (read-only витрина для PWA), `commerce_*`, импорт номенклатуры (`commerce_import_job_service`).
- **Frontend:** `AdminCommercePage`; пациентское приложение — `StorePage` (`/app/store`) при включённой витрине клиники.
- **Ценность:** дополнительный вертикальный контур для сетей; показ ассортимента пациенту без обязательного checkout в текущем срезе.
- **План и ADR:** `docs/architecture/domains/COMMERCE_STORE_ARCHITECTURE_PLAN.md`, ADR-013.

### 4.16. Безопасность, роли, аудит, эксплуатация

- **Backend:** `admin_rbac_management`, `rbac_matrix`, аудитные сущности, rate limits, health/metrics.
- **Infra в репозитории:** Grafana/Prometheus (`deploy/*`), CI-проверки.
- **Ценность:** ниже cost of ownership и выше управляемость SaaS-операций.

---

## 5) Тарифная и продуктовая матрица (из кода, без маркетинговых обещаний)

| Уровень | Что реально ограничивает |
|---|---|
| **Box / basic** | Срез enterprise-модулей (например sales/retention): скрытие сегментов в UI + backend-gate (`require_crm_enterprise_edition`). |
| **Enterprise** | Доступ к расширенным CRM/retention/marketing-возможностям. |
| **SaaS entitlements (org-level)** | Тонкая модульная матрица по ключам (`organization_entitlements`) и проверкам `require_entitlement`; UI получает `entitlement_keys` в сессии и отражает гейты по сегментам. |

**Практическая ценность для продаж:** можно продавать не только "пакет edition", но и поэтапное включение модулей у действующей клиники.

---

## 6) Роль основателя платформы (отдельная ценность B2B2C)

- Отдельный маршрутный контур `"/platform/*"` и отдельный auth-realm (включая MFA-сценарий).
- Внутренние операции платформы (провижининг/управление SaaS-контуром) не смешаны с админкой конкретной клиники.
- Для production предусмотрен отдельный секрет founder JWT (разделение рисков между tenant-контуром и платформенным контуром).

**Коммерческий смысл:** управляемое масштабирование SaaS-операций без ручного ad-hoc доступа в tenant-приложение.

---

## 7) Что здесь сознательно НЕ утверждается

- Не утверждаются TAM/SAM, юнит-экономика, фактическая выручка и market share.
- Не утверждаются юридические сертификаты (152-ФЗ/GDPR/HIPAA) без внешних юридических артефактов.
- Не утверждается полнота отраслевого ERP сверх того, что подтверждено миграциями/роутерами/страницами.

---

## 8) Ключевые ссылки на кодовые источники

- `src/api/v1/router.py`
- `frontend/src/App.tsx`
- `frontend/src/routePaths.ts`
- `src/core/edition.py`
- `frontend/src/config/edition.ts`
- `frontend/src/admin/adminEntitlementNav.ts`
- сервисы и оркестраторы в `src/application/services/`
- платформенные и биллинговые роутеры `platform_*`, `public_platform_*`, `payments`, `admin_leads_log_routing`
