# DEV PROMPTS: Реализация пунктов ARCH Review (омниканальный ассистент)

> Пошаговая реализация для @DEV по документу `ARCH_AI_ASSISTANT_OMNICHANNEL_REVIEW.md`.  
> Выполнять в порядке блоков; внутри блока — по шагам.

---

## Общие правила

- Менять только затронутые файлы; не переписывать лишнее.
- После каждого блока — прогнать релевантные тесты (указаны в блоке).
- Все новые эндпоинты — под тем же префиксом и авторизацией, что существующие Owner/Admin API.

---

## Блок 1. Идемпотентность входящих сообщений (Must)

**Цель:** При повторной доставке вебхука с тем же `external_message_id` для того же чата не создавать дубликат сообщения и не вызывать AI.

### Шаг 1.1. Репозиторий сообщений — проверка дубликата

**Файл:** `src/domain/interfaces/repositories/omnichannel_chat_repository.py`

- Добавить абстрактный метод в `MessageRepository`:

```python
@abstractmethod
async def exists_by_chat_and_external_id(
    self,
    chat_id: UUID,
    provider: str,
    external_message_id: str,
) -> bool:
    """Return True if an INBOUND message already exists with this chat_id and source_metadata (provider, external_message_id)."""
    ...
```

**Файл:** `src/infrastructure/database/omnichannel_chat_repo_impl.py`

- Реализовать `exists_by_chat_and_external_id`:
  - Запрос к `Message` где `chat_id == chat_id`, `direction == "INBOUND"`, и в `source_metadata` поле `provider` равно `provider`, `external_message_id` равно `external_message_id`.
  - В PostgreSQL с JSONB: `Message.source_metadata["provider"].astext == provider` и `Message.source_metadata["external_message_id"].astext == external_message_id`. Либо использовать `func.jsonb_extract_path_text(Message.source_metadata, 'provider') == provider` и то же для `external_message_id`.
  - Вернуть `True` если такой строки хотя бы одна (например, `select(1).where(...).limit(1)`, затем `result.scalar_one_or_none() is not None`).

### Шаг 1.2. Сервис чата — метод проверки перед созданием

**Файл:** `src/application/services/omnichannel_chat_service.py`

- Добавить метод (для использования из gateway):

```python
async def exists_inbound_by_external_id(
    self,
    chat_id: UUID,
    provider: str,
    external_message_id: str,
) -> bool:
    """True if inbound message with this external id already exists in chat."""
    return await self.messages.exists_by_chat_and_external_id(
        chat_id=chat_id, provider=provider, external_message_id=external_message_id
    )
```

### Шаг 1.3. Integration Gateway — проверка перед созданием сообщения

**Файл:** `src/application/services/integration_gateway_service.py`

- В `handle_inbound_normalized_message` после получения `chat` (после `get_or_create_chat`) и **до** вызова `create_inbound_message`:
  - Вызвать `exists = await self.chat_service.exists_inbound_by_external_id(chat.id, dto.provider, dto.external_message_id)`.
  - Если `exists` — залогировать `"duplicate inbound message, skipping"` с `chat_id`, `provider`, `external_message_id`, затем `return` (не создавать сообщение, не вызывать AI).

### Шаг 1.4. Тест

- В `tests/api/test_integrations_gateway.py` (или отдельный тест): отправить два одинаковых webhook-запроса (один и тот же `external_message_id` для одного и того же чата). После второго в БД должно быть по-прежнему одно сообщение в этом чате с таким `source_metadata.external_message_id`.

**Готовность блока 1:** Повторная доставка вебхука не создаёт дубликат и не дергает AI.

---

## Блок 2. Фильтрация скрытых сообщений и DTO (Must)

**Цель:** По умолчанию в API не возвращать сообщения с `ui_hidden = true`; при необходимости показывать их с пометкой по флагу `include_hidden`.

### Шаг 2.1. Репозиторий — параметр `include_hidden`

**Файл:** `src/domain/interfaces/repositories/omnichannel_chat_repository.py`

