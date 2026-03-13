## DEV_PROMPTS: Админские омниканальные каналы и омниканальный чат

> Основано на `ARCH_OMNICHANNEL_ADMIN_CHANNELS_AND_CHAT.md` + `ARCH_AI_ASSISTANT_OMNICHANNEL*.md` + текущей реализации `owner_omni_channels.py` и `admin_omni_chat.py`.

---

### 0. Общие принципы

- Не ломать существующую страницу `/admin/channels` — она продолжает управлять **каналами уведомлений** (`NotificationChannelConfig`).
- Для омниканальных каналов (живое общение/AI) использовать уже существующие сущности:
  - `OmnichannelChannel`
  - `OmnichannelIntegrationConfig`
  - Owner API: `/api/v1/owner/channels`, `/api/v1/owner/channels/{id}`, `/api/v1/owner/channels/{id}/credentials`.
- Все секреты и токены:
  - пишем только через `OmnichannelIntegrationsConfigService.store_integration_secret`;
  - **никогда** не возвращаем в явном виде во фронтенд (только `has_credentials`/статус).

---

### 1. Новый фронтенд для омниканальных каналов (Owner)

#### 1.1. Создать hook API клиента для Owner Omnichannel Channels

**Файл:** `frontend/src/hooks/useOwnerOmniChannels.ts` (рабочее имя, можно скорректировать, но сохранить единый стиль с `useOwnerOmniAiSettings.ts`).

**Сделать:**

- Типы:
  - `OwnerOmniChannel`:
    - `id: string`
    - `type: string`
    - `display_name: string`
    - `status: string`
    - `has_credentials: boolean`
  - `OwnerOmniChannelsResponse`:
    - `items: OwnerOmniChannel[]`
- Хуки (через `@tanstack/react-query` и `api` как в других хуках):
  - `useOwnerOmniChannels()`:
    - `GET /v1/owner/channels`
    - key: `["owner-omni-channels"]`
  - `useCreateOwnerOmniChannel()`:
    - `POST /v1/owner/channels`
    - body: `{ type: string; display_name: string }`
    - invalidate: `["owner-omni-channels"]`
  - `useUpdateOwnerOmniChannel()`:
    - `PUT /v1/owner/channels/{id}`
    - body: `{ display_name?: string; status?: string }`
    - invalidate: `["owner-omni-channels"]`
  - `useSetOwnerOmniChannelCredentials()`:
    - `POST /v1/owner/channels/{id}/credentials`
    - body: `{ provider_type: string; scopes?: string | null; payload: string }`
    - invalidate: `["owner-omni-channels"]`

**Проверка:**

- линтер+типизация без ошибок;
- при ошибках API — bubbling ошибок на уровень компонента (через `error`/`isError`).

---

#### 1.2. Страница админки для омниканальных каналов

**Файл:** `frontend/src/admin/pages/AdminOmniChannelsPage.tsx` (новый).

**UI‑задача:**

- Сделать страницу в духе текущей `AdminChannelsPage`, но:
  - данные — из `useOwnerOmniChannels`;
  - семантика — **каналы общения**, не уведомлений.

**Функционал:**

- Заголовок: `Омниканальные каналы`.
- Описание (кратко): объяснить, что это каналы, через которые AI/операторы общаются с клиентами (Telegram, WhatsApp, VK, Viber, Max, SMS, email, другие).
- Список каналов:
  - таблица/карточки с полями:
    - Тип (читаемый лейбл по `type`);
    - Отображаемое имя (`display_name`);
    - Статус (`status`, badge);
    - Подключено (иконка/лейбл по `has_credentials`).
  - Кнопка «Добавить канал»:
    - селект типа (см. список кодов в ARCH: `TELEGRAM_BOT`, `WHATSAPP_BUSINESS`, `VIBER_BOT`, `VK_BOT`, `MAX_CHAT`, `SMS_GATEWAY`, `EMAIL_INBOX`, `OTHER`);
    - поле `display_name`;
    - при сабмите → `useCreateOwnerOmniChannel.mutate`.
