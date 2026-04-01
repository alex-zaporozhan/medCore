## 🛠 DEV PROMPTS: AI‑омниканальный ассистент и контакт‑центр

> Этот файл — рабочий сценарий для @DEV: что реализуем, по каким фазам, в каком порядке.  
> Архитектурный источник правды: `ARCH_AI_ASSISTANT_OMNICHANNEL.md`.

---

### 0. Общие договорённости для разработки

- **Ядро домена / backend‑сервисы** — в существующем стекe проекта (см. текущие ARCH/DEV_PROMPTS).
- **Фичу собираем итеративно**:
  - MVP: Telegram + Web‑чат, базовые сущности, AI в режиме `SUGGEST_ONLY` или `AUTO_REPLY` для FAQ.
  - Затем расширение на другие каналы (WhatsApp, VK, Instagram*, Email).
- **Важный принцип:** никаких «тихих» удалений. Любое изменение/удаление логируется, как описано в ARCH.

Рекомендация: вести отдельную ветку/фичу `feature/ai-omnichannel-assistant`.

---

### Фаза 1. База сущностей и миграции (Contact, Channel, Chat, Message, AISettings, AuditLog)

**Цель фазы:** поднять доменную модель и минимальные репозитории так, чтобы можно было создавать чаты/сообщения даже без реальных интеграций и AI.

**Шаги:**

1. **Создать модели и миграции:**
   - `Contact`:
     - поля см. `ARCH_AI_ASSISTANT_OMNICHANNEL.md` (раздел 2.1).
   - `Channel`:
     - тип канала, статус, привязка к бизнес‑аккаунту.
   - `Chat`:
     - статус, `ai_mode`, ссылки на `Contact`, `business_account_id`.
   - `Message`:
     - `direction`, `actor_type`, `content`, `source_metadata`, `ui_hidden`, `hidden_reason`.
   - `AISettings` (или аналогичная таблица/конфигурация):
     - scope (BUSINESS / CHANNEL / CHAT), `ai_mode`, политики.
   - `AuditLog`:
     - `actor_type`, `action_type`, `target_type`, `target_id`, `metadata`.

2. **Реализовать репозитории/DAO и базовый сервис работы с чатами:**
   - CRUD для `Chat`, `Message`, `Contact`, `Channel`, `AISettings`, `AuditLog`.
   - Методы выборки:
     - последние N сообщений по чату;
     - поиск чатов по статусу, `business_account_id`, текстовому поиску (по желанию).

3. **Покрыть базовые операции тестами (минимум unit/integration):**
   - создание контакта и чата;
   - добавление входящего и исходящего сообщения;
   - soft‑hide сообщения и запись в `AuditLog`.

**Готовность фазы:** можно вручную создать через код/скрипты Chat+Message+Contact и увидеть, что всё корректно сохраняется и читается.

---

### Фаза 2. MVP Integration Gateway (Telegram + Web‑чат)

**Цель фазы:** подключить хотя бы два канала (Telegram‑бот и Web‑чат) к домену Chat/Message.

**Шаги:**

1. **Integration Gateway для Telegram:**
   - HTTP‑endpoint `POST /api/integrations/webhooks/telegram`:
     - валидация токена/подписей;
     - преобразование в `NormalizedMessageDTO`:
       - `external_message_id`, `from_id`, `chat_id`, `text`, `timestamp`.
   - Метод отправки сообщений:
     - клиент к Telegram Bot API (sendMessage);
     - функция `sendMessageToProvider(channel_id, OutgoingMessageDTO)`.

2. **Integration Gateway для Web‑чата:**
   - простой REST/WebSocket‑слой:
     - `POST /api/webchat/messages` — приём сообщений от виджета;
     - WebSocket/long‑polling для отдачи новых сообщений.
   - Нормализация в тот же `NormalizedMessageDTO`.

3. **Identity & Routing (минимальный):**
   - по Telegram:
     - `findOrCreateContact` по комбинации `telegram_user_id` (+ телефон/email, если есть);
   - по Web‑чату:
     - временный анонимный идентификатор с возможностью позже связать с телефоном/email.
   - `findOrCreateChat`:
     - один открытый чат на `Contact` + `business_account_id` (в простом варианте).

4. **Простой pipeline до Conversation Service:**
   - webhook → NormalizedMessageDTO → Contact/Chat → `createInboundMessage(...)`.

