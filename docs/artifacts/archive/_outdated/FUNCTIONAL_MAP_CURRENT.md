## 🧭 FUNCTIONAL_MAP_CURRENT — Dental Booking (функциональная карта по коду)

> Цель: дать ИИ и разработчикам **точное, модульное представление о функциональных возможностях системы**,  
> не опираясь на исторические планы, а только на:
> - код backend (`src/**`),
> - код frontend (`frontend/src/**`),
> - актуальные техпаспорта (`TECH_PASSPORT_*`),
> - актуальную бизнес‑логику (`BUSINESS_LOGIC_CURRENT.md`).

Этот документ отвечает на вопросы:

- **Что умеет система по факту** в каждом функциональном модуле.
- **Какие страницы/модули/модальные окна** есть во frontend и с какими данными они работают.
- **Какие backend‑эндпоинты** стоят за каждой функцией.
- **Как устроена «машина» логики** (главные потоки: запись, предоплата, уведомления, omnichannel, AI).
- **Где и как интегрирован AI**.

Для детальной навигации по коду всегда можно перейти к:

- `TECH_PASSPORT_BACKEND.md`
- `TECH_PASSPORT_FRONTEND.md`
- `TECH_PASSPORT_PROJECT.md`
- `BUSINESS_LOGIC_CURRENT.md`

---

## 1. Конвенции и сущности верхнего уровня

- **Роли**:
  - `patient` — пациент (клиент клиники).
  - `admin` — администратор клиники.
  - owner‑уровень — админ с доступом к owner‑роутерам (логически «владелец»/старший админ клиники).

- **Основные доменные сущности** (подробно в `src/domain/entities/*.py`):
  - Организация: `Clinic`, `ClinicPlan`, `ClinicAiSettings`, `ClinicIntegrationSettings`, `ClinicPaymentGateway`, `AgreementSettings`.
  - Люди и услуги: `Doctor`, `DoctorWorkingHours`, `DoctorAbsence`, `Service`, `ServiceDoctor`, `Patient`, `PatientCommunicationPreferences`.
  - Запись и очередь: `Booking`, `QueuePolicy`, `WaitlistEntry`, `WaitlistNotification`.
  - Платежи и скидки: `Payment`, `PrepaymentPolicy`, `PrepaymentTransaction`, `Discount`.
  - Коммуникации и AI: `Notification`, `NotificationChannelConfig`, `OmnichannelChat`, `OmnichannelMessage`, `OmnichannelContact`, `OmnichannelChannel`, `OmnichannelAuditLog`, `OmnichannelAiSettings`, `OmnichannelIntegrationConfig`, `Conversation`, `ConversationAiAnalysis`.
  - Маркетинг и recall: `PromoPost`, `Story`, `ClientReference`, `CsvImportJob`, `RecallCampaign`, `RecallSegment`, `RecallTemplate`, `RecallAutomation`, `RecallLog`.
  - Администрирование: `AdminUser`, `AttentionFeed` (и др. вспомогательные).

- **Глобальные инварианты**:
  - Один слот (`doctor + дата + время`) — максимум одна запись (`Booking`) → уникальный индекс в БД.
  - Пациент видит только свои сущности; админ ограничен `clinic_id`.
  - Все внешние интеграции (YooKassa, Telegram, SMS, AI и т.п.) конфигурируются через `.env` + сущности `Clinic*`/`*Settings` и **не** хардкодятся в код.

---

## 2. Аутентификация и идентичность

### 2.1. Пациент: SMS‑код и OAuth

**Frontend**:

- Страницы:
  - `/login` → `LoginPage`:
    - Формы:
      - ввод номера телефона → запрос SMS‑кода;
      - ввод кода и согласий → подтверждение логина;
      - опциональные кнопки входа через VK/Yandex.
    - Данные:
      - `phone`, `code`, флаги согласий (прочитано/согласен), ссылка на текст соглашений (`AgreementSettings`).
  - `/oauth/result` → `OAuthResultPage`:
    - Обрабатывает результат редиректа от VK/Yandex (query/fragment‑параметры).
    - Вызывает backend‑эндпоинт OAuth и сохраняет patient‑токен.

