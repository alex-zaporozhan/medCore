# ARCH_CHAT_PATIENT_ADMIN — Архитектура модуля чата пациент ↔ администрация

**Проект:** Dental Booking System MVP  
**Режим:** SAAS  
**Назначение документа:** детализировать БД, API и меры безопасности для внутреннего чата между пациентом и администрацией, чтобы @DEV мог реализовать модуль без уточнений, а также подготовить почву для ленты внимания и AI‑оператора (см. `ARCH_ATTENTION_FEED.md`, `ARCH_CHAT_AI_OPERATOR.md`).

---

## 1. Режим и стек

Режим и стек совпадают с основным проектом (см. `ARCH_DENTAL_BOOKING_01_DB_AND_STRUCTURE.md`, `STACK_SELECTION.md`):

- **Режим:** SAAS, одна клиника на инстанс (multi-tenancy за скобками MVP, но в таблицах сохраняем `clinic_id` для будущего роста).
- **Backend:** Python + FastAPI.
- **Frontend:**
  - Веб-админка: TypeScript + React.
  - PWA пациента: TypeScript + React.
- **БД:** PostgreSQL.

Почему: стек уже принят для всего продукта; чат — ещё один модуль внутри существующей архитектуры (Clean Architecture, слои `domain` / `application` / `infrastructure` / `interfaces`).

---

## 2. Цели и контекст

**Цель:** дать клинике **внутренний безопасный чат** пациент ↔ администрация, который становится основой:

- для ведения диалога по записям и оплатам;
- для **ленты внимания** (обещали перезвонить, конфликты, давно не были);
- для **AI‑оператора**, который умеет суммаризировать диалоги и предлагать ответы.

Основные свойства:

- Один диалог на пациента на клинику.
- Несколько администраторов могут одновременно работать с разными диалогами.
- Есть назначение диалога на конкретного администратора (кто «ведёт» чат).
- История сообщений хранится и доступна в карточке пациента.

**Безопасность (запрос пользователя):**

- **Безопасный закрытый контур для внутреннего использования клиникой**:
  - HTTPS для всего трафика.
  - Авторизация пациента (по телефону/SMS, существующий механизм) и администратора (логин/пароль, сессия/токен).
  - Жёсткая изоляция по `clinic_id`: пациент видит только свой диалог с клиникой, админ — только диалоги своей клиники.
  - Данные хранятся в инфраструктуре клиники/хостинга.
- **Без лицензии на СКЗИ / отдельные крипто‑модули.**
- Текст сообщений хранится в БД **как есть**; защита достигается организационными и инфраструктурными мерами (периметр, доступы, HTTPS, разграничение прав).

---

## 3. Схема БД для чата

Новые таблицы: `conversations`, `chat_messages`.

### 3.1 Таблица `conversations`

Один диалог пациент ↔ клиника. Все сообщения между конкретным пациентом и клиникой живут в одном `conversation`.

**Поля:**

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)`
- `patient_id UUID NOT NULL FK → patients(id)`
- `assigned_admin_id UUID NULL FK → admins(id)` — администратор, который «ведёт» диалог; может быть `NULL` (диалог никому не назначен).
- `last_message_at TIMESTAMPTZ NULL` — время последнего сообщения в диалоге.
- `last_message_sender_type TEXT NULL` (`patient`|`admin`|`system`) — кто отправил последнее сообщение.
- `unread_by_admin_count INT NOT NULL DEFAULT 0` — количество непрочитанных сообщений от пациента (для фильтра «без ответа» и индикаторов).
- `unread_by_patient_count INT NOT NULL DEFAULT 0` — непрочитанные для пациента сообщения от админов/системы.
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `deleted_at TIMESTAMPTZ NULL`

**Ограничения:**

- `UNIQUE (clinic_id, patient_id)` — один активный диалог на пациента на клинику.  
  При необходимости в будущем поддержать несколько диалогов (по записи/booking) — добавлять новое поле `booking_id` и снимать этот UNIQUE или делать его условным.

**Индексы:**

- `idx_conversations_clinic_patient (clinic_id, patient_id)` — быстрый поиск диалога для пациента.
- `idx_conversations_clinic_last_message (clinic_id, last_message_at DESC)` — сортировка списка диалогов по дате последнего сообщения.
- `idx_conversations_assigned_admin (assigned_admin_id, last_message_at DESC)` — выборка диалогов, назначенных конкретному админу.
- `idx_conversations_clinic_unread_admin (clinic_id, unread_by_admin_count)` — фильтры/статистика по непрочитанным (без partial index, для простоты).

### 3.2 Таблица `chat_messages`

Отдельная запись для каждого сообщения внутри диалога.

**Поля:**

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)` — денормализация для фильтров/отчётов по клинике.
- `conversation_id UUID NOT NULL FK → conversations(id)`
- `patient_id UUID NULL FK → patients(id)` — для удобства запросов/аудита; дублирует `conversations.patient_id`.
- `admin_id UUID NULL FK → admins(id)` — отправитель‑администратор (если сообщение от админа).
- `sender_type TEXT NOT NULL` (`patient`|`admin`|`system`)
- `body TEXT NOT NULL` — текст сообщения (хранится в открытом виде в рамках закрытого контура).
- `read_by_admin_at TIMESTAMPTZ NULL` — когда админ (любой из администраторов клиники) прочитал сообщение пациента.
- `read_by_patient_at TIMESTAMPTZ NULL` — когда пациент прочитал сообщение от админа/системы.
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `deleted_at TIMESTAMPTZ NULL`