- Редактирование канала:
  - возможность поменять `display_name` и `status`:
    - изменение через `useUpdateOwnerOmniChannel.mutate`.
- Настройка креденшелов:
  - для каждой строки — кнопка «Настроить ключи/интеграцию»:
    - открывает модальное окно/дропдаун с формой, зависящей от `type`:
      - `TELEGRAM_BOT`: `bot_token`, `webhook_secret?`;
      - `WHATSAPP_BUSINESS`: `api_url`, `api_token`, `phone_number_id`;
      - `VIBER_BOT`: `bot_token`;
      - `VK_BOT`: `group_id`, `access_token`;
      - `MAX_CHAT`: `base_url`, `api_key`, `webhook_secret`;
      - `SMS_GATEWAY`: `login`, `password`, `sender`;
      - `EMAIL_INBOX`: `imap_host`, `imap_port`, `imap_user`, `imap_password`, `inbox_email`;
      - `OTHER`: свободный JSON (textarea) или пара «ключ‑значение» (MVP можно сделать textarea с JSON).
    - при сабмите:
      - собрать JSON-объект;
      - привести к строке `JSON.stringify`;
      - вызвать `useSetOwnerOmniChannelCredentials` c `provider_type` (согласованным с ARCH) и `payload`.
    - После успешного сабмита:
      - закрыть модалку;
      - обновить список (инвалидация уже в hook).

**Интеграция в роутер:**

- В `frontend/src/App.tsx`:
  - импортировать `AdminOmniChannelsPage`;
  - добавить роут:
    - либо отдельный путь `/admin/omni-channels`;
    - либо использовать `/admin/integrations`/`/admin/settings`, но **рекомендуется отдельный путь**.
- В `AdminSettingsPage`:
  - опционально добавить ссылку «Омниканальные каналы связи», если нужно отдельное меню.
- В `AdminLayout`:
  - по желанию — добавить ссылку в блок «Настройки», если важно быстрый доступ.

**Проверка:**

- Запуск фронта, ручной прогон:
  - можно создать канал Telegram/Max/Other;
  - статус `has_credentials` меняется на `true` после сохранения секретов;
  - ни один secret не попадает в network‑ответы (`has_credentials` только bool).

---

### 2. Улучшения омниканального чата для админов

#### 2.1. Фильтры и статусы в списке чатов

**Бекенд (по необходимости, если ещё нет полного покрытия):**

- Проверить доменную модель `OmnichannelChat.status` и возможные значения.
- Если в домене уже описаны статусы, согласовать с BIZ/ARCH:
  - минимум: `OPEN`, `WAITING_FOR_OPERATOR`, `IN_PROGRESS`, `CLOSED`.
- В `list_omni_chats` (`admin_omni_chat.py`) статус уже фильтруется по query‑параметру `status` — оставить как есть, убедиться что список значений документирован в коде/доках.

**Фронтенд:**

- В `AdminOmniChatPage`:
  - сейчас `statusFilter` зафиксирован в `undefined`.  
  - Заменить на настоящий селект:
    - добавить `Select` с опциями:
      - `Все` (undefined),
      - `Только AI` (если в домене есть такой статус, иначе можно отфильтровать по `ai_mode` — см. ниже),
      - `Ждёт оператора` (`WAITING_FOR_OPERATOR`),
      - `В работе` (`IN_PROGRESS`),
      - `Закрыт` (`CLOSED`).
    - при выборе значения — обновлять `statusFilter` и вызывать `useAdminOmniChats` с этим параметром (он уже передаётся).
- В списке чатов:
  - визуально выделять:
    - `WAITING_FOR_OPERATOR` — цвет/иконка;
    - `CLOSED` — более «приглушённый» стиль.

---

#### 2.2. Отображение и управление AI‑режимами

**Фронтенд:**

- В header выбранного чата:
  - уже есть `Select` по `OMNI_CHAT_AI_MODES`.  
  - Проверить, что:
    - значение берётся из `chatDetail.ai_mode`;
    - при смене → отправляется `useUpdateOmniChatAiMode.mutate` (уже так и сделано).
