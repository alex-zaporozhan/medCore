## ARCH: Админские каналы и омниканальный чат

> Цель: связать настройку внешних каналов связи (Telegram, WhatsApp, VK, Viber, Max, SMS, email, произвольный «other») с уже существующим омниканальным ядром (Contact/Chat/Message/Channel/IntegrationConfig) и админ‑чатом, так чтобы владелец бизнеса мог без кода подключать любые каналы, а администраторы работали из одного окна `Омниканальный чат`.

---

### 1. Область и текущая ситуация

**Что уже есть:**

- **Домен и бекенд:**
  - `OmnichannelChannel` + `OmnichannelIntegrationConfig` + `OmnichannelChat` + `OmnichannelMessage` реализованы (см. `ARCH_AI_ASSISTANT_OMNICHANNEL*.md`, `admin_omni_chat.py`, `owner_omni_channels.py`).
  - Владелец (Owner) может через API:
    - `GET /api/v1/owner/channels` — получать список каналов;
    - `POST /api/v1/owner/channels` — создавать канал (поле `type` произвольная строка, нормализуемая в UPPER);
    - `PUT /api/v1/owner/channels/{id}` — обновлять `display_name`/`status`;
    - `POST /api/v1/owner/channels/{id}/credentials` — сохранять секреты в `OmnichannelIntegrationConfig` (шифрованно).
  - Админский омниканальный чат:
    - `GET /api/v1/admin/omni-chats` — список диалогов;
    - `GET /api/v1/admin/omni-chats/{chat_id}` — детали диалога (`channel_id`, `channel_type`, `ai_mode` и т.д.);
    - `GET /api/v1/admin/omni-chats/{chat_id}/messages` — сообщения;
    - `POST /api/v1/admin/omni-chats/{chat_id}/messages` — исходящее сообщение от администратора;
    - `POST /api/v1/admin/omni-chats/{chat_id}/ai-mode` — переключение AI режима для диалога;
    - `POST /api/v1/admin/omni-chats/{chat_id}/messages/{message_id}/hide` — soft‑hide с AuditLog.
- **Фронтенд:**
  - `/admin/omni-chat` (`AdminOmniChatPage`) — рабочий интерфейс:
    - слева — список чатов с поиском по контакту;
    - справа — лента сообщений, отправка сообщений, переключение `ai_mode`;
    - чат помечается `status` и `channel_type` (в заголовке).
  - `/admin/channels` (`AdminChannelsPage`) — **каналы уведомлений**:
    - Telegram / SMS / Email для внутренних напоминаний пациентам;
    - работает через `useChannelConfigs` и отдельную модель `NotificationChannelConfig`, **не связанную** с `OmnichannelChannel`.

**Вывод:**  
Сейчас:

- каналы на `/admin/channels` — это **уведомления и напоминания** (internal/marketing),  
- каналы омниканального чата (`OmnichannelChannel` + `OmnichannelIntegrationConfig`) — живут только в API Owner и в backend‑сервисах, но **не имеют своей админ‑страницы**.

---

### 2. Цели архитектуры

- **2.1. Для владельца (Owner):**
  - В одном месте видеть и настраивать **все омниканальные каналы связи с клиентами**:
    - Telegram, WhatsApp, Viber, VK, Max, SMS, email, любой другой чат/платформа;
    - без знания кода — только ключи/токены/URL‑ы.
  - При добавлении/обновлении канала — сразу понимать, что:
    - канал подключен / требует настройки / отключен;
    - все входящие сообщения из этого канала будут стекаться в омниканальный чат.

- **2.2. Для администраторов/операторов:**
  - Работать в едином интерфейсе `/admin/omni-chat`, где:
    - каждый диалог — агрегатор сообщений клиента из разных каналов;
    - видно **из какого канала** пришло конкретное сообщение;
    - можно:
      - быстро находить диалоги по статусу, источнику и активности AI;
      - подключаться к диалогу, когда AI не справляется или клиент просит оператора;
      - управлять `ai_mode` и статусом чата.

- **2.3. Для архитектуры:**
  - Развести понятия:
    - **NotificationChannel** (уведомления/напоминания) — остаётся на `/admin/channels`;
    - **OmnichannelChannel** (канал живого общения/AI ассистента) — новая отдельная конфигурационная страница.
  - Использовать уже существующий слой `OmnichannelChannel` + `OmnichannelIntegrationConfig` как основу для любых новых провайдеров (включая «Other»).

---

### 3. Модели и связи (омниканальные каналы)

**Ключевые сущности (актуализируем в контексте каналов):**

