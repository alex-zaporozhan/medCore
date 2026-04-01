## 🧱 ARCH: AI‑омниканальный ассистент и контакт‑центр

> Цель: описать архитектуру модуля AI‑омниканального ассистента на основе `BIZ_AI_ASSISTANT_OMNICHANNEL.md`: сущности, сервисы, интеграции, потоки данных и контракты для @DEV.

---

### 1. Границы модуля и high‑level архитектура

- **Scope модуля:**
  - приём сообщений из внешних каналов (мессенджеры, соцсети, сайт, email);
  - нормализация и маршрутизация в **единый Chat** на стороне платформы;
  - обработка через AI‑конвейер (автоответ / подсказки / эскалация к оператору);
  - работа живых админов в едином интерфейсе;
  - полное журналирование диалогов и действий (включая работу с ключами).

- **Встраивание в существующую систему:**
  - модуль живёт рядом с уже существующими доменами (`Bookings`, `Patients`, `Doctors`, `Services`, `Payments`, `Notifications`);
  - использует существующие сервисы:
    - `NotificationService` (для триггеров и уведомлений админов/клиентов);
    - сервисы расписания и услуг (для получения фактов: цены, слоты, специалисты);
    - сервисы аутентификации и ролей (Owner / Admin / System).

- **High‑level схема (логическая):**
  - **Integration Layer** ← внешние каналы (Telegram, WhatsApp, VK, Instagram*, Web‑чат, Email)
  - → **Routing & Identity** (Contact/Channel/Chat matching)
  - → **Conversation Service** (создание/обновление Chat/Message)
  - → **AI Orchestrator** (режимы AI, промпты, запросы к LLM, доступ к данным)
  - → **Outbound Dispatcher** (отправка ответов обратно в каналы)
  - → **Admin UI / Operator Console** (просмотр и участие людей)
  - Параллельно: **Audit Log Service**, **Secrets Vault / Integrations Config**.

---

### 2. Базовые доменные сущности

#### 2.1. Contact

- Описывает **клиента** (пациента, ученика, покупателя).
- Ключевые поля:
  - `id` (UUID);
  - `full_name` (nullable);
  - `primary_phone`, `emails` (список), `timezone` (опционально);
  - ссылки на внешние идентификаторы:
    - `external_ids: { telegram_user_id?, whatsapp_number?, vk_user_id?, instagram_user_id?, ... }`;
  - статус/теги клиента (например: VIP, потенциальный, blacklisted).

#### 2.2. Channel

- Описывает **конкретный подключённый канал** коммуникации для аккаунта бизнеса.
- Ключевые поля:
  - `id` (UUID);
  - `business_account_id` (привязка к клинике/школе);
  - `type` (enum: `TELEGRAM_BOT`, `WHATSAPP_BUSINESS`, `VK_BOT`, `INSTAGRAM_DM`, `WEB_WIDGET`, `EMAIL_INBOX`, ...);
  - `display_name` (то, как канал будет называться в админке);
  - `status` (ACTIVE / DISABLED / ERROR / PENDING_SETUP);
  - `settings_ref` (ссылка на запись в хранилище интеграций/секретов).

#### 2.3. IntegrationConfig (секреты и настройки)

- Логическая сущность, физически часть **vault/секретного хранилища**.
- Поля (метаданные в обычной БД, сами секреты — в vault):
  - `id`, `business_account_id`, `channel_id`;
  - `provider_type` (Telegram, Facebook/Meta, etc.);
  - `scopes` (что имеет право делать: чтение сообщений, отправка и т.п.);
  - `status` (OK / EXPIRED / REVOKED);
  - `created_by`, `updated_by` (Owner / системная роль).

#### 2.4. Chat

- Единый «хаб» диалога с клиентом.
- Поля:
  - `id` (UUID);
  - `business_account_id`;
  - `contact_id`;
  - `title` (опционально, для оператора);
  - `status` (OPEN / WAITING_FOR_OPERATOR / IN_PROGRESS / CLOSED);
  - `ai_mode` (enum: `AUTO_REPLY`, `SUGGEST_ONLY`, `DISABLED`);
  - `last_message_at`, `last_actor_type` (для сортировки в UI);
  - дополнительные флаги (например, «эскалировано», «жалоба»).

#### 2.5. Message