- Добавить визуальные индикаторы в списке диалогов:
  - возле каждого элемента списка отображать компактный бейдж с текущим AI‑режимом:
    - `AI выкл.`, `AI автоответ`, `AI подсказки`.
  - Значение можно брать:
    - либо расширив DTO `OmniChatListItemDto` на бекенде полем `ai_mode` и прокинув его;
    - либо подмешивая информацию из `chatDetail` (но это потребует доп. запросов; предпочтительно добавить поле на бекенд).

**Бекенд (опционально, но желательно):**

- В `OmniChatListItemDto` + сборке DTO в `list_omni_chats`:
  - добавить поле `ai_mode: str` (по аналогии с `OmniChatDetailDto`);
  - заполнять его из `chat.ai_mode` с дефолтом `"DISABLED"`.

---

#### 2.3. Очередь «ждёт оператора» и детекция запросов оператора

**Бекенд (частично уже описан в ARCH Review):**

- В `OmnichannelAIOrchestrator` (см. `ARCH_AI_ASSISTANT_OMNICHANNEL_REVIEW.md`):
  - добавить простую эвристику:
    - по последнему inbound‑сообщению клиента искать фразы вида:
      - «оператор», «живой человек», «менеджер», «администратор», «хочу поговорить с человеком» и т.п. (RU; позже можно добавить EN).
  - При срабатывании:
    - установить `chat.status = "WAITING_FOR_OPERATOR"`;
    - при необходимости переключить `ai_mode` на `SUGGEST_ONLY` или `DISABLED`;
    - вызвать `NotificationService.notifyAdmins(...)` (или аналогичный механизм), чтобы операторы увидели новый диалог в очереди.

**Фронтенд:**

- В `AdminLayout`:
  - опционально добавить отдельный пункт меню «Омниканальный чат (очередь)» с бейджем количества диалогов в статусе `WAITING_FOR_OPERATOR` (для этого может понадобиться отдельный endpoint/фильтр).
- В `AdminOmniChatPage`:
  - добавить быстрый переключатель/кнопку «Показать только диалоги, ожидающие оператора»:
    - под капотом — `status=WAITING_FOR_OPERATOR`.

---

#### 2.4. Soft‑hide и модерация сообщений

**Бекенд:**

- Уже реализовано:
  - `GET /admin/omni-chats/{chat_id}/messages` принимает `include_hidden`;
  - DTO `OmniMessageDto` содержит `ui_hidden` и `hidden_reason`;
  - `POST /admin/omni-chats/{chat_id}/messages/{message_id}/hide` выполняет soft‑hide и пишет AuditLog.
- Проверить:
  - по умолчанию `include_hidden=False` (так и есть);
  - при `include_hidden=True` возвращаются все сообщения.

**Фронтенд:**

- В `AdminOmniChatPage`:
  - в хуке `useAdminOmniChatMessages` добавить опцию `include_hidden?: boolean`, которая мапится на query‑параметр;
  - в UI:
    - чекбокс/переключатель «Показывать скрытые сообщения (для модераторов)»;
    - при включении:
      - вызывать `useAdminOmniChatMessages` с `include_hidden=true`;
      - отображать скрытые сообщения в сером цвете, с подписью:
        - «Сообщение скрыто: [hidden_reason]».
- Для каждого сообщения:
  - добавить контекстное меню/кнопку «Скрыть сообщение» (видно только рабочим админам/Owner в UI):
    - при клике:
      - запросить причину (простое модальное окно/textarea);
      - вызвать `useHideAdminOmniMessage.mutate({ chatId, messageId, reason })`;
      - после успеха → инвалидация сообщений (уже есть в hook).

---

#### 2.5. Отображение источника сообщения (канал)

**Бекенд (опционально, но желательно):**