- Логика состояния:
  - `PatientAuthContext`:
    - хранит `accessToken` и `patientId` в `localStorage`;
    - предоставляет `login(token, patientId)` и `logout()`.
  - Хуки `useAuth`:
    - инкапсулируют вызов `/v1/auth/send-code`, `/v1/auth/verify-code` и OAuth‑эндпоинтов.

**Backend**:

- Роутер: `src/api/v1/routers/auth.py`.
- Основные эндпоинты:
  - `POST /api/v1/auth/send-code`:
    - Вход: телефон.
    - Поведение:
      - нормализует номер;
      - проверяет rate‑limit по IP/телефону;
      - генерирует 6‑значный код, сохраняет в Redis;
      - отправляет SMS через `SmsClient` (если `smsc_enabled=True`) либо логирует.
  - `POST /api/v1/auth/verify-code`:
    - Вход: телефон, код, флаги согласий.
    - Поведение:
      - сверяет код с Redis;
      - создаёт/обновляет `Patient`;
      - записывает согласия (AgreementSettings/поля `consent_*`);
      - создаёт JWT (`role="patient"`) и возвращает `access_token` и `patient_id`.
  - OAuth:
    - `GET/POST /api/v1/auth/oauth/vk/*`, `/oauth/yandex/*`:
      - реализуют обмен кода на токен у внешнего провайдера;
      - находят/создают `Patient` по внешнему ID;
      - выдают JWT пациента.

- Логика безопасности:
  - Rate limiting — `RateLimiter` + Redis; лимиты в `Settings` (`rate_auth_send_code_*`).
  - JWT:
    - создаётся через `core/security.py::create_access_token`;
    - хранит `sub` = `patient_id`, тип/роль и TTL (`jwt_access_token_expire_minutes_patient`).
  - Доступ к текущему пациенту:
    - `get_current_patient` в `dependencies.py`:
      - читает `Authorization: Bearer`;
      - парсит токен, проверяет роль;
      - загружает `Patient` из БД.

### 2.2. Админ: email/пароль

**Frontend**:

- Страницы:
  - `/admin/login` → `AdminLoginPage`:
    - Поля: `email`, `password`.
    - Поведение:
      - вызывает `/v1/admin/auth/login`;
      - при успехе сохраняет админ‑токен (`dental_booking_admin_token`) в `localStorage`;
      - редиректит на `/admin`.
  - `/admin/*`:
    - обёрнуто в `AdminAuthGuard`:
      - проверяет наличие валидного админ‑токена;
      - при 401 (или отсутствии токена) редиректит на `/admin/login`.

- Логика состояния:
  - `api/client.ts`:
    - `getAdminToken`, `setAdminToken`, `clearAdminToken`;
    - автоматически подставляет токен для `/v1/admin*` и `/v1/owner*`;
    - на 401 очищает токен и делает redirect `/admin/login`.

**Backend**:

- Роутер: `src/api/v1/routers/admin_auth.py`.
- Эндпоинт:
  - `POST /api/v1/admin/auth/login`:
    - Вход: `email`, `password`.
    - Поведение:
      - проверка admin user по email;
      - проверка пароля через `passlib.pbkdf2_sha256`;
      - проверка rate‑limit по IP/email (`rate_admin_login_*`);
      - выдача JWT с `type="admin"` и `clinic_id`.
  - Доступ к текущему админу:
    - `get_current_admin`/`get_current_admin_optional` в `dependencies.py`:
      - парсят токен, проверяют тип `admin`, подгружают `AdminUser`.

---

## 3. Клиника, бизнес‑лексикон и глобальные настройки

### 3.1. AdminClinicContext и выбор клиники

**Frontend**:

- `AdminClinicProvider`:
  - Использует `useClinics()` (React Query) для получения списка клиник.
  - Автоматически выбирает первую клинику, если `currentClinicId` не задан.
  - Предоставляет:
    - `clinics: Clinic[]`;
    - `currentClinicId: string | null`;
    - `setCurrentClinicId(id)` — смена активной клиники;
    - `businessLexicon: BusinessLexicon | null`.

- `useBusinessLexicon()`:
  - Возвращает настроенный `business_lexicon` текущей клиники;
  - Если не задан, подставляет дефолтные подписи для стоматологии (Пациент, Пациенты, Врачи, и т.д.).