- В методах `list_last_messages` и `list_messages_cursor` добавить опциональный параметр `include_hidden: bool = False`.
- Сигнатуры:
  - `list_last_messages(self, chat_id, limit, include_hidden: bool = False) -> list[Message]`
  - `list_messages_cursor(self, chat_id, limit, after_id=None, before_id=None, include_hidden: bool = False) -> list[Message]`

**Файл:** `src/infrastructure/database/omnichannel_chat_repo_impl.py`

- В обоих методах: базовое условие `select(Message).where(Message.chat_id == chat_id)`. Если `include_hidden is False`, добавить `.where(Message.ui_hidden == False)`. Если `True` — не фильтровать по `ui_hidden`.

### Шаг 2.2. Сервис чата — проброс параметра

**Файл:** `src/application/services/omnichannel_chat_service.py`

- В `list_messages` добавить параметр `include_hidden: bool = False` и передавать его в `list_last_messages` и в `list_messages_cursor`.

### Шаг 2.3. Admin API — query-параметр и ответ

**Файл:** `src/application/dto/omnichannel_chat_dto.py`

- В `OmniMessageDto` добавить поля: `ui_hidden: bool = False`, `hidden_reason: str | None = None` (опционально, для модераторов).

**Файл:** `src/api/v1/routers/admin_omni_chat.py`

- В эндпоинте `get_omni_chat_messages` добавить query-параметр `include_hidden: bool = Query(False, description="Include soft-hidden messages")`.
- Передавать `include_hidden` в `service.list_messages(..., include_hidden=include_hidden)`.
- При формировании `OmniMessageDto` заполнять `ui_hidden` и `hidden_reason` из сущности `Message`.

### Шаг 2.4. Тест

- Создать чат и сообщение, сделать soft-hide этого сообщения. Вызвать `GET .../messages` без параметра — скрытое сообщение не должно попадать в ответ. С `include_hidden=true` — должно попадать, с полем `ui_hidden: true`.

**Готовность блока 2:** В списке сообщений по умолчанию только не скрытые; при `include_hidden=true` возвращаются все, в DTO есть `ui_hidden` (и при необходимости `hidden_reason`).

---

## Блок 3. GET /owner/audit-log (Should)

**Цель:** Эндпоинт для Owner с выгрузкой записей `omni_audit_logs` с фильтрами и пагинацией.

### Шаг 3.1. Роутер и DTO

**Файл:** создать или расширить Owner API. Рекомендуется создать `src/api/v1/routers/owner_omni_audit.py`.

- DTO ответа (например `OwnerAuditLogEntryDto`): `id`, `business_account_id`, `actor_id`, `actor_type`, `action_type`, `target_type`, `target_id`, `meta` (dict — данные из колонки `metadata` сущности AuditLog, в API лучше назвать `meta`, чтобы не путать с HTTP-метаданными), `created_at`, `ip_address`, `user_agent`.
- Ответ списка: `items: list[OwnerAuditLogEntryDto]`, `total: int`.

### Шаг 3.2. Запрос к БД

- Выборка из `omni_audit_logs` (сущность `AuditLog`) с условиями:
  - `business_account_id == current_admin.clinic_id` (только своя клиника).
  - Опционально: `action_type` (query `type`), `actor_type` (query `actor`), `created_at >= from`, `created_at <= to` (query `from`, `to` в ISO или дата).
  - Сортировка по `created_at desc`.
  - Пагинация: `limit` (по умолчанию 50, макс 200), `offset` или `page`/`page_size`.

### Шаг 3.3. Эндпоинт

- `GET /api/v1/owner/audit-log` (или префикс роутера `/owner/audit-log` при подключении под `/api/v1`).
- Query-параметры: `type` (action_type), `actor` (actor_type), `from`, `to` (даты), `page`, `page_size` (или `limit`, `offset`).
- Зависимости: `get_session`, `get_current_admin` — как в других Owner-эндпоинтах.

### Шаг 3.4. Подключение роутера

**Файл:** `src/api/v1/router.py`

- Подключить новый роутер `owner_omni_audit` (или добавить эндпоинты в существующий owner-роутер).

### Шаг 3.5. Тест