- `OmnichannelChannel`:
  - `id`
  - `business_account_id`
  - `type` — строковый код канала (UPPER_SNAKE_CASE);
  - `display_name` — как будет называться канал в UI;
  - `status` — `PENDING_SETUP` / `ACTIVE` / `DISABLED` / `ERROR` и т.п.
- `OmnichannelIntegrationConfig`:
  - `business_account_id`
  - `channel_id`
  - `provider_type` — тип провайдера (может дублировать/уточнять `type`);
  - `scopes` — опционально (например, `messages:read, messages:write`);
  - `credentials_encrypted` — зашифрованный blob с сырым JSON/строкой.
- `OmnichannelChat`:
  - `id`
  - `business_account_id`
  - `contact_id`
  - `channel_id` — **основной канал, в котором был создан диалог** (может быть `NULL`, если чат только веб);
  - `status` — `OPEN` / `WAITING_FOR_OPERATOR` / `IN_PROGRESS` / `CLOSED` (см. ARCH AI ассистента);
  - `ai_mode` — `DISABLED` / `AUTO_REPLY` / `SUGGEST_ONLY`.
- `OmnichannelMessage`:
  - `id`
  - `chat_id`
  - `direction` — `INBOUND` / `OUTBOUND`;
  - `actor_type` — `CLIENT` / `AI` / `HUMAN_ADMIN` / `SYSTEM`;
  - `content`
  - `source_channel_id` (опционально, если отдельное поле) **ИЛИ** берём `chat.channel_id` как основной;
  - `source_metadata` — внешний message_id, payload и т.д.;
  - `ui_hidden`, `hidden_reason`.

**Связь с интеграционным слоем:**

- Входящий вебхук (Telegram, WhatsApp, VK, Max, др.):
  - на уровне gateway определяется:
    - `business_account_id`;
    - `channel_id` (`OmnichannelChannel`) по токену/URL/секрету;
    - `contact_id` по внешнему идентификатору (телефон, messenger id, email);
    - `chat_id` (findOrCreate chat для этой пары).
  - создаётся `OmnichannelMessage` c ссылкой на канал и внешние метаданные.
- Исходящее сообщение из админки:
  - UI `/admin/omni-chat` отправляет текст → `OmnichannelChatService.append_outbound_message` → `OmnichannelOutboundDispatcher.dispatch_to_channel`:
    - диспетчер берёт `chat.channel_id` → подгружает `OmnichannelIntegrationConfig` → выбирает конкретный провайдер (Telegram/WhatsApp/Max/другие) и отправляет наружу.

---

### 4. Классификация типов каналов

**Базовый набор типов `OmnichannelChannel.type`:**

- `TELEGRAM_BOT`
- `WHATSAPP_BUSINESS`
- `VIBER_BOT`
- `VK_BOT`
- `MAX_CHAT` (условное имя для Max‑платформы)
- `SMS_GATEWAY`
- `EMAIL_INBOX`
- `OTHER`

`CreateChannelRequest.type` уже строка, нормализуется в UPPER — предлагаем:

- в UI давать пользователю выбор из преднастроенных типов, плюс «Другое»;
- `type` хранить **строгим кодом**, а «человеческое» имя — в `display_name`.

**Пример соответствия `type` ↔ `provider_type` ↔ структура payload:**

- `TELEGRAM_BOT`:
  - `provider_type`: `TELEGRAM`
  - payload (JSON) в `ChannelCredentialsRequest.payload`:
    - `bot_token`
    - `webhook_secret` (опционально)
- `WHATSAPP_BUSINESS`:
  - `provider_type`: `WHATSAPP`
  - payload:
    - `api_url`
    - `api_token`
    - `phone_number_id`
- `VIBER_BOT`:
  - `provider_type`: `VIBER`
  - payload:
    - `bot_token`
- `VK_BOT`:
  - `provider_type`: `VK`
  - payload:
    - `group_id`
    - `access_token`
- `MAX_CHAT`:
  - `provider_type`: `MAX`
  - payload:
    - `base_url`
    - `api_key`
    - `webhook_secret`
- `SMS_GATEWAY`:
  - `provider_type`: `SMS`
  - payload:
    - `login`
    - `password`
    - `sender`
- `EMAIL_INBOX`:
  - `provider_type`: `EMAIL`
  - payload:
    - `imap_host`
    - `imap_port`
    - `imap_user`
    - `imap_password`
    - `inbox_email`
- `OTHER`:
  - `provider_type`: свободная строка;
  - payload:
    - произвольный JSON (например, `{ "webhook_url": "...", "auth_header": "Bearer ..." }`).

**Важно:** структура payload **не зашивается жёстко в модель**, а описывается:

- в UI (формы для каждого типа);
- в коде адаптеров провайдеров (OutboundDispatcher + IntegrationGateway).

---

### 5. UI для Owner: страница «Омниканальные каналы»

**Новый экран (рабочее имя):**

- URL: `/admin/omni-channels` (или включить как отдельный пункт в раздел «Настройки»).
- Назначение: управление объектами `OmnichannelChannel` + их `OmnichannelIntegrationConfig`.

**Функции:**

- Список каналов:
  - колонки: Тип (иконка/лейбл), Название (`display_name`), Статус, Подключено (по `has_credentials`), Последняя активность (опционально).
  - действия: «Редактировать», «Отключить/Включить».
- Добавление канала:
  - выбор типа из предустановленных (`TELEGRAM_BOT`, `WHATSAPP_BUSINESS`, `VIBER_BOT`, `VK_BOT`, `MAX_CHAT`, `SMS_GATEWAY`, `EMAIL_INBOX`, `OTHER`);
  - задание `display_name`;
  - сохранение создаёт `OmnichannelChannel` через `POST /owner/channels`.
- Настройка интеграции:
  - для каждого типа отображается соответствующая форма (как сейчас на `/admin/channels`, только на уровне `OmnichannelIntegrationConfig`);
  - при сохранении:
    - вызывается `POST /owner/channels/{id}/credentials`;
    - UI не показывает сырой secret, только флаг «подключено».

**Взаимосвязь с уже существующей `/admin/channels`:**

- `/admin/channels` **остаётся страницей для NotificationChannelConfig** (напоминания, триггерные уведомления, маркетинг).
- Новая `/admin/omni-channels` посвящена **каналам диалогов**.
- В тексте/подзаголовках нужно явно развести смысл:
  - «Каналы уведомлений» vs «Каналы общения (омниканальные)».

---

### 6. UI для админов: развитие `/admin/omni-chat`

**6.1. Текущее поведение (по коду `AdminOmniChatPage` + `useAdminOmniChat`):**

- Список чатов:
  - подгружается с `/v1/admin/omni-chats`, обновляется каждые 5 секунд;
  - можно искать по имени/телефону (`search`);
  - виден `status`, `last_actor_type`, но:
    - нет фильтров по статусу/AI/каналу;
    - нет отдельной очереди «ждёт оператора».
- Детали чата:
  - заголовок: имя/телефон контакта, `status`, `channel_type`;
  - селектор `ai_mode` (`DISABLED` / `AUTO_REPLY` / `SUGGEST_ONLY`), связанный с `POST /admin/omni-chats/{chat_id}/ai-mode`.
- Сообщения:
  - загружаются из `/v1/admin/omni-chats/{chat_id}/messages` (лимит 100, без пагинации далее);
  - отображаются как простая лента, различая только направление/actor;
  - soft‑hide уже поддержан на API уровне (поле `ui_hidden`, `hidden_reason`), но UI пока не показывает модерацию и не даёт скрывать сообщения.

**6.2. Что нужно для соответствия бизнес‑образу (BIZ_AI_ASSISTANT_OMNICHANNEL):**

- **Очереди и статусы:**
  - статусы чатов:
    - `AI_ONLY` / `WAITING_FOR_OPERATOR` / `IN_PROGRESS` / `CLOSED` (имена можно привести к единому набору в домене);
  - UI‑фильтры:
    - «все», «только AI ведёт диалог», «ждёт оператора», «в работе у оператора», «закрыт»;
  - выделение чатов в статусе `WAITING_FOR_OPERATOR` (цвет/иконка, сортировка вверх списка).
- **Флаг участия AI:**
  - быстрые фильтры/бейджи по `ai_mode`:
    - например, отображать иконку режима AI около каждого диалога;
  - возможность быстро отключать/включать AI для диалога, не заходя в карточку (контекстное меню/иконка в списке).
- **Детекция запроса оператора и эскалация:**
  - backend: уже предусмотрен сценарий в ARCH Review (детекция ключевых фраз и установка статуса `WAITING_FOR_OPERATOR` + уведомление админов);
  - frontend:
    - отдельный фильтр/вкладка «Запросы оператора»;
    - визуальное выделение чатов, попавших по такому триггеру.
- **Работа с сообщениями:**
  - отображение `ui_hidden` и `hidden_reason` при включённом режиме `include_hidden=true`:
    - например, серое сообщение с пометкой «скрыто модератором: [причина]»;
  - возможность скрыть сообщение из UI (кнопка/меню на сообщении), вызывая `POST /messages/{id}/hide`.