**Индексы:**

- `idx_chat_messages_conversation_created_at (conversation_id, created_at)` — подгрузка истории по диалогу, пагинация по времени.
- `idx_chat_messages_clinic_created_at (clinic_id, created_at)` — при необходимости отчёты/аудит по клинике.

**Связь с существующими сущностями:**

- Все запросы делаются в контексте текущей клиники (одна клиника на инстанс, но `clinic_id` сохраняем для единообразия и возможной мультиклиники).
- Логика домена:
  - При создании сообщения:
    - обновляем `conversations.last_message_at`, `last_message_sender_type`;
    - инкрементируем `unread_by_admin_count` или `unread_by_patient_count` в зависимости от `sender_type`.
  - При отметке «прочитано»:
    - проставляем `read_by_*_at` в сообщениях;
    - декрементируем соответствующий `unread_*_count` в `conversations`.

---

## 4. Меры безопасности: закрытый контур

Цель: **безопасный закрытый контур для внутреннего использования клиникой**, без отдельной лицензии на шифрование (СКЗИ).

### 4.1 Транспорт и периметр

- Все эндпоинты чата доступны только по **HTTPS** (соответствует общей архитектуре проекта).
- Backend и БД размещены в инфраструктуре провайдера/клиники в РФ (см. `ARCH_PWA_PATIENT_APP.md`).

### 4.2 Авторизация и изоляция по клинике

- **Пациент:**
  - Аутентификация как в основном приложении (по телефону/SMS + токен).
  - `clinic_id` пациента задаётся по его записи/профилю и не может быть изменён клиентом.
- **Администратор:**
  - Логин/пароль, привязка к `clinic_id` (см. таблицу `admins`).

Все запросы к БД выполняются **только с фильтром по `clinic_id` из контекста аутентификации**, а не из входных данных клиента.  
ID сущностей (`conversation_id`, `message_id`) проверяются на принадлежность к текущей клинике.

### 4.3 Доступ к данным чата

- Пациент:
  - Имеет доступ только к **своему** диалогу (`conversation` по `patient_id` в рамках `clinic_id`).
  - Не может запрашивать чужие `conversation_id`.
- Администратор:
  - Имеет доступ ко **всем диалогам** своей клиники (`clinic_id` совпадает).

### 4.4 Хранение данных

- Поля `body` в `chat_messages` хранятся в виде обычного текста.
- Защита от утечек реализуется за счёт:
  - контролируемого доступа к БД и бэкапам (организационные меры, DevOps‑политика);
  - доступа к чату только через авторизованные интерфейсы;
  - HTTPS и отсутствия открытых анонимных эндпоинтов.

При изменении регуляторики/требований возможно добавить **шифрование при хранении** (прозрачное для клиента) в отдельной фазе, без изменения доменной модели.

---

## 5. API: контракты для чата

Версионирование: все пути начинаются с `/api/v1/`.

### 5.1 Общие принципы

- Все эндпоинты требуют авторизацию (пациентский токен или админская сессия).
- На входе принимаем только **фильтры и параметры**, а не `clinic_id`/`patient_id` — их берём из контекста аутентификации.
- Ответы содержат только поля, которые нужны интерфейсу (см. BIZ‑план).

Ниже — целевые контракты на уровне DTO, без деталей реализации FastAPI.

### 5.2 API для пациента

Базовый префикс: `/api/v1/patient/chat`.

#### 5.2.1 Получить (или создать) диалог пациента с клиникой

- **GET** `/api/v1/patient/chat/conversation`
- **Логика:**
  - По `patient_id` и `clinic_id` ищем `conversation`.
  - Если нет — создаём новый (`unread_*_count = 0`).