**Готовность фазы:** можно прислать сообщение в Telegram‑бот или Web‑чат → оно отобразится в БД как `Message(INBOUND, CLIENT)` в связанном `Chat`.

---

### Фаза 3. Conversation Service + Admin API (без AI)

**Цель фазы:** дать рабочему админу UI/API для чтения и ручного ответа в чатах (AI пока не участвует).

**Шаги:**

1. **Реализовать Conversation Service:**
   - `createInboundMessage(normalizedMessage, contact, chat, channel)`:
     - создаёт запись `Message` с нужными полями;
     - обновляет `chat.last_message_at`, `last_actor_type`.
   - `appendOutboundMessage(chat, actor_type, content, channel?)`:
     - создаёт `Message(OUTBOUND, actor_type, ...)`;
     - обновляет статус чата (например, OPEN/IN_PROGRESS).
   - soft‑hide:
     - метод `hideMessage(message_id, reason, actor)` с записью в `AuditLog`.

2. **Admin API (операторский backend):**
   - `GET /api/chats?status=&search=&page=&page_size=`;
   - `GET /api/chats/{chat_id}`;
   - `GET /api/chats/{chat_id}/messages?before=&after=&limit=`;
   - `POST /api/chats/{chat_id}/messages`:
     - actor определяется по JWT (Admin/Owner);
     - создаёт `Message(OUTBOUND, HUMAN_ADMIN)` и инициирует отправку в нужный канал (или только в чат, если это Web‑чат).
   - `POST /api/chats/{chat_id}/messages/{message_id}/hide` (soft‑hide).

3. **Интеграция с Outbound Dispatcher (без AI):**
   - после `appendOutboundMessage`:
     - если `channel_id` указан — вызов `dispatchToChannel(message)`;
     - если это Web‑чат — пуш в WebSocket/long‑poll.

4. **Базовый UI (если в проекте уже есть фронт для админки):**
   - список чатов;
   - просмотр диалога;
   - поле ввода ответа админом.

**Готовность фазы:** оператор может:
  - видеть новые сообщения, пришедшие из Telegram/Web‑чата;
  - отвечать в эти каналы из единой админки, без участия AI.

---

### Фаза 4. AI Orchestrator (AUTO_REPLY / SUGGEST_ONLY) + интеграция с доменом

**Цель фазы:** встроить AI‑конвейер, который на основе настроек решает, как обрабатывать новые входящие сообщения.

**Шаги:**

1. **Реализовать AISettings и сервис доступа к ним:**
   - функции:
     - `getEffectiveSettings(business_account_id, channel_id, chat_id)`:
       - читает настройки в порядке BUSINES → CHANNEL → CHAT;
       - собирает итоговый `ai_mode`, `working_hours_policy`, `confidence_thresholds`, ссылки на промпты/KB.

2. **Сервис AI Orchestrator:**
   - точка входа, вызываемая после `createInboundMessage(...)`:
     - `handleIncomingForAI(message: Message, chat: Chat, contact: Contact)`.
   - логика:
     - получает `effectiveSettings`;
     - если `ai_mode = DISABLED` → ничего не делает либо ставит чат в очередь для оператора;
     - если `AUTO_REPLY` или `SUGGEST_ONLY`:
       - собирает контекст:
         - последние N сообщений по чату;
         - данные из домена (прайс, расписание, статусы заявок/платежей) через существующие сервисы;
       - формирует prompt для LLM (с системными ограничениями и фактами);
       - вызывает клиент LLM (см. п.3).

3. **LLM‑клиент:**
   - создать абстракцию `LLMClient`:
     - `generateReply(context: AIContext) -> LLMReply { text, confidence, meta }`.
   - под капотом — конкретный поставщик (OpenAI, другие; выбор по текущему стеку проекта).

4. **Ветвление по режиму:**
   - **AUTO_REPLY:**
     - если `confidence >= threshold_auto`:
       - создать `Message(OUTBOUND, AI)` с текстом модели;
       - `OutboundDispatcher.dispatchToChannel(message)`;
       - опционально: если `confidence` средний, пометить чат как требующий внимания оператора.
     - если `confidence < threshold_auto`:
       - чат помечается `WAITING_FOR_OPERATOR`, создаётся задача для админов (без ответа клиенту).
   - **SUGGEST_ONLY:**
     - создать `Message` с `content_type = TEMPLATE`, пометкой «черновик AI»;
     - `notifyAdmins` о наличии предложения ответа.