**Backend**:

- Модели:
  - `Clinic`, `ClinicIntegrationSettings`, `ClinicPlan`, `ClinicAiSettings`, `ClinicPaymentGateway`, `AgreementSettings`.
- API (в т.ч. админские):
  - `src/api/v1/routers/clinics.py` и связанные admin‑роутеры (конкретные пути см. в коде):
    - получение/редактирование профиля клиники;
    - управление бизнес‑лексиконом;
    - управление планами/тарифами (поля есть, но тарификация как отдельный продукт логически не активирована).
  - `admin_ai_settings`, `admin_payment_gateway`, `admin_integrations`, `admin_agreements`, `admin_notification_policy`, `admin_styling`, `admin_channels`:
    - работают поверх соответствующих сущностей `Clinic*` и `Notification*`.

### 3.2. Темы, стили, соглашения

**Frontend**:

- `AdminStylingPage`, `AdminStickersPage`, `AdminSettingsPage`:
  - Управление внешним видом приложения (цветовые темы, логотипы, стикеры и т.п.).
  - Используют типы из `api/types.ts` и соответствующие хуки.
- `AdminAgreementsPage`:
  - Управление текстами пользовательских соглашений (`AgreementSettings`).
  - Влияет на содержимое, показываемое в форме логина пациента и при регистрации/согласии на обработку ПДн.

**Backend**:

- Модель `AgreementSettings`:
  - Содержит тексты и флаги обязательных соглашений.
- `GET /api/v1/auth/agreement`:
  - Отдаёт настройки для фронта (LoginPage).

---

## 4. Врачи, услуги и расписание

### 4.1. Управление врачами и услугами (админка)

**Frontend**:

- Страницы:
  - `AdminDoctorsPage`:
    - Список врачей, поля: ФИО, специальность, фото/аватар, активность, расписание, и др. (подробнее в `Doctor`).
    - Действия:
      - создание/редактирование врача (через модальные формы);
      - включение/выключение врача;
      - переход к расписанию конкретного врача.
  - `AdminServicesPage`:
    - Каталог услуг (название, категория, цена, длительность, активность).
    - Привязка услуг к врачам (обычно через отдельный интерфейс или секцию в модальном окне).

- UI‑элементы:
  - формы создания/редактирования врача/услуги реализованы как модальные окна Mantine (React компоненты с формами и валидацией по типам из `api/types.ts`).

**Backend**:

- Модели:
  - `Doctor`, `DoctorWorkingHours`, `DoctorAbsence`, `Service`, `ServiceDoctor`.
- API:
  - Публичные:
    - `/api/v1/doctors/*` — список врачей, детали по врачу, публичное расписание.
    - `/api/v1/services/*` и `/api/v1/public/services/*` — публичный каталог услуг.
  - Админские:
    - `/api/v1/admin/doctors/*`, `/api/v1/admin/services/*` — CRUD врачей и услуг.

### 4.2. Расписание и сетка (пациент и админ)

**Frontend**:

- Пациент:
  - `BookingWizardPage`:
    - шаги:
      1. выбор клиники (если несколько);
      2. выбор услуги;
      3. выбор врача или «любой врач»;
      4. выбор слота в расписании (по дате/времени).
    - использует хуки:
      - `useDoctorSchedule` — `/v1/doctors/{doctor_id}/schedule?date=...`;
      - `useServices` и `useClinics`.
  - `HistoryPage`:
    - список прошлых и будущих записей пациента.

- Админ:
  - `SchedulePage`:
    - отображает сетку расписания по клинике/дню (все врачи за день).
    - поддерживает drag‑and‑drop (`@dnd-kit`) для перекидывания записей между слотами/врачами.
  - `AdminDoctorSchedulePage`:
    - отдельный вид расписания по одному врачу.
  - Хуки:
    - `useAdminSchedule`, `useDoctorScheduleAdmin`, `useDoctorScheduleConfig`.

**Backend**:

- API:
  - Публичные:
    - `GET /api/v1/doctors/{doctor_id}/schedule` — публичное расписание на день/диапазон.
  - Админские:
    - `GET /api/v1/admin/clinics/{clinic_id}/schedule` — сводная сетка по клинике.
    - `GET /api/v1/admin/doctors/{doctor_id}/schedule` — расписание по врачу.
    - `PUT/POST`‑эндпоинты для изменения слотов, работы с `DoctorWorkingHours`, `DoctorAbsence` и `Booking`.

