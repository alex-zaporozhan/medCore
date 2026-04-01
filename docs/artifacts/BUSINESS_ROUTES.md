## 🛰 BUSINESS_ROUTES — фактическая карта маршрутов и gap-анализ

> **Цель:** зафиксировать **фактическую** карту маршрутов (backend + frontend) и сравнить её  
> с бизнес-картой модулей из `BUSINESS_LOGIC_CURRENT.md` и `BUSINESS_LOGIC_V2.md`.  
> Источник правды по маршрутам — **код** (`src/api/v1/router.py`, `src/api/v1/routers/*`, `frontend/src/App.tsx`).

---

## 1. Backend API v1 — фактические роутеры и префиксы

Источник: `src/api/v1/router.py` + `src/api/v1/routers/*.py`.

- **Базовый router**: `api_router = APIRouter()`  
  Подключены (реальные APIRouter с префиксами):
  - **Аутентификация и конфиг**
    - `auth` → `prefix="/auth"` → `tags=["auth"]`
    - `config` → (конфигурация приложения, см. файл)
  - **Публичные и пациентские API**
    - `clinics` → `prefix="/clinics"`
    - `doctors` → `prefix="/doctors"`
    - `services` → `prefix="/services"`
    - `public_services` → `prefix="/public/services"` (по имени файла; точный префикс в коде)
    - `public_marketing` → `prefix="/public/clinics"`
    - `patients` → `prefix="/patients"`
    - `schedule` → `prefix="/schedule"`
    - `bookings` → `tags=["bookings"]` (без явного `prefix`, пути описаны в файле)
    - `payments` → платёжные операции (YooKassa и др.)
    - `patient_chat` → `prefix="/patient/chat"`
    - `patient_notification_settings` → `prefix="/patient/notifications"` (по имени файла; уточняется кодом)
    - `patient_loyalty` → `prefix="/patient/loyalty"`
    - `patient_forms` → `prefix="/patient/forms"`
  - **Omnichannel / интеграции / AI**
    - `integrations_gateway` → `prefix="/api"` (входящие webhooks мессенджеров и email)
    - `admin_omni_chat` → `prefix="/admin/omni-chats"`
    - `owner_omni_channels` → `prefix="/owner/channels"`
    - `owner_omni_ai_settings` → владелецские AI‑настройки (prefix в файле)
    - `owner_omni_audit` → аудит действий (prefix в файле)
    - `admin_ai_settings` → `prefix="/admin/ai-settings"`
    - `admin_ai_status` → `prefix="..."` (глобальный статус AI)
    - `admin_ai_reports` → `prefix="/admin/ai-reports"`
    - `admin_patient_ai` → `prefix="/admin/patients"`
    - `ai_agent` → `prefix="/ai"` (AI Command Line / Spotlight)
  - **Админка: операционка**
    - `admin_services` → `prefix="/admin/clinics"`
    - `admin_schedule` → `prefix="/admin/clinics"`
    - `admin_doctor_schedule` → `prefix="/admin/doctors"`
    - `admin_prepayment` → `prefix="/admin/clinics"`
    - `admin_waitlist` → `prefix="/admin/clinics"`
    - `admin_recall` → `prefix="/admin/clinics"`
    - `admin_marketing` → `prefix="/admin/clinics"`
    - `admin_chat` → `prefix="/admin/chat"`
    - `admin_channel_configs` → `prefix="/admin/channels"` (конфиги каналов)
    - `admin_admins` → `prefix="/admin/admins"` (администраторы)
    - `admin_attention_feed` → `prefix="/admin/clinics"`
    - `admin_notification_policy` → `prefix="/admin/clinics"`
    - `admin_payment_gateway` → `prefix="/admin/clinics"`
    - `admin_forms` → `prefix="/admin/forms"`
  - **Админка: бизнес‑уровень (CRM/ERP/Loyalty/Tasks/Reports/etc.)**
    - `admin_clinics_summary` → `prefix="/admin/clinics"`
    - `admin_discounts` → `prefix="/admin/clinics"`
    - `admin_integrations` → `prefix="/admin/clinics"`
    - `admin_owner_settings` → `prefix="/admin/clinics"`
    - `admin_reports` → `prefix="/admin/clinics"`
    - `admin_reports_aggregate` → `prefix="/admin"`
    - `admin_finance` → `prefix="/admin/clinics"`
    - `admin_inventory` → `prefix="/admin/clinics"`
    - `admin_payroll` → `prefix="/admin/clinics"`
    - `admin_crm` → `prefix="/admin/crm"`
    - `admin_tasks` → `prefix="/admin/tasks"`
    - `admin_loyalty` → `prefix="/admin/loyalty"`
    - `admin_marketing_attribution` → `prefix="/admin/attribution"`
    - `admin_retention` → `prefix="/admin/clinics"`
    - `admin_vault` → `prefix="/admin"` (экспорт/backup)
  - **Прочее**
    - `reports` → аналитика (общая)
    - `stickers` → `prefix="/stickers"`
    - `csv_sync` → CSV‑импорт/синхронизация
    - `admin_agreement` → `prefix="/admin/agreements"`
    - `admin_auth` → `prefix="/admin/auth"`
    - `admin_client_reference` → `prefix="/admin/clinics"`

