# Промпты @DEV: Omni Agent Workstation (исполняемая дорожная карта)

> **Роль:** @DEV  
> **Основание:** `ARCH_OMNI_AGENT_WORKSTATION_2026.md` (§3 OutboundPolicy, §5 безопасность, §6 SSE, §10 инвариант)  
> **Правила:** один PR на один крупный блок по возможности; тесты + линтер; **не** смешивать `admin/chat` с `admin/omni-chats` без отдельной задачи.

**Связь с @LEAD:** закрытие **P0-A + P0-B** = минимум для честного «оператор может работать в омниканале» (GATE-2 по фиче + основа под GATE-6/E2E-сетку «омниканал» в `docs/LEAD_PRODUCT_GATE_PROTOCOL.md`). Антигалочка: `docs/LEAD_ANTI_CHECKBOX_PROTOCOL.md` — отчёт без тестов/строк файла не принимается.

---

## Порядок внедрения (не переставлять без причины)

1. **P0-A** — исходящий канал (OutboundPolicy) + `sender_admin_id` + API + OpenAPI + тесты + минимальный UI канала.  
2. **P0-B** — история ленты (`before`) + merge + UX скролла.  
3. **P0-H** — rate limit на `POST .../messages` (сразу после зелёного P0-A, см. ниже).  
4. **P1-A** — SSE + fallback.  
5. **P1-B** — assignee + PATCH + «мои диалоги».  
6. **P2** — макросы, навигация/legacy.

---

## Сводная таблица backlog (возможность → результат)

| ID | Возможность | Эталон / смысл | RBAC / API | Приоритет |
|----|-------------|----------------|------------|-----------|
| P0-A | Ответ в **верный** канал | Last CLIENT inbound | `reply_channel_id` + tenant + тип канала исходящий | **Must** |
| P0-A | Кто отправил | Аудит | `sender_admin_id` в БД и DTO | **Must** |
| P0-B | Полная история | Zendesk / Intercom | `GET .../messages?before=` + merge | **Must** |
| P0-H | Защита от флуда | 429 | Лимитер на POST messages | **Must** (после P0-A) |
| P1-A | Лента без F5 | SSE | JWT + событие без content | **Should** |
| P1-B | Очередь | Назначение | PATCH + фильтр | **Should** |
| P2 | Макросы / меню | Живые данные | CRUD + routePaths | **Could** |

---

## Маппинг на ворота (для @LEAD / ретроспективы)

| Пакет | Ворота | Доказательство |
|-------|--------|----------------|
| P0-A + P0-B | Контракт исполнен, оператор видит историю и шлёт в верный канал | pytest + eslint; ручной сценарий длинного треда |
| P0-H | Эксплуатационный минимум | 429 в тесте или интеграция с существующим limiter |
| P1-A | Realtime без поломки ленты | Тест события / ручной чек |
| P1-B | Очередь по BIZ | Тест изоляции tenant на assignee |

---

## P0-A — OutboundPolicy + аудит (Must)

### Промпт (скопировать в задачу)

```
Реализуй ARCH_OMNI_AGENT_WORKSTATION_2026.md §3 OutboundPolicy для POST /v1/admin/omni-chats/{chat_id}/messages.

1. DTO SendOmniMessageRequest: опциональное поле reply_channel_id (UUID). Обнови OpenAPI/схемы Pydantic и описание кодов ответа (404 / 400 / 409 / 201) согласно §3 таблица HTTP в ARCH.

2. Алгоритм канала (строго порядок):
   - если reply_channel_id задан — загрузить OmniChannel по id и clinic_id == current_admin.clinic_id; иначе 400;
   - проверить канал допускает исходящие (та же логика/список типов, что у OmnichannelOutboundDispatcher); иначе 400 с detail;
   - иначе — последнее сообщение чата: INBOUND + actor_type CLIENT, order by created_at DESC → channel_id;
   - иначе — chat.channel_id;
   - если канал не определён — 409 с кодом/ detail как в ARCH (OMNI_REPLY_CHANNEL_UNRESOLVED или эквивалент).

3. append_outbound_message(..., channel_id=resolved_id). Миграция: omni_messages.sender_admin_id nullable FK → admin_users; для HUMAN_ADMIN заполнять current admin id.

4. OmnichannelOutboundDispatcher.dispatch_to_channel(msg) с resolved channel_id на созданной записи.

5. Ответ 201: OmniMessageDto с channel_id (или эквивалент в DTO), channel_type, sender_admin_id, id, created_at, остальные поля по контракту.

Тесты pytest (обязательно в CI):
- два канала в одном чате: два inbound с разным channel_id — POST без reply_channel_id → исходящее с channel_id последнего CLIENT inbound; при необходимости замокать dispatch, но резолв канала и FK — реальные;
- reply_channel_id другой клиники или несуществующий — 400;
- нет канала для ответа (синтетический сценарий) — 409;
- tenant: как в tests/api/test_admin_omni_chat.py (изоляция clinic_id).

Логи: не писать content сообщения в INFO (см. ARCH §5).
```

### Definition of Done

- [ ] Миграция Alembic для `sender_admin_id`.  
- [ ] Поведение и коды HTTP совпадают с §3 и таблицей в `ARCH_OMNI_AGENT_WORKSTATION_2026.md`.  
- [ ] OpenAPI / схемы ручки обновлены.  
- [ ] Минимум **4** осмысленных теста (два канала, чужой канал/клиника, 409, tenant) в `tests/api/` или `tests/services/`.  
- [ ] Фронт: `AdminOmniChatPage` — **виден канал отправки** до submit: либо текст «Ответ в: {label}», либо Select при нескольких каналах клиники (данные с бэка или вычисленный default; при явном выборе — передать `reply_channel_id`).  
- [ ] Нет регрессии: `pytest tests/api/test_admin_omni_chat.py` зелёный.