- **Ответ (200):**
  - `conversation_id: string`
  - `unread_by_patient_count: number`
  - `unread_by_admin_count: number`
  - `last_message_at: string | null`

#### 5.2.2 Список сообщений диалога

- **GET** `/api/v1/patient/chat/conversation/messages`
- **Параметры запроса (query):**
  - `cursor` (опционально) — ID последнего сообщения, для пагинации «истории вверх» или «обновления вниз» (детали реализации — на уровне @DEV).
  - `limit` (опционально, по умолчанию 50, максимум 200).
- **Ответ (200):**
  - `items: MessageDto[]`
  - `next_cursor: string | null`

Где `MessageDto`:

- `id: string`
- `sender_type: "patient" | "admin" | "system"`
- `body: string`
- `created_at: string`
- `is_mine: boolean` — клиентский флаг (можно считать на бэке как `sender_type === "patient"`).

#### 5.2.3 Отправка сообщения от пациента

- **POST** `/api/v1/patient/chat/conversation/messages`
- **Тело запроса:**
  - `body: string` (ограничение по длине, например 2000 символов; валидация на бэке).
- **Логика:**
  - Находим/создаём `conversation` (как в 5.2.1).
  - Создаём `chat_messages` с `sender_type = "patient"`.
  - Увеличиваем `unread_by_admin_count`.
  - Обновляем `last_message_at`, `last_message_sender_type`.
  - При необходимости вызываем `NotificationService` (см. 6.2).
- **Ответ (201):**
  - `message: MessageDto` (созданное сообщение).

#### 5.2.4 Отметить сообщения как прочитанные пациентом

- **POST** `/api/v1/patient/chat/conversation/mark-read`
- **Тело запроса (опционально):**
  - `up_to_message_id: string | null` — до какого сообщения отметить «прочитано» (если `null`, значит все).
- **Логика:**
  - Ставим `read_by_patient_at` для сообщений, отправленных админами/системой.
  - Сбрасываем/уменьшаем `unread_by_patient_count` в `conversations`.
- **Ответ (204)** — без тела.

### 5.3 API для администратора

Базовый префикс: `/api/v1/admin/chat`.

#### 5.3.1 Список диалогов

- **GET** `/api/v1/admin/chat/conversations`
- **Параметры запроса (query):**
  - `filter` (опционально): `"all" | "mine" | "unassigned"`:
    - `all` — все диалоги клиники.
    - `mine` — диалоги с `assigned_admin_id = current_admin`.
    - `unassigned` — диалоги с `assigned_admin_id IS NULL`.
  - `search` (опционально): строка для поиска по имени/телефону пациента (делегируется в join c `patients`).
  - `limit`, `offset` (пагинация).
- **Ответ (200):**
  - `items: AdminConversationListItemDto[]`
  - `total: number`

`AdminConversationListItemDto`:

- `conversation_id: string`
- `patient_id: string`
- `patient_name: string | null`
- `patient_phone: string`
- `assigned_admin_id: string | null`
- `assigned_admin_name: string | null`
- `last_message_at: string | null`
- `last_message_sender_type: "patient" | "admin" | "system" | null`
- `unread_by_admin_count: number`

#### 5.3.2 История сообщений диалога (админ)

- **GET** `/api/v1/admin/chat/conversations/{conversation_id}/messages`
- **Параметры запроса (query):**
  - `cursor`, `limit` — аналогично пациентскому API.
- **Ответ (200):**
  - `items: MessageDto[]`
  - `next_cursor: string | null`

#### 5.3.3 Отправка сообщения от администратора

- **POST** `/api/v1/admin/chat/conversations/{conversation_id}/messages`
- **Тело запроса:**
  - `body: string`
- **Логика:**
  - Проверка, что `conversation` принадлежит текущей клинике.
  - Создание `chat_messages` с `sender_type = "admin"`, `admin_id = current_admin`.
  - Увеличение `unread_by_patient_count`.
  - Обновление `last_message_at`, `last_message_sender_type`.
- **Ответ (201):**
  - `message: MessageDto`.

#### 5.3.4 Назначение диалога на администратора

- **POST** `/api/v1/admin/chat/conversations/{conversation_id}/assign`
- **Тело запроса:**
  - `admin_id: string | null` — если `null`, снять назначение; если не передан, по умолчанию **назначить на текущего администратора**.
- **Логика:**
  - Проверка доступа по `clinic_id`.
  - Обновление поля `assigned_admin_id`.