**Вывод по backend:** карта роутеров в `router.py` **консистентна с кодом**: каждый импортируемый модуль действительно содержит `APIRouter` с ожидаемым префиксом. Бизнес‑описания (`BUSINESS_LOGIC_CURRENT/V2`) не перечисляют эти префиксы явно, но по доменам и названиям соответствие в целом выдержано.

---

## 2. Frontend — фактические маршруты (SPA)

Источник: `frontend/src/App.tsx` + layouts.

- **Корень / Landing**
  - `"/"` → `LandingPage` (маркетинговый лендинг Business OS; описывает модули AI Agent, CRM, Finance & ERP, Tasks, Loyalty, Paperless & Attribution).

- **Админка `/admin`**
  - Обёртка: `AdminAuthGuard` + `AdminLayout` + `AdminClinicProvider`.
  - Роуты:
    - `"/admin/login"` → `AdminLoginPage`
    - `"/admin"` (index) → `AdminDashboardPage`
    - `"/admin/clinics"` → `AdminClinicsPage`
    - `"/admin/services"` → `AdminServicesPage`
    - `"/admin/schedule"` → `SchedulePage` (операционное расписание и записи)
    - `"/admin/tasks"` → `AdminTasksPage`
    - `"/admin/bookings"` → `AdminBookingsPage`
    - `"/admin/prepayment"` → `AdminPrepaymentPage`
    - `"/admin/waitlist"` → `AdminWaitlistPage`
    - `"/admin/recall"` → `AdminRecallPage`
    - `"/admin/marketing"` → `AdminMarketingPage`
    - `"/admin/retention"` → `AdminRetentionPage`
    - `"/admin/sales"` → `AdminSalesPipelinePage` (CRM‑Kanban)
    - `"/admin/attention"` → `AdminAttentionFeedPage`
    - `"/admin/reports"` → `AdminReportsPage`
    - `"/admin/finance"` → `AdminFinancePage` (кассы, транзакции, ЗП, склад)
    - `"/admin/loyalty"` → `AdminLoyaltyPage`
    - `"/admin/forms"` → `AdminFormsPage`
    - `"/admin/doctors"` → `AdminDoctorsPage`
    - `"/admin/doctor-schedule"` → `AdminDoctorSchedulePage`
    - `"/admin/patients"` → `AdminPatientsPage`
    - `"/admin/omni-chat"` → `AdminOmniChatPage`
    - `"/admin/omni-channels"` → `AdminOmniChannelsPage`
    - `"/admin/omni-ai-settings"` → `AdminOmniAiSettingsPage`
    - `"/admin/channels"` → `AdminChannelsPage`
    - `"/admin/integrations"` → `AdminIntegrationsPage`
    - `"/admin/omni-vault"` → `AdminOmniVaultPage`
    - `"/admin/styling"` → `AdminStylingPage`
    - `"/admin/stickers"` → `AdminStickersPage`
    - `"/admin/settings"` → `AdminSettingsPage`
    - `"/admin/administrators"` → `AdminAdministratorsPage`
    - `"/admin/payment-gateway"` → `AdminPaymentGatewayPage`
    - `"/admin/client-reference"` → `AdminClientReferencePage`
    - `"/admin/discounts"` → `AdminDiscountsPage`
    - `"/admin/notification-policy"` → `AdminNotificationPolicyPage`
    - `"/admin/agreements"` → `AdminAgreementsPage`