5. **Настройки и промпты:**
   - описать структуру промптов и подключение к документам/FAQ:
     - пока достаточно:
       - статический системный промпт (описание роли ассистента, запреты);
       - данные из домена как JSON/табличка внутри промпта.
   - дальнейшее развитие (retrieval, векторные индексы) можно вынести в отдельную фазу.

**Готовность фазы:** при включённом `ai_mode`:
  - на новые сообщения AI либо отвечает сам (AUTO_REPLY), либо предлагает черновик для оператора (SUGGEST_ONLY), как описано в BIZ/ARCH.

---

### Фаза 5. Secrets & Integrations Config (vault, права Owner)

**Цель фазы:** безопасно хранить API‑ключи/токены интеграций и ограничить доступ к ним.

**Шаги:**

1. **Инкапсулировать работу с секретами в сервис:**
   - `SecretsService`/`IntegrationsConfigService`:
     - `storeIntegrationSecret(business_account_id, channel_id, payload, actor)`:
       - сохраняет метаданные в БД;
       - передаёт секреты в vault/KMS;
       - пишет запись в `AuditLog`.
     - `getIntegrationSecret(channel_id, system_actor)`:
       - только для системных/фоновых процессов.

2. **Owner‑API для управления интеграциями:**
   - `GET /api/owner/channels`;
   - `POST /api/owner/channels`;
   - `PUT /api/owner/channels/{id}`;
   - `POST /api/owner/channels/{id}/credentials`:
     - принимает ключи/токены;
     - вызывает `storeIntegrationSecret`.

3. **Ограничить UI и права:**
   - рабочий админ:
     - видит только статус интеграции (OK / ERROR / EXPIRED);
   - Owner:
     - имеет доступ к экранам настройки ключей;
     - все его действия (создание/обновление/удаление ключей) логируются.

**Готовность фазы:** Owner может добавить/обновить токен интеграции, рабочий админ не видит сам токен, но каналы корректно работают.

---

### Фаза 6. Расширение каналов и UI‑режимов AI

**Цель фазы:** добавить остальные каналы и сделать гибкую настройку AI (глобально, по каналам, по чатам).

**Шаги:**

1. **Добавить адаптеры для:**
   - WhatsApp Business;
   - VK Messages;
   - Instagram* Direct;
   - Email.
   - Все — через тот же `Integration Gateway` и `NormalizedMessageDTO`.

2. **Расширить AISettings:**
   - настройки по каналам (например: в Telegram — AUTO_REPLY, в Instagram — SUGGEST_ONLY);
   - настройки по конкретным чатам (настроить через Admin UI и API `POST /api/chats/{chat_id}/ai-mode`).

3. **UI в админке для AI‑режимов:**
   - глобальные настройки (Owner);
   - переключатели на уровне канала;
   - быстрый переключатель для конкретного чата (кнопка «AI: выкл / автоответ / подсказки»).

**Готовность фазы:** система поддерживает несколько каналов, AI‑режимы можно настраивать на разных уровнях, и всё это отражено в UI и в поведении чат‑ядра.

---

### Фаза 7. Наблюдаемость, метрики и отладка

**Цель фазы:** сделать систему управляемой в проде.

**Шаги:**

1. **Метрики:**
   - количество входящих/исходящих сообщений по каналам;
   - доля автоответов AI vs ответов операторов;
   - количество и доля эскалаций;
   - ошибки интеграций (rate‑limits, timeouts).

2. **Логи и трассировка:**
   - структурированные логи по основным сервисам (`Integration Gateway`, `AI Orchestrator`, `Conversation Service`);
   - correlation id по чату/сообщению.

3. **Технический мониторинг:**
   - алерты по:
     - недоступности каналов;
     - резкому росту ошибок AI‑провайдера;
     - неожиданным всплескам трафика.

**Готовность фазы:** можно понять, как живёт фича в проде, где что падает и как работает AI относительно людей.

---

### Краткий чек‑лист от точки A до точки B

1. **A:** нет омниканального AI‑модуля.
2. **После Фазы 1–3:** единый чат‑центр с ручной обработкой через админку.
3. **После Фазы 4:** AI умеет автоотвечать/подсказывать по правилам и данным бизнеса.
4. **После Фазы 5–6:** безопасная работа с ключами, несколько каналов, гибкие AI‑режимы.
5. **B:** продукционный AI‑омниканальный ассистент с логированием и управляемостью.