- Описывает конкретное сообщение в диалоге.
- Поля:
  - `id` (UUID);
  - `chat_id`;
  - `contact_id` (nullable для системных/админских сообщений);
  - `channel_id` (откуда пришло / куда было отправлено);
  - `direction` (INBOUND / OUTBOUND);
  - `actor_type` (CLIENT / AI / HUMAN_ADMIN / SYSTEM / OWNER);
  - `content_type` (TEXT / MEDIA / SYSTEM_EVENT / TEMPLATE);
  - `content` (текст, ссылки на медиа и т.п.);
  - `source_metadata` (JSON: внешний message_id, thread_id, etc.);
  - `created_at`, `updated_at`;
  - `ui_hidden` (bool, soft‑hide для модерации);
  - `hidden_reason` (опционально).

#### 2.6. AISettings / AIMode

- Хранит настройки AI на разных уровнях:
  - **глобально для бизнеса**;
  - для конкретного канала;
  - для конкретного чата.
- Поля:
  - `scope` (BUSINESS / CHANNEL / CHAT);
  - `scope_id` (business_account_id / channel_id / chat_id);
  - `ai_mode` (AUTO_REPLY / SUGGEST_ONLY / DISABLED);
  - `working_hours_policy` (как вести себя в разное время);
  - `confidence_thresholds` (порог уверенности для автоответа и эскалации);
  - ссылки на наборы промптов/документов (`prompt_profile_id`, `kb_profile_id`).

#### 2.7. AuditLog

- Отдельная таблица/коллекция для **аудита действий**:
  - изменения настроек AI;
  - операции с IntegrationConfig и ключами;
  - soft‑ и hard‑delete действий над сообщениями/чатами.
- Поля:
  - `id`;
  - `business_account_id`;
  - `actor_id`, `actor_type` (OWNER / ADMIN / SYSTEM);
  - `action_type` (e.g. `MESSAGE_SOFT_HIDE`, `MESSAGE_HARD_DELETE`, `AI_MODE_CHANGED`, `INTEGRATION_KEY_ROTATED`);
  - `target_type` (MESSAGE / CHAT / INTEGRATION / SETTINGS);
  - `target_id`;
  - `metadata` (JSON, подробности);
  - `created_at`, `ip_address`, `user_agent` (по возможности).

---

### 3. Сервисы и ответственность

#### 3.1. Integration Gateway Service

- Отвечает за:
  - веб‑хуки и polling от внешних платформ (Telegram, WhatsApp, VK, Instagram*, email);
  - валидацию запросов (подписей, токенов);
  - нормализацию входящих сообщений в единый внутренний формат.
- Основные операции:
  - `handleIncomingWebhook(provider_type, raw_payload) -> NormalizedMessageDTO`;
  - `sendMessageToProvider(channel_id, OutgoingMessageDTO)`.
- Не содержит бизнес‑логики AI/чатов, только **адаптерный слой**.

#### 3.2. Identity & Routing Service

- Задача: сопоставить входящее сообщение с `Contact` и `Chat`.
- Основные функции:
  - `findOrCreateContact(normalizedMessage)`;
  - `findOrCreateChat(contact, business_account, channel)`;
  - правила мёрджа контактов по телефону/email/ID мессенджера.

#### 3.3. Conversation Service

- Управляет `Chat` и `Message`.
- Функции:
  - `createInboundMessage(normalizedMessage, contact, chat, channel) -> Message`;
  - `appendOutboundMessage(chat, actor_type, content, channel?) -> Message`;
  - изменение статусов чата (OPEN → WAITING_FOR_OPERATOR → IN_PROGRESS → CLOSED);
  - soft‑hide сообщений (только для UI, с записью в `AuditLog`).

#### 3.4. AI Orchestrator Service

- Центральный сервис принятия решений, что делать с новым сообщением.
- Задачи:
  - получить настройки AI на уровнях BUSINESS → CHANNEL → CHAT;
  - проверить `ai_mode` и рабочие часы;
  - сформировать контекст для LLM:
    - последние сообщения чата;
    - релевантные факты (прайс, расписание, услуги, статусы записей/платежей);
    - системные промпты и ограничения;
  - вызвать внешний LLM/AI‑провайдер (через отдельный `LLMClient`);
  - принять решение:
    - `AUTO_REPLY`: отправить ответ клиенту;
    - `SUGGEST_ONLY`: сохранить черновик ответа и показать оператору;
    - `ESCALATE`: не отвечать, но пометить чат как `WAITING_FOR_OPERATOR`.

#### 3.5. Outbound Dispatcher

- Отвечает за доставку исходящих сообщений:
  - в конкретный канал (Telegram, WhatsApp, etc.);
  - в Admin UI (push обновления списка сообщений/чатов).
- Функции:
  - `dispatchToChannel(message: Message)`;
  - `notifyAdmins(business_account_id, event_type, payload)` (использует существующий `NotificationService`).