---

## 5. Записи (Booking), история и отмены

### 5.1. Пациентские записи

**Frontend**:

- `BookingWizardPage`:
  - Формы:
    - выбор услуги, врача, даты/времени;
    - блок предоплаты (если включена).
  - Взаимодействие с API:
    - создание записи → `POST /api/v1/patient/bookings` (или эквивалентный эндпоинт в `bookings.py`).
    - после успешного создания и, при необходимости, успешной оплаты — редирект на `/booking/success`.

- `HistoryPage`:
  - показывает список записей пациента (получение через `/v1/patient/bookings`);
  - предоставляет действия:
    - отмена будущей записи;
    - просмотр деталей (услуга, врач, дата/время, статус, наличие предоплаты).

**Backend**:

- Роутер: `src/api/v1/routers/bookings.py`.
- Основные эндпоинты (пациент):
  - `GET /api/v1/patient/bookings` — список записей пациента.
  - `POST /api/v1/patient/bookings` — создание записи:
    - принимает DTO с `clinic_id`, `doctor_id`, `service_id`, `appointment_date`, `appointment_time`, и др.;
    - проверяет наличие свободного слота;
    - учитывает политику предоплаты (может потребовать платёж).
  - `DELETE /api/v1/patient/bookings/{booking_id}` — отмена записи:
    - проверяет, что `booking.patient_id` = текущий пациент;
    - обновляет статус;
    - триггерит уведомления и возможный возврат предоплаты (через PaymentService).

### 5.2. Админские записи

**Frontend**:

- `AdminBookingsPage`:
  - Таблица/список записей с фильтрацией:
    - по дате/периоду;
    - по статусу;
    - по врачу/пациенту (телефон, имя).
  - Действия:
    - создание новой записи (обычно модальное окно);
    - изменение статуса: подтверждение, завершение, отмена, no‑show;
    - перенос записи на другой слот/врача.

**Backend**:

- Роутер `bookings.py` содержит также админские эндпоинты:
  - `GET /api/v1/admin/bookings` — поиск/фильтрация записей.
  - `POST /api/v1/admin/bookings` — создание записи от имени пациента.
  - `PUT /api/v1/admin/bookings/{id}/cancel|complete|no-show|reschedule` — управление статусами и переносами.

---

## 6. Предоплата и платёжные шлюзы

### 6.1. Настройки и политики предоплаты

**Frontend**:

- `AdminPrepaymentPage`:
  - UI для управления:
    - глобальным флагом «предоплата включена» для клиники;
    - политиками предоплаты:
      - по врачу (`doctor`);
      - по услуге (`service`);
      - по комбинации (`doctor_service`);
    - типом предоплаты (none/partial/full) и суммой/процентом.
- `AdminPaymentGatewayPage`:
  - UI для ввода учётных данных YooKassa:
    - `shop_id`, `secret_key`, режим test/prod и т.п. (точные поля см. `ClinicPaymentGateway`).

**Backend**:

- Модели:
  - `PrepaymentPolicy`, `PrepaymentTransaction`, `ClinicPaymentGateway`.
- API:
  - `admin_prepayment.py`:
    - CRUD политик предоплаты и чтение/изменение флагов.
  - `admin_payment_gateway.py`:
    - CRUD настроек платёжного шлюза для клиники.

### 6.2. Поток создания платежа и webhook

**Backend**:

- Роутер: `src/api/v1/routers/payments.py`.
- Клиент: `src/infrastructure/external_apis/yookassa_client.py`.
- Сервис: `PaymentService`.
- Эндпоинты:
  - `POST /api/v1/payments`:
    - Вход: `booking_id`, `amount`, валюта и др.
    - Поведение:
      - создаёт платёж в YooKassa;
      - пишет запись в таблицу `Payment`;
      - возвращает `confirmation_url` для фронта.
  - `POST /api/v1/payments/webhook`:
    - Принимает webhook от YooKassa (по статусу платежа);
    - Обновляет `Payment.status` и, при необходимости, статус `Booking`.

**Frontend**:

- `BookingWizardPage`:
  - при необходимости предоплаты:
    - вызывает `POST /v1/payments` через соответствующий хук;
    - редиректит пациента на `confirmation_url`;
    - после успешной оплаты и редиректа — показывает `BookingSuccessPage`.

---

## 7. Очередь, лист ожидания и политики

**Backend**:

- Модели:
  - `QueuePolicy` — параметры очередности, приоритизация.
  - `WaitlistEntry`, `WaitlistNotification` — лист ожидания и уведомления по нему.
- Роутеры:
  - `admin_waitlist.py`:
    - эндпоинты для просмотра/управления waitlist;
  - часть логики планирования/переноса записей встроена в `BookingService` и связанные сервисы.

**Frontend**:

- `AdminWaitlistPage`:
  - список клиентов в листе ожидания (имя/телефон/желаемое время/услуга);
  - действия:
    - переместить в реальный слот (создать запись);
    - удалить/обновить запись waitlist.
- Хуки:
  - `useAdminWaitlist` — обёртка над `/v1/admin/waitlist/*` эндпоинтами.

---

## 8. Уведомления и напоминания

### 8.1. Каналы и настройки

**Backend**:

- Модели:
  - `Notification`, `NotificationChannelConfig`, `PatientCommunicationPreferences`, `WaitlistNotification`.
- Сервисы:
  - `NotificationService` — создание и отправка уведомлений;
  - `MessagingService`, `OmnichannelOutboundDispatcher` — интеграция с каналами.
- Celery‑таски:
  - `send_booking_created_task`, `send_booking_cancelled_task`,
    `send_reminder_24h_task`, `send_reminder_2h_task`, `run_reminders_task`.

**Frontend**:

- `AdminNotificationPolicyPage`:
  - UI‑формы для настройки каналов и интервалов уведомлений по клинике.
- `PatientNotificationSettingsPage` (по роутеру `patient_notification_settings.py`):
  - настройки пациента: предпочтительные каналы (SMS/Telegram/Email) и opt‑in/out.

### 8.2. Потоки уведомлений

- **Создание записи**:
  - Backend:
    - создаёт `Notification`;
    - триггерит Celery‑таск `send_booking_created`.
  - Каналы:
    - Telegram (бот);
    - SMS;
    - Email — согласно настройкам.

- **Напоминания**:
  - Периодический таск `run_reminders`:
    - находит записи с подходящими датами и статусом confirmed;
    - ставит `send_reminder_24h` / `send_reminder_2h`.

- **Отмена/изменение записи**:
  - Уведомления пациенту и, при необходимости, администратору через соответствующие таски.

---

## 9. Omnichannel‑чат и интеграция AI

### 9.1. Входящие каналы и интеграционный шлюз

**Backend**:

- Роутер: `src/api/v1/routers/integrations_gateway.py`.
- Эндпоинты:
  - `/api/integrations/webhooks/telegram`
  - `/api/integrations/webhooks/whatsapp`
  - `/api/integrations/webhooks/vk`
  - `/api/integrations/webhooks/instagram`
  - `/api/integrations/webhooks/email`
  - `/api/webchat/messages` — входящие сообщения web‑чата.
  - `/api/webchat/poll` — long‑poll для отдачи сообщений обратно в web‑чат.
- Логика:
  - проверка валидности и сигнатур (в т.ч. `X-Telegram-Bot-Api-Secret-Token` для Telegram при наличии секрета);
  - нормализация входящих payload‑ов до унифицированного формата (через `IntegrationGatewayService`);
  - создание/обновление `OmnichannelChat`, `OmnichannelMessage`, `OmnichannelContact`.

### 9.2. Пациентский чат

**Frontend**:

- `ChatPage` (в PWA `/app/chat`):
  - показывает:
    - историю сообщений пациента;
    - статусы (прочитано/не прочитано);
  - позволяет:
    - отправлять новые сообщения;
    - удалять свои сообщения;
    - отмечать сообщения как прочитанные.
- Хуки:
  - `usePatientConversation`, `usePatientChatMessages`, `useSendPatientMessage`, `useDeletePatientMessage`, `usePatientMarkRead`.

**Backend**:

- Роутер: `src/api/v1/routers/patient_chat.py`.
- Эндпоинты:
  - получение текущего диалога и списка сообщений;
  - отправка/удаление сообщения;
  - отметка прочитанным.

### 9.3. Рабочее место админа и AI

**Frontend**:

- Страницы:
  - `AdminOmniChatPage` — основное окно омниканального чата:
    - список диалогов/контактов;
    - лента сообщений;
    - поля для ответа, кнопки шаблонов/стикеров/эмодзи;
    - статус/канал каждого сообщения.
  - `AdminOmniChannelsPage` — управление каналами (подключение Telegram/WhatsApp/VK/Instagram/email/webchat).
  - `AdminOmniAiSettingsPage` — настройки AI асcистента (модель, режимы, подсказки и т.п.).
  - `AdminAiReportsPage` — AI‑отчёты по перепискам.
  - `AdminAiStatusPage` — состояние AI‑интеграции (health, лимиты).
  - `OwnerOmniChannelsPage`, `OwnerOmniAiSettingsPage`, `OwnerOmniAuditPage` — owner‑уровень управления и аудита.

**Backend**:

- Модели:
  - `OmnichannelChat`, `OmnichannelMessage`, `OmnichannelContact`, `OmnichannelChannel`, `OmnichannelAuditLog`,
    `OmnichannelAiSettings`, `OmnichannelIntegrationConfig`, `Conversation`, `ConversationAiAnalysis`.
- Сервисы:
  - `OmnichannelChatService` — управление чатами и сообщениями.
  - `OmnichannelOutboundDispatcher` — отправка сообщений в конкретные внешние каналы.
  - `OmnichannelAiOrchestrator` — оркестрация AI‑ответов и аналитики.
  - `ChatAiService` — низкоуровневый клиент AI‑провайдера.
  - `ConversationAnalysisService` — аналитика диалогов, подготовка отчётов.
- Внешний AI:
  - Клиент: `infrastructure/external_apis/ai_client.py`.
  - Настройки:
    - `Settings.ai_provider_base_url`;
    - `Settings.ai_provider_api_key`;
    - `Settings.ai_provider_model` (по умолчанию `deepseek-chat`, может быть изменён).
- Потоки AI:
  - При запросе админа/owner к AI‑функции (в UI чат/отчёты):
    - бекенд формирует промпт на основе истории `Conversation`/`OmnichannelMessage`;
    - шлёт запрос к AI‑провайдеру через `AiClient`;
    - сохраняет ответы и аналитические данные в `ConversationAiAnalysis` и связанные сущности;
    - отдаёт результат на фронт (чат, отчёт, attention‑лента).

---

## 10. Маркетинг, recall и клиентские истории

**Frontend**:

- Пациент:
  - `FeedPage` (`/app/feed`):
    - отображает маркетинговую ленту: посты, акции, сторис;
    - использует эндпоинты `public_marketing`.
  - `HomePage`:
    - может включать виджеты с акциями и ссылками на запись.

- Админ:
  - `AdminMarketingPage`:
    - управление `PromoPost` и `Story` (карточки, тексты, медиа, порядок показа).
  - `AdminRecallPage`:
    - управление:
      - сегментами (`RecallSegment`);
      - кампаниями (`RecallCampaign`);
      - шаблонами (`RecallTemplate`);
      - автоматизациями (`RecallAutomation`);
    - просмотр логов (`RecallLog`).
  - `AdminClientReferencePage`:
    - управление `ClientReference` (кейсы, отзывы, истории).

**Backend**:

- Роутеры:
  - `admin_marketing.py`, `public_marketing.py`, `admin_recall.py`, `admin_client_reference.py`, `csv_sync.py`.
- Функциональность:
  - CRUD маркетинговых сущностей и их связей с клиникой;
  - запуск/управление recall‑кампаниями (частично завязано на уведомления/omnichannel);
  - CSV‑импорт/экспорт (`CsvImportJob`) для интеграций с внешними системами (в т.ч. 1С через файлы).

---

## 11. Отчёты, аналитика и attention‑лента

**Frontend**:

- `AdminReportsPage`:
  - классические отчёты по:
    - записям (кол‑во, статусы, no‑show);
    - выручке и платежам;
    - эффективности кампаний/маркетинга.