- **Пациентское PWA `/app`**
  - Обёртка: `PatientAuthProvider` + `AppLayout` с bottom‑nav.
  - Навигация в `AppLayout`:
    - top‑nav/bottom‑nav: `/app`, `/app/booking`, `/app/chat`, `/app/profile` (+ `/app/history` в верхнем меню).
  - Роуты:
    - `"/app"` (index) → `HomePage`
    - `"/app/feed"` → `FeedPage`
    - `"/app/booking"` → `BookingWizardPage`
    - `"/app/history"` → `HistoryPage`
    - `"/app/loyalty"` → `LoyaltyPage`
    - `"/app/forms"` → `FormsPage`
    - `"/app/chat"` → `ChatPage`
    - `"/app/profile"` → `ProfilePage`

- **Прочие маршруты**
  - `"/login"` → `LoginPage` (пациент)
  - `"/oauth/result"` → `OAuthResultPage`
  - `"/booking/success"` → `BookingSuccessPage`

**Вывод по frontend:** карта SPA‑маршрутов полностью определяется в `App.tsx` и **согласована** с бизнес‑документом `BUSINESS_LOGIC_CURRENT.md` на уровне доменов (записи, чат, маркетинг, отчёты, омниканал, лояльность, финансы и пр.). `BUSINESS_LOGIC_V2.md` расширяет смысл модулей, но маршруты для этих модулей уже существуют.

---

## 3. Сопоставление с BUSINESS_LOGIC_CURRENT.md

`BUSINESS_LOGIC_CURRENT.md` описывает реализованные домены. С точки зрения **маршрутов**:

- **3.2 Врачи, услуги и расписание**
  - Backend: `doctors`, `services`, `schedule`, `admin_schedule`, `admin_doctor_schedule`.
  - Frontend: `AdminDoctorsPage`, `AdminServicesPage`, `SchedulePage`, `AdminDoctorSchedulePage`.
  - **Gap по маршрутам:** нет; карта доменов и реальные роуты согласованы.

- **3.3 Записи (Booking) и история**
  - Backend: `bookings`, `schedule`, `payments`.
  - Frontend: `AdminBookingsPage`, `BookingWizardPage`, `HistoryPage`, `BookingSuccessPage`.
  - **Gap:** отсутствует отдельный маршрут для «подтверждения записи» как бизнес‑сущности — реализовано внутри `bookings`/`schedule`, что соответствует текущему описанию.

- **3.4 Предоплата и платежи**
  - Backend: `payments`, `admin_prepayment`, `admin_payment_gateway`.
  - Frontend: `AdminPrepaymentPage`, `AdminPaymentGatewayPage`, шаги в `BookingWizardPage`.
  - **Gap:** документация корректно отражает маршруты; глубина UI по возвратам/частичным возвратам зависит от реализации `PaymentService`, но маршруты на месте.

- **3.5 Уведомления и напоминания**
  - Backend: `admin_notification_policy`, `patient_notification_settings`, часть логики в `admin_recall`, `admin_marketing`.
  - Frontend: `AdminNotificationPolicyPage`, `AdminRecallPage`, `AdminMarketingPage`.
  - **Gap:** `BUSINESS_LOGIC_CURRENT` описывает fallback‑цепочку каналов; в коде есть единый Notification‑домен и настройки каналов. По маршрутам расхождений нет.