#### 3.6. Admin Console / Operator API

- Backend‑API для интерфейса администратора:
  - список чатов, фильтрация по статусам и тегам;
  - просмотр истории сообщений;
  - отправка ответов от `HUMAN_ADMIN`;
  - переключение `ai_mode` на уровне чата;
  - операции soft‑hide сообщений.
- Отдельные endpoint’ы для Owner:
  - управление каналами и интеграциями;
  - настройки глобальных политик AI;
  - выгрузка audit‑логов.

#### 3.7. Secrets & Integrations Config Service

- Обёртка над выбранным vault/KMS:
  - `storeIntegrationSecret(business_account_id, channel_id, secret_payload)` (только Owner);
  - `getIntegrationSecret(channel_id)` (только системные процессы, не UI).
- Все операции логируются в `AuditLog`.

---

### 4. Основные потоки данных (sequence overview)

#### 4.1. Входящее сообщение из канала → AI → ответ клиенту

1. Веб‑хук от провайдера → `Integration Gateway Service`.
2. Нормализация → `NormalizedMessageDTO`.
3. `Identity & Routing`:
   - `findOrCreateContact`;
   - `findOrCreateChat`.
4. `Conversation Service`:
   - `createInboundMessage(...)` записывает `Message(INBOUND, CLIENT)`.
5. `AI Orchestrator`:
   - читает настройки `AISettings` (BUSINESS → CHANNEL → CHAT);
   - если `ai_mode = DISABLED` → ставит чат в очередь для оператора, без ответа клиенту;
   - если `AUTO_REPLY` или `SUGGEST_ONLY`:
     - формирует контекст (история сообщений + данные из домена расписания/услуг/платежей);
     - вызывает LLM;
     - получает `ProposedAnswer`.
6. Ветвление:
   - **AUTO_REPLY**:
     - `ConversationService.appendOutboundMessage(..., actor_type=AI, ...)`;
     - `OutboundDispatcher.dispatchToChannel(...)`;
     - при низкой уверенности AI может параллельно пометить чат `WAITING_FOR_OPERATOR`.
   - **SUGGEST_ONLY**:
     - сохраняется черновик в `Message` с `content_type = TEMPLATE` и флагом «черновик AI»;
     - `OutboundDispatcher.notifyAdmins` → в UI оператор видит предложение ответа.

#### 4.2. Клиент просит живого оператора

1. Входящее сообщение («оператор», «живой человек» и т.п.) проходит через тот же pipeline.
2. `AI Orchestrator`:
   - по детектору фраз или по явному правилу:
     - меняет статус `chat.status = WAITING_FOR_OPERATOR`;
     - отключает автодальнейшие ответы AI в этом чате (переводит `ai_mode` на уровне чата в `SUGGEST_ONLY` либо `DISABLED`).
3. `OutboundDispatcher.notifyAdmins`:
   - создаёт уведомление администраторам о необходимости подключиться.
4. Оператор в Admin UI:
   - открывает чат, видит историю;
   - отправляет ответы от своего имени (`actor_type = HUMAN_ADMIN`).

#### 4.3. Soft‑hide и удаление сообщений

1. Рабочий админ:
   - вызывает API `POST /chats/{chat_id}/messages/{message_id}/hide` с причиной.
2. Backend:
   - отмечает `ui_hidden = true`, `hidden_reason = ...` для `Message`;
   - пишет запись в `AuditLog` (`MESSAGE_SOFT_HIDE`).

3. Owner:
   - для hard‑delete использует отдельный защищённый endpoint (например, `DELETE /owner/messages/{id}`);
   - требует повторный ввод пароля/2FA;
   - при успешной проверке:
     - помечает сообщение как окончательно удалённое (логика зависит от требований по GDPR и пр.: физическое удаление или «логическое удалено»);
     - создаёт запись в `AuditLog` (`MESSAGE_HARD_DELETE`).

---

### 5. Интеграции с внешними платформами

#### 5.1. Поддерживаемые каналы (первый этап)

- Telegram Bot API;
- WhatsApp Business (через официальный провайдер/API);
- VK Messages (сообщества/боты);
- Instagram* Direct (через Meta Graph API, если возможно);
- Web‑виджет (собственный frontend на сайте);
- Email (IMAP/SMTP или провайдер типа SendGrid/Postal).

#### 5.2. Общие требования к интеграциям

- Асинхронность: long‑running операции и нестабильные провайдеры — через очереди/worker’ы.
- Идемпотентность обработки веб‑хуков:
  - внешний `message_id` должен использоваться для недопуска дублирующих сообщений.