- **Ответ (200):**
  - `conversation_id: string`
  - `assigned_admin_id: string | null`

#### 5.3.5 Отметить сообщения как прочитанные администратором

- **POST** `/api/v1/admin/chat/conversations/{conversation_id}/mark-read`
- **Тело (опционально):**
  - `up_to_message_id: string | null`.
- **Логика:**
  - Обновление `read_by_admin_at` для сообщений пациента.
  - Сброс/изменение `unread_by_admin_count` в `conversations`.
- **Ответ (204)**.

---

## 6. Интеграция с NotificationService и реал-тайм

### 6.1 Реал-тайм (выбор)

Для MVP модуля чата:

- **Выбор:** использовать **polling/long-polling** (клиент периодически запрашивает новые сообщения через `GET .../messages?cursor=...`).
- Причины:
  - не требует отдельной инфраструктуры (WebSocket‑сервер, sticky‑sessions и т.п.);
  - достаточно для нагрузки и SLA стоматологической клиники;
  - упрощает отладку и развёртывание.

В будущем возможно вынести выбор WebSocket/SSE в отдельный ADR, если появится требование к «почти мгновенной» доставке и индикаторам набора текста.

### 6.2 NotificationService (точки расширения)

Хуки для существующего `NotificationService` (см. `notifications` и `NotificationSender`):

- **Новое сообщение от пациента:**
  - Событие: `ChatMessageCreated(sender_type="patient")`.
  - Действие (опционально в первой версии):
    - отправка уведомления в Telegram‑бот администраторов (шаблон `chat_new_message_patient`);
    - либо в интерфейсе админки обновляется счётчик непрочитанных за счёт polling.
- **Новое сообщение от админа:**
  - Событие: `ChatMessageCreated(sender_type="admin")`.
  - Действие: при необходимости — уведомить пациента через выбранный канал (`sms`/`telegram`/`email`), но для минимального варианта достаточно, чтобы пациент увидел сообщение при следующем входе.

Конкретные шаблоны/каналы могут быть добавлены в `notifications` как отдельная задача.

---

## 7. Встраивание в структуру backend

Продолжаем существующую Clean Architecture (см. раздел 2 в `ARCH_DENTAL_BOOKING_01_DB_AND_STRUCTURE.md`).

Предлагаемое размещение:

```text
src/
  domain/
    entities/
      conversation.py
      chat_message.py
    interfaces/
      repositories/
        conversation_repository.py
        chat_message_repository.py

  application/
    dto/
      chat_dto.py                # DTO для MessageDto, AdminConversationListItemDto и т.п.
    services/
      chat_service.py            # Бизнес-логика: создание сообщений, mark-read, назначение админа, подсчёт unread

  infrastructure/
    repositories/
      conversation_repo_impl.py
      chat_message_repo_impl.py

  interfaces/
    api/
      admin/
        chat_routes.py           # реализация эндпоинтов /api/v1/admin/chat/...
      patient/
        chat_routes.py           # реализация эндпоинтов /api/v1/patient/chat/...
```

Миграции для `conversations` и `chat_messages` добавляются в стандартном для проекта виде (Alembic).

---

## 8. Коды ошибок и валидация (кратко)

Базовые случаи, которые должен обработать @DEV:

- `400 Bad Request`:
  - Пустое/слишком длинное `body` сообщения.
- `401 Unauthorized`:
  - Отсутствие/некорректный токен пациента или админа.
- `403 Forbidden`:
  - Попытка админа/пациента получить доступ к диалогу другой клиники.
- `404 Not Found`:
  - `conversation_id` не существует или помечен `deleted_at` (для админских API).
- `409 Conflict`:
  - Редкие случаи конкурентного создания диалога (два запроса одновременно) — при нарушении `UNIQUE (clinic_id, patient_id)` на уровне БД нужно корректно обработать конфликт и перечитать диалог.

---

## 9. Критерии готовности для @DEV

Модуль считается спроектированным, если:

- Схема таблиц `conversations` и `chat_messages` реализуема без дополнительных вопросов (есть поля, типы, связи и индексы).
- Эндпоинты из раздела 5 покрывают все сценарии из `BIZ_PLAN_CHAT_PATIENT_ADMIN.md`:
  - пациент пишет/читает в одном диалоге;
  - администратор видит список диалогов, открывает чат, пишет и помечает прочитанным;
  - есть назначение диалога на администратора.
- Требование «безопасный закрытый контур без лицензии на шифрование» отражено через:
  - обязательный HTTPS;
  - изоляцию по `clinic_id`;
  - доступ только авторизованным пациентам и администраторам.