### Не входит в P0-A

- SSE; SLA; макросы; rate limit (отдельно P0-H).

---

## P0-B — История ленты (Must)

### Промпт

```
Реализуй подгрузку старых сообщений на AdminOmniChatPage по ARCH §7.

1. useAdminOmniChat (messages): infinite query или явный loadOlder с параметром before (UUID последнего «верхнего» загруженного сообщения согласно API).
2. UI: кнопка «Ранее» над лентой или intersection observer у верхнего края при scrollTop < threshold; сохранять позицию скролла после подгрузки (не прыгать вниз без необходимости).
3. Merge: ключ message.id, порядок хронологический asc, без дубликатов.
4. refetchInterval для **сообщений** не увеличивать; список чатов может остаться 5s.

Тест: vitest на mergeMessagesById(prev, incoming) или эквивалент по соглашению репозитория.
```

### Definition of Done

- [ ] При количестве сообщений > limit одной страницы оператор **дочитывает** начало переписки.  
- [ ] Нет дубликатов id при merge и после invalidateQueries.  
- [ ] `npx eslint` на затронутых файлах без новых ошибок.

---

## P0-H — Rate limit (Must, сразу после P0-A)

### Промпт

```
Реализуй лимит на POST /v1/admin/omni-chats/{chat_id}/messages с ответом 429 и стабильным detail согласно ARCH §5.

1. Найти существующий rate limiter в src/infrastructure (или общий middleware для admin).
2. Если инфраструктуры нет — минимальная реализация согласованная с @ARCH (in-memory per admin id + окно времени) с пометкой tech debt в комментарии и задачей на Redis при масштабировании.
3. Тест: запрос сверх лимита → 429 (или документированный e2e-ручной чек + unit на счётчик).
```

### Definition of Done

- [ ] Лимит включён для POST messages.  
- [ ] Документировано в коммите/описании PR значение лимита (например 30/мин).

---

## P1-A — SSE (Should)

### Промпт

```
Реализуй SSE по ARCH_OMNI_AGENT_WORKSTATION_2026.md §6.

1. GET /v1/admin/omni-chats/stream (или /events) — авторизация как у admin routes; события только для clinic текущего admin (clinic_id в payload для клиентской фильтрации).
2. Событие: type message.created, chat_id, message_id, clinic_id — без content.
3. После события — invalidateQueries для сообщений открытого чата.
4. Fallback: при ошибке EventSource — refetch открытого чата 10–15s и/или кнопка «Обновить».

Disconnect on unmount; не открывать SSE вне страницы омника.
```

### Definition of Done

- [ ] Новое сообщение в открытом чате без ручного F5.  
- [ ] В событии нет текста сообщения.  
- [ ] Тест: формат события или handler (по возможностям проекта).

---

## P1-B — Назначение и очередь (Should)

### Промпт

```
Миграция: omni_chats.assignee_admin_id nullable FK.
PATCH /v1/admin/omni-chats/{id}: body { assignee_admin_id?: uuid | null, status?: string } с RBAC — зафиксировать permission в rbac_matrix.py.
GET list: query assignee=me для фильтра «мои диалоги».
Фронт: бейдж/имя в списке, фильтр «Только мои».
```

### Definition of Done

- [ ] Назначение сохраняется и видно после перезагрузки.  
- [ ] Тест: другая клиника не видит чужие назначения.

---

## P2 — Макросы (Could) — только «живые»

### Промпт

```
Таблица omni_quick_replies (clinic_id, title, body, sort_order, created_at).
CRUD admin API под RBAC.
Фронт: Select/Menu у composer — вставка body в поле; без API не считать done.
```

### Definition of Done

- [ ] Данные в БД, не в коде.  
- [ ] Редактирование защищено правом.

---

## P2 — Маршруты и legacy (Could)

### Промпт

```
Проверь routePaths и AdminLayout: клиентский омниканал → /admin/omni-chat (или актуальный путь); staff internal chat — отдельно.
Комментарий в routePaths.ts + при необходимости строка в README.
```

---

## Регрессия (каждый PR к омничату)

```bash
poetry run pytest tests/api/test_admin_omni_chat.py -q --tb=short
```

При изменении изоляции tenant:

```bash
poetry run pytest tests/api/test_tenant_isolation_admin_paths.py -q --tb=short
```

Фронт:

```bash
cd frontend && npx eslint src/admin/pages/AdminOmniChatPage.tsx src/hooks/useAdminOmniChat.ts
```

**Ручная проверка:** смена клиники в селекторе не показывает чаты и сообщения другой клиники.

**E2E (если есть в CI):** прогон сценария омника при наличии теста в `tests/e2e/` — после P0 не ломать.

---

## Инвариант «один открытый чат на контакт» (техдолг, согласовать с @ARCH)

Если в коде возможны два OPEN чата на `(clinic, contact)` — завести задачу: уникальный индекс или атомарность `get_or_create_chat` + тест гонки. Ссылка: `ARCH_OMNI_AGENT_WORKSTATION_2026.md` §10.

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-03-25 | Первая версия P0–P2 |
| 2026-03-25 | @QA_ARCH: порядок, DoD, таблица backlog, §3 OutboundPolicy, фронт канала, hardening |
| 2026-03-25 | @LEAD: таблица HTTP/OpenAPI; P0-H rate limit обязателен; маппинг ворот; регрессия tenant; инвариант чата; усиленные DoD и тесты |