- Создать запись в `omni_audit_logs` (например, через soft-hide сообщения или сохранение credentials). Вызвать `GET /owner/audit-log` с авторизацией Owner — в ответе должна быть эта запись; проверить фильтры по `type`, `actor`, датам.

**Готовность блока 3:** Owner может выгружать аудит с фильтрами и пагинацией.

---

## Блок 4. Уведомление админов при SUGGEST_ONLY (Should)

**Цель:** После сохранения черновика AI в режиме SUGGEST_ONLY уведомить админов (лента, telegram админам или лог — по возможностям проекта).

### Шаг 4.1. Вариант A: Логирование + опционально Telegram админам

**Файл:** `src/application/services/omnichannel_ai_orchestrator.py`

- В методе `_suggest_only` после `self.session.add(draft)` и `await self.session.flush()` (и после инкремента метрики):
  - Залогировать структурированно событие `"omni_ai_suggestion_created"` с `chat_id`, `message_id`, `business_account_id`.
  - Опционально: если в проекте есть способ отправить уведомление «всем админам клиники» или в один admin-chat (например, `settings.telegram_admin_chat_id`), вызвать его с текстом вида: «Новый черновик ответа AI в омниканальном чате. Chat ID: {chat_id}. Откройте раздел «Омниканальный чат» в админке.»

### Шаг 4.2. Вариант B: Интеграция с лентой внимания (если требуется)

- Если в проекте есть единая «лента внимания» для админов (например, `AttentionFeedService`) и туда можно добавить тип элемента «omni_ai_suggestion»:
  - Добавить в домен/сервис ленты поддержку нового типа (источник — omni_messages с `content_type=TEMPLATE` и `source_metadata.kind=ai_suggestion` по `business_account_id` / `chat_id`).
  - Это выходит за минимальный объём; можно оставить как следующий этап и в первом релизе ограничиться логированием и при необходимости одним telegram-уведомлением в admin-chat.

### Шаг 4.3. Реализация минимального уведомления (рекомендуется для шага 4.1)

- Импортировать `send_with_fallback` из `src.application.services.notification_service`.
- После сохранения черновика: сформировать короткий текст `message` и вызвать `await send_with_fallback(message=..., template="omni_ai_suggestion", chat_id=settings.telegram_admin_chat_id or None, ...)` в фоне (или синхронно, но не падать при ошибке — обернуть в try/except, логировать). Использовать `telegram_admin_chat_id` как получателя, если он задан, чтобы уведомление пришло в один «админский» чат.

**Готовность блока 4:** При появлении черновика AI операторы получают уведомление (лог и при наличии — telegram в admin-chat).

---

## Блок 5. Детекция «живой оператор» и эскалация (Should)

**Цель:** Если клиент явно просит живого оператора (ключевые фразы), перевести чат в `WAITING_FOR_OPERATOR`, ослабить/выключить AI и уведомить админов.

### Шаг 5.1. Эвристика по тексту

**Файл:** `src/application/services/omnichannel_ai_orchestrator.py` (или отдельный модуль `src/application/services/omnichannel_escalation.py`).

- Функция вида `_client_asks_for_operator(text: str) -> bool`:
  - Привести `text` к нижнему регистру, убрать лишние пробелы.
  - Список ключевых фраз/слов: например `["оператор", "живой человек", "менеджер", "позовите", "хочу поговорить с человеком", "соедините с оператором"]`. Проверять вхождение подстрок (или слов) в `text`.
  - Вернуть `True`, если хотя бы одна фраза найдена.

### Шаг 5.2. Вызов до или после LLM

**Файл:** `src/application/services/omnichannel_ai_orchestrator.py`, метод `handle_incoming_for_ai`.

- Сразу после получения `effective_settings` и проверки `ai_mode != DISABLED`, взять последнее входящее сообщение клиента (например, переданное `message` — это только что созданное входящее). Текст: `message.content`.
- Вызвать `if _client_asks_for_operator(message.content or ""):` тогда:
  - Установить `chat.status = "WAITING_FOR_OPERATOR"`.
  - Установить `chat.ai_mode = "SUGGEST_ONLY"` или `"DISABLED"` (на выбор продукта; в ARCH допускается SUGGEST_ONLY или DISABLED).
  - Сохранить изменения чата (`await self.session.flush()` или через сервис чата).
  - Вызвать уведомление админов (тот же механизм, что в блоке 4: лог + опционально telegram admin-chat) с текстом «Клиент запросил живого оператора в чате {chat_id}».
  - Сделать `return` (не вызывать LLM и не слать автоответ).