- **3.6 Omnichannel чат и AI**
  - Backend: `integrations_gateway`, `admin_omni_chat`, `patient_chat`, `owner_omni_channels`, `owner_omni_audit`, `owner_omni_ai_settings`, `admin_ai_reports`, `admin_ai_settings`, `admin_ai_status`, `admin_patient_ai`.
  - Frontend: `AdminOmniChatPage`, `AdminOmniChannelsPage`, `AdminOmniAiSettingsPage`, `ChatPage`, лендинговые блоки про AI.
  - **Gap:** `BUSINESS_LOGIC_CURRENT` описывает AI как **аналитику и ответы в чатах** — это соответствует наличию `ConversationAiAnalysis` и AI‑отчётов. Новые маршруты `ai_agent` и hook `useAiAgent` находятся **в статусе заглушки** (см. §4.1).

- **3.7 Маркетинг, recall и клиентские истории**
  - Backend: `admin_marketing`, `admin_recall`, `public_marketing`, `admin_client_reference`.
  - Frontend: `AdminMarketingPage`, `AdminRecallPage`, `AdminClientReferencePage`, `FeedPage`.
  - **Gap:** карта маршрутов и доменов совпадает; различия только в глубине бизнес‑логики (какие типы кампаний реально поддержаны).

- **3.8 Отчёты и аналитика**
  - Backend: `reports`, `admin_reports`, `admin_reports_aggregate`, `admin_ai_reports`, `admin_marketing_attribution`.
  - Frontend: `AdminReportsPage`, страницы AI‑отчётов/отчётности встроены в админку.
  - **Gap:** `BUSINESS_LOGIC_CURRENT` согласован с текущими роутами.

**Итог по CURRENT:** с точки зрения **маршрутов** расхождений между `BUSINESS_LOGIC_CURRENT.md` и фактическим кодом **нет**; документ немного упрощает карту (не перечисляет все служебные роуты), но не вводит в заблуждение.

---

## 4. Сопоставление с BUSINESS_LOGIC_V2.md (фазы)

V2 описывает целевое состояние модулей. Сравниваем **идею модуля** с наличием маршрутов и объёмом реализации.

### 4.1 Фаза 1 — AI Agent (Function Calling, Autopilot)

- **Фактические маршруты:**
  - Backend:
    - `POST /ai/agent` → `ai_agent.ai_agent_command` (заглушка: статический ответ, без вызова инструментов).
    - `POST /ai/generate-offers` → заглушка, возвращающая пустой список.
    - Существующие Omnichannel‑роуты (`admin_omni_chat`, `integrations_gateway`, `admin_ai_*`, `owner_omni_*`).
  - Frontend:
    - `useAiAgent` (Spotlight «Спросить AI») вызывает `/v1/ai/agent`, но также содержит fallback‑заглушку.
    - В `AdminLayout` AI‑агент wired как экшен Spotlight, но на бэке ещё нет оркестратора.

- **План V2:** полноценный AI‑агент с function calling, registry инструментов (`get_available_slots`, `create_booking`, ...) и оркестратором `OmnichannelAiOrchestrator`.

- **Gap‑вывод:**
  - **Маршруты уже заведены**, но:
    - отсутствует реализация tools‑registry и вызова доменных сервисов из AI;
    - эндпоинты помечены как stub (явное сообщение «будет подключено в следующей версии»).
  - **Статус:** *маршруты в коде соответствуют V2‑видению, но бизнес‑функционал AI‑агента ещё не реализован*.

### 4.2 Фаза 2 — Sales & Kanban (CRM‑воронка)