- `AdminAiReportsPage`:
  - AI‑отчёты:
    - на основе `ConversationAiAnalysis`;
    - агрегированные метрики по диалогам и коммуникациям.
- `AdminAttentionFeedPage`:
  - attention‑лента:
    - ключевые события, требующие внимания (критичные статусы, ошибки интеграций, важные сигналы AI и т.п.).

**Backend**:

- Сервисы:
  - `ReportService`, `PricingService`, `ConversationAnalysisService`.
- Роутеры:
  - `admin_reports.py`, `admin_ai_reports.py`, `admin_ai_status.py`, `admin_attention_feed.py`.

---

## 12. Администрирование, безопасность и ограничители

**Frontend**:

- `AdminAdministratorsPage`:
  - управление `AdminUser`:
    - список администраторов;
    - создание/редактирование (email, имя, привязка к клинике и т.д.).

**Backend**:

- `AdminUser`:
  - хранит email, пароль (pbkdf2 sha256), ФИО и др.

- Rate limiting:
  - Реализован централизованно в `infrastructure/rate_limiter.py`.
  - Применяется минимум к:
    - `/auth/send-code` (по IP/телефону);
    - `/admin/auth/login` (по IP/email);
    - AI‑эндпоинтам (`rate_ai_*`).

- Логирование и метрики:
  - `core/logging.py` — JSON‑логирование, уровень по `Settings.log_level`.
  - `core/metrics.py` + `/metrics` — Prometheus‑метрики.

- Тесты безопасности:
  - `tests/security/test_security_kassa.py` — безопасность платёжного флоу;
  - `tests/security/test_security_chats.py` — безопасность чатов;
  - `tests/security/test_security_pd.py` — защита персональных данных.

---

## 13. Что **есть** и чего **нет** (по факту кода)

**Есть в коде (реализовано):**

- Полный цикл записи пациента:
  - от выбора услуги/врача/слота до подтверждения и напоминаний;
  - предоплата через YooKassa (опционально, с политиками и webhook‑обновлением);
  - отмены и история записей.
- Админское управление:
  - врачами, услугами, расписанием (в т.ч. drag‑and‑drop сетка);
  - листом ожидания и политиками очереди;
  - уведомлениями и их каналами;
  - маркетинговой лентой, recall‑кампаниями и клиентскими референсами;
  - omnichannel‑чатом и AI‑настройками;
  - администраторами и настройками клиники/интеграций/предоплаты/стилей.
- Интеграции:
  - YooKassa, SMS‑провайдер, SMTP, Telegram/WhatsApp/VK/Instagram/email/webchat, внешний AI‑провайдер.
- Тесты:
  - API‑, security‑, доменные и сервисные тесты.

**Нет (по коду прямо сейчас):**

- Нет реализованной многоарендности на уровне отдельных организаций с разными доменами/префиксами как полноценного SaaS‑кастомера — но есть поле `clinic_id` и модуль `ClinicPlan`, позволяющие это развивать.
- Нет полноценной внутренней ролевой модели в админке (типы админов «кассир/врач/маркетолог» и т.п.) — существует только сущность `AdminUser`.
- Нет интеграций с 1С/qMS/B24 через онлайн‑API: есть **CSV‑импорт/экспорт** и подготовленные сущности/архитектура, но прямых API‑колбеков/коннекторов в коде не видно.
- Нет мобильных нативных приложений — только PWA (React + Vite + vite‑plugin‑pwa).

---

## 14. Как использовать этот документ для RAG

- Для ИИ:
  - использовать этот файл как **функциональный индекс**:
    - искать нужный модуль/страницу по разделам 2–12;
    - далее идти в соответствующие *TECH_PASSPORT* и в код (`src/**`, `frontend/src/**`) по указанным именам файлов и роутеров.
  - при проектировании новых фич:
    - сначала проверить, что похожий модуль или сущность уже **есть**;
    - использовать существующие паттерны (сервисы, DTO, хуки).

- Для людей:
  - как «каталог возможностей» для владельца продукта;
  - как чек‑лист «что уже сделано» перед постановкой новых задач.

Этот документ описывает **фактически реализованные** функциональные возможности Dental Booking на момент ревизии и должен обновляться при появлении значимых новых модулей, сущностей или интеграций.