### Шаг 5.3. Тест

- Создать чат, отправить входящее сообщение с текстом «Хочу поговорить с оператором». Проверить, что в БД у чата `status == WAITING_FOR_OPERATOR` и `ai_mode` изменён; что запись в логах/уведомлении есть и что автоответ AI не отправлялся.

**Готовность блока 5:** Запрос живого оператора по фразам приводит к эскалации и уведомлению без автоответа.

---

## Блок 6. Исправление GET omni-ai-settings при пустом списке каналов (рефакторинг)

**Цель:** При отсутствии каналов не передавать в SQL условие с литералом `False`; явно не запрашивать CHANNEL-настройки.

**Файл:** `src/api/v1/routers/owner_omni_ai_settings.py`

- В `get_omni_ai_settings` после получения списка `channels`:
  - Если `not channels`: задать `channel_items = []`, не выполнять запрос к `OmniAISettings` для scope CHANNEL.
  - Если `channels`: выполнять текущий запрос `select(OmniAISettings).where(scope == "CHANNEL", scope_id.in_([c.id for c in channels]))`, затем строить `channel_items` как сейчас.
- Убрать из `where` выражение `... if channels else False`.

**Готовность блока 6:** При нуле каналов эндпоинт возвращает пустой `channels` без сомнительного условия в запросе.

---

## Блок 7. Ретраи при отправке в Telegram (Nice)

**Цель:** При 429/5xx или сетевой ошибке повторять отправку с backoff.

**Файл:** `src/application/services/omnichannel_outbound_dispatcher.py`

- В `_dispatch_telegram` обернуть вызов `client.post` в цикл: максимум 3 попытки (или 2 ретрая после первой неудачи).
- При исключении (httpx.HTTPStatusError для 429/5xx или сетевые ошибки): подождать `asyncio.sleep(1 * (2 ** attempt))` (1s, 2s), затем повторить. После последней попытки — залогировать и выйти.
- Успешный ответ или «ok: false» от Telegram — не ретраить (только логировать при «ok: false» как сейчас).

**Готовность блока 7:** Временные сбои Telegram не приводят к мгновенной потере сообщения без повтора.

---

## Блок 8. Документирование ограничения WebchatPushManager (Nice)

**Файл:** `src/application/services/webchat_push_manager.py`

- В docstring модуля или класса `WebchatPushManager` добавить предупреждение:
  - «При нескольких инстансах приложения long-poll на одном инстансе не получит событие от диспетчера на другом. Для горизонтального масштабирования необходимо заменить in-memory хранилище на Redis Pub/Sub (канал по chat_id или глобальный с payload chat_id).»

**Готовность блока 8:** Ограничение зафиксировано для будущей доработки.

---

## Порядок выполнения и тесты

| Порядок | Блок | Команда тестов (пример) |
|---------|------|--------------------------|
| 1 | Блок 1 — идемпотентность | `pytest tests/api/test_integrations_gateway.py -v -k telegram or webchat` |
| 2 | Блок 2 — ui_hidden | `pytest tests/api/test_admin_omni_chat.py -v` |
| 3 | Блок 3 — audit-log | `pytest tests/api/test_owner_omni_audit.py` (написать тест) |
| 4 | Блок 4 — notifyAdmins | Ручная проверка или тест создания черновика и проверки логов/уведомления |
| 5 | Блок 5 — эскалация | Тест в test_omnichannel или test_integrations_gateway |
| 6 | Блок 6 — пустой channels | `pytest tests/api/test_owner_omni_ai_settings.py -v` |
| 7 | Блок 7 — ретраи | Мок httpx: первая попытка 429, вторая 200 — сообщение должно уйти |
| 8 | Блок 8 — документ | — |

После всех блоков прогнать полный набор тестов омниканального модуля и смежных интеграций.