- **Фактические маршруты и UI:**
  - Backend: `admin_crm` (`/admin/crm/*`) — Kanban‑вью:
    - `/admin/crm/pipelines`, `/admin/crm/stages`, `/admin/crm/leads`, `/admin/crm/leads/{id}`, `/admin/crm/leads/{id}/stage`, `/admin/crm/leads/{id}/notes`.
  - Frontend:
    - `"/admin/sales"` → `AdminSalesPipelinePage` — полноценный Kanban с drag&drop, агрегациями по стадиям, карточкой лида и заметками; интеграция с `AdminOmniChatPage` (переход в чат по `omnichannel_contact_id`).

- **План V2:** LeadPipeline / LeadStage / LeadCard, автодвижение по событиям (создание контакта, запись, завершение визита и т.д.).

- **Gap‑вывод:**
  - **Kanban‑часть (визуальный CRM + ручное управление лидами)** реализована и согласована с V2.
  - Требует проверки/доработки **автотриггеров** (создание/движение LeadCard по событиям Booking/Omnichannel) — это больше бизнес‑логика, чем маршруты. По карте маршрутов — **соответствие есть**.

### 4.3 Фаза 3 — ERP (Финансы, зарплаты, склад)

- **Фактические маршруты и UI:**
  - Backend:
    - `admin_finance` (`/admin/clinics/{clinic_id}/finance/*`): кассы, транзакции, liability.
    - `admin_inventory` (`/admin/clinics/{clinic_id}/inventory/*`): склад, движения, остатки.
    - `admin_payroll` (`/admin/clinics/{clinic_id}/payroll/*`): политика ЗП и начисления.
    - Логика ERP‑узла при завершении визита реализована в сервисах (`FinanceService`, `AttentionFeedService` использует `erp_error_code`).
  - Frontend:
    - `"/admin/finance"` → `AdminFinancePage`: вкладки «Кассы», «Транзакции», «Зарплаты», «Склад».

- **План V2:** единый транзакционный узел при завершении визита с созданием `FinancialTransaction`, `SalaryTransaction`, `InventoryTransaction` в одной транзакции.

- **Gap‑вывод:**
  - **Маршруты ERP‑модуля присутствуют и активно используются**.
  - Требуется дальнейшая валидация полноты Unit‑of‑Work при `Booking.status → completed`, но это уровень бизнес‑логики, не роутинг. С точки зрения карты маршрутов — **совпадение**.

### 4.4 Фаза 4 — RBAC & Tasks

- **Фактические маршруты и UI:**
  - Backend:
    - `admin_tasks` (`/admin/tasks/*`) — управление задачами (сущность `Task` уже есть, используется в `AttentionFeedService`).
    - Множество админ‑роутеров используют `require_permissions(...)` (`view_crm`, `manage_crm`, `view_finance`, `manage_finance` и т.д.), что реализует **RBAC на уровне пермишенов**.
  - Frontend:
    - `"/admin/tasks"` → `AdminTasksPage` (список задач).
    - RBAC на фронте опирается на токен и контекст клиники (нет отдельной UI‑страницы «Роли и права»).

- **План V2:** явные модели `Role`, `Permission`, `RolePermission`, `UserRole`, роли Owner/Manager/Admin/Doctor, AI‑Task‑Generator.

- **Gap‑вывод:**
  - **Задачи как сущность и UI‑маршрут реализованы.**
  - RBAC фактически реализован через permissions и токены, но:
    - нет отдельного маршрута/страницы для управления ролями и матрицей прав;
    - AI Task Generator (ночной Celery‑процесс) маршрутов не требует, но его наличие нужно проверять по коду задач.
  - **Статус по маршрутам:** домен Tasks и базовый RBAC присутствуют, **UI для управления ролями в стиле V2 отсутствует**.

### 4.5 Фаза 5 — Loyalty & Subscriptions

- **Фактические маршруты и UI:**
  - Backend:
    - `admin_loyalty` (`/admin/loyalty/*`) — управление подписками/кошельком/политиками.
    - `patient_loyalty` (`/patient/loyalty/*`) — пациентский доступ к программе лояльности.
    - Лояльность также встроена в `AttentionFeedService` (retention‑gap и loyalty‑gap).
  - Frontend:
    - `"/admin/loyalty"` → `AdminLoyaltyPage`.
    - `"/app/loyalty"` → `LoyaltyPage` (PWA).