- Лимиты и rate‑limits:
  - каждый адаптер должен уважать rate‑limits провайдера;
  - при превышении лимитов — ретраи с backoff и логирование.

---

### 6. Безопасность и хранение секретов

- Все чувствительные данные:
  - API‑ключи мессенджеров и соцсетей;
  - клиентские секреты OAuth;
  - токены доступа
  - **хранятся во внешнем vault/KMS**, а не в открытом виде в БД.

- Модель доступа:
  - только Owner/системные служебные аккаунты могут создавать/обновлять интеграции;
  - UI рабочих админов никогда не показывает сами ключи, только статус интеграции.

- Аудит:
  - все операции с секретами → `AuditLog` (`INTEGRATION_KEY_CREATED`, `ROTATED`, `REVOKED`).

---

### 7. Контракты для @DEV (API‑эскизы)

> Ниже — целевые контракты уровня REST/HTTP (названия и форматы могут уточняться при реализации, но смысл сохраняется).

#### 7.1. Веб‑хуки интеграций

- `POST /api/integrations/webhooks/{provider}`  
  - body: сырой JSON от провайдера;
  - ответ: `200 OK` с техническим ответом/echo.

#### 7.2. Работа операторов с чатами

- `GET /api/chats?status=&search=&page=&page_size=`  
  - возвращает список чатов с метаданными.

- `GET /api/chats/{chat_id}`  
  - возвращает чат и последние N сообщений.

- `GET /api/chats/{chat_id}/messages?before=&after=&limit=`  
  - пагинация истории.

- `POST /api/chats/{chat_id}/messages`  
  - body:
    - `content: string`;
    - `content_type?: "TEXT" | "MEDIA"`;
    - `channel_id?: string` (если требуется отправка в конкретный канал).
  - actor определяется по JWT (Admin/Owner).

- `POST /api/chats/{chat_id}/ai-mode`  
  - body:
    - `ai_mode: "AUTO_REPLY" | "SUGGEST_ONLY" | "DISABLED"`.

#### 7.3. Управление AI‑настройками (Owner)

- `GET /api/owner/ai-settings`  
  - глобальные и поканальные настройки.

- `PUT /api/owner/ai-settings`  
  - изменение политик AI (режимы, рабочие часы, пороги уверенности и т.п.).

#### 7.4. Управление каналами и интеграциями (Owner)

- `GET /api/owner/channels`  
  - список каналов и их статусы.

- `POST /api/owner/channels`  
  - создание нового канала (тип, название, базовые настройки).

- `PUT /api/owner/channels/{id}`  
  - изменение статуса (enable/disable) и человекочитаемых настроек.

- `POST /api/owner/channels/{id}/credentials`  
  - приём и сохранение секретов/ключей (прокидывается в vault).

#### 7.5. Audit‑лог

- `GET /api/owner/audit-log?type=&from=&to=&actor=`  
  - выгрузка действий для владельца.

---

### 8. Нефункциональные требования (NFR)

- **Надёжность:**
  - при сбое AI‑провайдера система должна:
    - не падать;
    - ставить чат в очередь к оператору;
    - логировать проблему для техподдержки.

- **Масштабируемость:**
  - `Integration Gateway` и `AI Orchestrator` должны масштабироваться горизонтально;
  - очереди для входящих/исходящих сообщений.

- **Наблюдаемость:**
  - метрики:
    - количество входящих/исходящих сообщений по каналам;
    - доля автоответов AI vs ответов операторов;
    - количество эскалаций.
  - логи:
    - технические (ошибки интеграций, timeouts);
    - бизнес‑события (запрос живого оператора, конфликтные диалоги).

- **Секьюрити:**
  - все админские операции — только по защищённым протоколам (HTTPS);
  - усиленная аутентификация Owner (2FA, уведомления о входах).

---

### 9. Следующие шаги для @DEV

- Разбить реализацию на независимые эпики:
  1. **База сущностей и миграции**: Contact, Channel, Chat, Message, AISettings, AuditLog.
  2. **Integration Gateway** для одного-двух каналов (напр., Telegram + Web‑чат) как MVP.
  3. **Conversation Service + Admin API** (просмотр/ответы операторов).
  4. **AI Orchestrator** с интеграцией с выбранным LLM и подключением к расписанию/услугам.
  5. **Secrets & Integrations Config** (интеграция с vault).
  6. Расширение на остальные каналы и доработка UI‑режимов AI.

На базе этого документа @DEV может подготовить `DEV_PROMPTS_AI_ASSISTANT_OMNICHANNEL.md` с конкретными задачами и шагами реализации.