- **Происхождение сообщений:**
  - на уровне UI:
    - для каждого сообщения показывать, из какого канала оно пришло (`TELEGRAM`, `WHATSAPP`, `VK`, `WEBCHAT` и т.п.), если эта информация есть в DTO;
  - при необходимости можно расширить DTO `OmniMessageDto` полями `channel_type` / `source_channel_type`.

**6.3. UX‑детали для производственной работы:**

- быстрые «пресеты» фильтров: «Новые диалоги», «Только AI», «В работе у оператора»;
- возможность помечать диалог как «важный»/«VIP» (доп. флаг/тег в домене, не обязательно на первом этапе);
- отображение счётчика непрочитанных для текущего администратора (вокруг уже есть паттерн `useAdminChatConversations` и `chatUnread` в `AdminLayout` — аналогично можно расширить для omni‑чата).

---

### 7. Ответы на вопросы по архитектуре

- **Связаны ли каналы страницы `/admin/channels` с каналами омниканального чата?**
  - На текущем состоянии кода — **нет**:
    - `/admin/channels` управляет `NotificationChannelConfig` для напоминаний и уведомлений;
    - Омниканальные каналы представлены сущностью `OmnichannelChannel` и настраиваются только через Owner API (`/owner/channels`), без UI.
  - После внедрения этого ARCH:
    - `/admin/channels` остаётся для уведомлений;
    - появляется отдельная страница (например, `/admin/omni-channels`), которая работает поверх `OmnichannelChannel`/`OmnichannelIntegrationConfig` и **непосредственно связана** с омниканальным чатом.

- **Можно ли сюда подключать любой чат/API (включая Max и произвольные «other»)?**
  - Да, концептуально уже сейчас:
    - `CreateChannelRequest.type` — свободная строка;
    - `ChannelCredentialsRequest.payload` — произвольная строка/JSON;
  - ARCH уточняет:
    - стандартные типы (Telegram/WhatsApp/Viber/VK/Max/SMS/Email);
    - механизм `OTHER` с произвольным JSON и отдельным адаптером в интеграционном слое.

- **Как работает фронтенд омниканального чата и достаточно ли он как инструмент администратора?**
  - Сейчас:
    - все диалоги стекаются в `/admin/omni-chat`, оператор может:
      - просматривать список диалогов и сообщений;
      - отвечать от имени администратора;
      - переключать `ai_mode` по диалогу.
    - этого достаточно для **технического MVP**, но не для полноценного контакт‑центра.
  - После доработок по этому ARCH:
    - появятся статусы и очереди, фильтры, явная работа с запросами «живого оператора», модерация сообщений и улучшенная видимость каналов;
    - интерфейс станет ближе к Intercom/HelpCrunch‑подобным решениям, как описано в BIZ‑документе.

---

### 8. Нефункциональные требования (каналы + чат)

- **Безопасность:**
  - все токены и ключи каналов по‑прежнему хранятся в `OmnichannelIntegrationConfig.credentials_encrypted` с шифрованием;
  - Owner и технические аккаунты — единственные, кто может менять эти ключи (см. BIZ‑документ и ARCH Review).
- **Наблюдаемость и аудит:**
  - любые изменения каналов и ключей идут через `OmnichannelIntegrationsConfigService` с записью в AuditLog;
  - soft‑hide сообщений всегда логируется с указанием администратора, IP, user‑agent.
- **Расширяемость:**
  - добавление нового провайдера сводится к:
    - добавлению нового типа `OmnichannelChannel.type` и UI‑формы для его payload;
    - реализации адаптера для inbound/outbound в интеграционном слое;
    - при желании — добавлению преднастроенного пресета в UI.

---

### 9. Критерии готовности реализации

- Есть отдельная админ‑страница для **омниканальных каналов**, работающая поверх `OmnichannelChannel`/`OmnichannelIntegrationConfig`, с базовыми типами (Telegram, WhatsApp, Viber, VK, Max, SMS, email, Other).
- Владелец может **создать**, **переименовать**, **отключить** канал и **задать/обновить_credentials** без знания кода; UI никогда не показывает секреты в открытом виде.
- Омниканальный чат `/admin/omni-chat`:
  - показывает статусы диалогов и режимы AI;
  - имеет фильтры по статусу и режиму AI;
  - поддерживает очередь «ждёт оператора» и визуальное выделение таких диалогов;
  - позволяет скрывать сообщения (soft‑hide) и видеть скрытые при включённом режиме модерации.
- Вся логика совместима с текущим `ARCH_AI_ASSISTANT_OMNICHANNEL*.md` и рекомендациями из `ARCH_AI_ASSISTANT_OMNICHANNEL_REVIEW.md`.