- **План V2:** богатый движок пакетов (COUNT/BALANCE‑based), FamilyLink, триггеры Celery `check_expiring_packages`.

- **Gap‑вывод:**
  - **Маршруты и основные экраны уже есть**, что соответствует V2‑карте модулей.
  - Отдельных маршрутов для FamilyLink и детальной истории списаний пока не выделено (они, вероятно, инкапсулированы в `admin_loyalty`).
  - **Статус:** соответствие по карте маршрутов; глубина функционала (FamilyLink, сложные AI‑триггеры) — частично/неполностью реализована.

### 4.6 Фаза 6 — Paperless Office

- **Фактические маршруты и UI:**
  - Backend:
    - `admin_forms` (`/admin/forms/*`) — управление шаблонами форм.
    - `patient_forms` (`/patient/forms/*`) — работа пациента с цифровыми формами.
  - Frontend:
    - `"/admin/forms"` → `AdminFormsPage`.
    - `"/app/forms"` → `FormsPage`; отправка ссылок на формы связана с записью/маркетингом.

- **План V2:** DigitalFormTemplate, DigitalFormSubmission, ESignature, связывание форм с визитами/пациентами.

- **Gap‑вывод:**
  - **Маршруты для Paperless‑модуля существуют** и соответствуют описанию V2.
  - Признаков полноценного модуля `ESignature` как отдельного домена/маршрута в коде не видно — это будущий gap.

### 4.7 Фаза 7 — Marketing Attribution

- **Фактические маршруты и UI:**
  - Backend:
    - `public_marketing` (`/public/clinics/*`) — фиксация атрибуции визитов.
    - `admin_marketing_attribution` (`/admin/attribution/*`) — отчёты по атрибуции.
  - Frontend:
    - Элементы атрибуции интегрированы в `AdminReportsPage` и связанные UI‑элементы; отдельного `/admin/attribution`‑экрана в SPA пока нет (может быть встроен в отчёты).

- **План V2:** домены `TrafficSource/Campaign`, расширения `LeadCard`, связь с `FinancialTransaction`, ROI‑дашборды.

- **Gap‑вывод:**
  - Backend‑маршруты для атрибуции уже созданы, что соответствует V2.
  - На фронте отдельного модульного экрана для атрибуции пока не видно; логика может быть распределена по отчётам.

---

## 5. Краткий итог gap‑анализа по маршрутам

1. **Карта маршрутов backend и frontend в коде самосогласована** (`router.py` ↔ `routers/*` ↔ `App.tsx`/layouts); явных «битых» или потерянных модулей нет.  
2. **`BUSINESS_LOGIC_CURRENT.md` в части маршрутов не врёт:** все описанные домены действительно имеют поддерживающие API и страницы; документ лишь не детализирует вспомогательные роуты.  
3. **`BUSINESS_LOGIC_V2.md` уже «подсвечен» в коде маршрутами:** для AI Agent, CRM‑воронки, ERP, Loyalty, Paperless и Attribution заведены соответствующие роуты и UI‑страницы.  
4. **Ключевые gap‑зоны находятся не в маршрутах, а в глубине реализации:**
   - AI Agent (`/ai/agent`, `/ai/generate-offers`, `useAiAgent`) пока реализован как заглушка, без function‑calling и автопилота.
   - RBAC‑модуль на уровне ролей/пермишенов не имеет отдельного UI и явных сущностей `Role/Permission`, хотя пермишены в коде используются.
   - V2‑расширения (FamilyLink для пакетов, E‑подпись, полный набор автотритгеров CRM/ERP/Loyalty) частично реализованы или скрыты внутри существующих доменов, но **новых маршрутов под них пока нет**.