- В `OmniMessageDto`:
  - при необходимости добавить поле `channel_type: str | None` или `source_channel_type: str | None`;
  - заполнять:
    - либо из `message.source_channel_id → OmnichannelChannel.type`;
    - либо из `chat.channel_id → OmnichannelChannel.type` (если нет более точного поля).

**Фронтенд:**

- В `AdminOmniChatPage`:
  - рядом с `actor_type` или в отдельной строке показывать канал:
    - пример: `CLIENT • TELEGRAM` или `AI • WHATSAPP`.

---

### 3. Разграничение `/admin/channels` и новой страницы

**Задача:**

- Явно развести в UI смысл:
  - `/admin/channels` — **Каналы уведомлений** (напоминания, смс/email/telegram для рассылок и системных уведомлений).
  - `/admin/omni-channels` — **Каналы общения** (омниканальные, для AI и живых админов).

**Шаги:**

- В `AdminChannelsPage`:
  - обновить подзаголовок:
    - подчеркнуть, что каналами здесь управляет механика уведомлений и напоминаний; они не влияют на омниканальный чат.
- В новом `AdminOmniChannelsPage`:
  - в описании явно указать:
    - «Здесь вы подключаете каналы, через которые клиенты пишут вам (Telegram, WhatsApp, VK, Viber, Max, SMS, email, другие). Все сообщения из них будут стекаться в раздел `Омниканальный чат`.»

---

### 4. Тесты

#### 4.1. Бекенд‑тесты для Owner Omnichannel Channels

**Файл:** дополнить `tests/api/test_owner_omni_channels.py`.

**Покрыть:**

- Создание канала с каждым ключевым `type` (минимум: `TELEGRAM_BOT`, `WHATSAPP_BUSINESS`, `VIBER_BOT`, `VK_BOT`, `MAX_CHAT`, `SMS_GATEWAY`, `EMAIL_INBOX`, `OTHER`):
  - проверить:
    - `type` сохраняется в UPPER;
    - `status == "PENDING_SETUP"`;
    - `has_credentials == False`.
- Установка креденшелов:
  - `POST /owner/channels/{id}/credentials` для хотя бы двух типов (например, Telegram и Max):
    - запись создаётся в `OmnichannelIntegrationConfig`;
    - в API‑ответе списка каналов у нужного канала `has_credentials == True`;
    - сырых секретов в ответе нет.
- Ограничения доступа:
  - владелец не может менять каналы чужой клиники (повтор логики уже существующего теста, но можно расширить).

---

#### 4.2. Фронтенд‑проверка (ручная/авто)

**Минимальный набор ручных сценариев:**

- Owner заходит в админку:
  - открывает `/admin/omni-channels`;
  - добавляет Telegram‑канал, вводит токен, видит, что канал помечен «подключено».
- Проверка связи с омни‑чатом (после интеграции вебхуков конкретного провайдера):
  - сообщение из Telegram (или другого подключённого канала) появляется в списке `/admin/omni-chat`;
  - заголовок/сообщения показывают правильный `channel_type`.

При наличии инфраструктуры E2E‑тестов — можно добавить smoke‑тест на UI (открытие страниц, базовые действия без реальных внешних провайдеров).

---

### 5. Критерии «готово»

- Есть:
  - `useOwnerOmniChannels.ts` с хуками для списка/создания/обновления/креденшелов;
  - `AdminOmniChannelsPage` с CRUD‑интерфейсом и базовыми типами каналов.
- `AdminOmniChatPage`:
  - поддерживает фильтры по статусу диалога;
  - отображает/управляет `ai_mode` (в заголовке и/или списке);
  - даёт скрывать сообщения (soft‑hide) и видеть скрытые с пометкой причины при включённом режиме модерации;
  - опционально показывает источник канала для сообщений.
- Бекенд:
  - покрыт тестами для сценариев Owner Omnichannel Channels;
  - при необходимости расширен полями `ai_mode`/`channel_type` в DTO для списков.
- Документация:
  - этот файл и `ARCH_OMNICHANNEL_ADMIN_CHANNELS_AND_CHAT.md` актуальны и отражают реализованное поведение.

