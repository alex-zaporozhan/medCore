## DEV_PROMPT: Лента внимания владельца (AttentionFeed)

> Архитектура и контекст: `ARCH_ATTENTION_FEED.md`, `ARCH_CHAT_PATIENT_ADMIN.md`, `ARCH_DENTAL_BOOKING_01_DB_AND_STRUCTURE.md`.
> Цель: дать владельцу и старшим администраторам «панель совести» — операционный список следующих действий по клиентам (перезвонить, вернуть, разобраться с конфликтом), без отдельного модуля «заметок», опираясь на уже существующие данные.

---

### Общие правила для @DEV

- Двигаться по чек‑листу ниже **строго по порядку**, не смешивая несколько крупных пунктов в одном коммите.
- Не ломать существующий прод:
  - на этапе v1 **не создаём** отдельную таблицу `attention_items`;
  - новые флаги/поля в существующих таблицах должны иметь дефолты / быть nullable и не нарушать старые DTO.
- Источник правды по бизнес-логике — `ARCH_ATTENTION_FEED.md`. Этот DEV_PROMPT отвечает за **как реализовать**, не меняя сути.
- На v1 лента:
  - собирается **на лету** сервисом `AttentionFeedService` по `clinic_id`;
  - поддерживает явное закрытие только для follow‑up (обещали перезвонить);
  - для `retention_gap` и `conflict` элементы исчезают автоматически, когда условие перестаёт выполняться (пациент вернулся / конфликт снят).

Рекомендуемый порядок: сначала backend (сервис + DTO + API), затем admin‑UI, затем тесты/доработки.

---

### To‑dos (по шагам)

#### 1. Backend: DTO и сервис AttentionFeedService

1.1. **DTO AttentionItemRead и AttentionFeedRead (умный список дел)**

- В модуле DTO, например `src/application/dto/attention_feed_dto.py`, создать:

```python
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class AttentionItemRead(BaseModel):
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    kind: str  # "follow_up" | "retention_gap" | "conflict"
    title: str
    description: str
    priority: int
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    patient_full_name: str | None
    patient_phone: str
    patient_tags: list[str] = []
    status: str  # "open" | "done"
    assigned_admin_id: UUID | None = None
    assigned_admin_name: str | None = None
    has_comment: bool = False
    last_comment_preview: str | None = None
    conversation_id: UUID | None = None


class AttentionFeedRead(BaseModel):
    follow_up: list[AttentionItemRead]
    retention_gap: list[AttentionItemRead]
    conflicts: list[AttentionItemRead]
```

- Типы и поля выровнять с `ARCH_ATTENTION_FEED.md` (объект `AttentionItem` + обогащение данными пациента) и с бизнес‑решением: лента как умный список дел с `status`, назначением на админа и коротким комментарием/превью.

1.2. **Сервис AttentionFeedService**

- В `src/application/services/attention_feed_service.py` реализовать:

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


class AttentionFeedService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_feed(self, clinic_id: UUID) -> AttentionFeedRead:
        ...
```

- Внутри `get_feed`:
  - организовать три приватных метода:
    - `_build_follow_up_items(clinic_id: UUID) -> list[AttentionItemRead]`;
    - `_build_retention_gap_items(clinic_id: UUID) -> list[AttentionItemRead]`;
    - `_build_conflict_items(clinic_id: UUID) -> list[AttentionItemRead]`;
  - собрать результаты и вернуть `AttentionFeedRead`.

#### 2. Backend: источники данных и правила расчёта

2.1. **Follow‑up (обещали перезвонить)**

- Опираться на `chat_messages` и/или `bookings`:
  - проверить текущие сущности `ChatMessage` и `Booking`:
    - если уже есть поля `follow_up_at` / `follow_up_reason` / `follow_up_closed` — использовать их;
    - если нет — на v1 реализовать follow‑up **только через чат**:
      - добавить в `chat_messages` (через Alembic‑миграцию) nullable поля:
        - `follow_up_at TIMESTAMP WITH TIME ZONE NULL`,
        - `follow_up_closed BOOLEAN NOT NULL DEFAULT FALSE`,
        - `follow_up_reason TEXT NULL`.
      - обновить entity и DTO чата при необходимости.
- Логика включения в ленту:
  - выбирать сообщения с:
    - `clinic_id = :clinic_id`;
    - `follow_up_at IS NOT NULL`;
    - `follow_up_closed = FALSE`;
    - `follow_up_at <= now()` (v1 — только просроченные и «на сегодня»).
- Расчёт `priority`:
  - базовое значение 80;
  - повышать на +10, если пациент имеет флаг `"vip"` (см. 2.3) или выручка по пациенту выше порога (можно использовать агрегаты из отчётов, если уже есть).
- Формирование `AttentionItemRead`:
  - `id` — `chat_message.id`;
  - `kind` — `"follow_up"`;
  - `title` — короткий текст, например: `f"Перезвонить: {patient_name or patient_phone}"`;
  - `description` — `follow_up_reason` или выжимка из `body` сообщения;
  - `due_at` — `follow_up_at`;
  - `created_at` / `updated_at` — по сообщению;
  - `patient_full_name`, `patient_phone`, `patient_tags` — см. 2.3;
  - `status`:
    - `"open"`, если `follow_up_closed = FALSE`;
    - `"done"`, если `follow_up_closed = TRUE`;
  - `conversation_id` — id диалога пациента (по `conversation.patient_id`);
  - `assigned_admin_id` / `assigned_admin_name` — см. 2.5;
  - `has_comment` / `last_comment_preview` — см. 2.5.

2.2. **Retention gap (давно не были)**

- Источники: `bookings` + `patients`.
- Для клиники:
  - посчитать по пациентам:
    - `last_visit_at` — дата/время последнего завершённого/подтверждённого визита;
    - суммарную выручку `total_amount` по этому пациенту.
  - порог ретеншна:
    - взять из настроек клиники, если уже есть (`retention_threshold_months` или аналог);
    - если нет — использовать дефолт 6 месяцев (сделать константу в сервисе).
- В ленту попадают пациенты, у которых:
  - `last_visit_at IS NOT NULL`;
  - `now() - last_visit_at > threshold`;
  - `total_amount > 0`.
- Расчёт приоритета:
  - базово 60;
  - масштабировать по выручке и давности, например:
    - `priority = 60 + min(30, int(log10(total_amount + 1) * 5))`;
  - в v1 можно сделать простее: сортировать по `total_amount DESC` и просто вернуть top‑50.
- Формирование `AttentionItemRead`:
  - `id` — `patient.id` (уникально в связке `kind="retention_gap"` для DTO, не для БД);
  - `kind` — `"retention_gap"`;
  - `title` — `f"Давно не был: {patient_name or patient_phone}"`;
  - `description` — краткий текст с датой последнего визита и выручкой (для UI);
  - `due_at` — `None` (решение владельца когда вернуться — вручную);
  - `created_at` / `updated_at` — можно использовать `last_visit_at` или `utc_now()`; важно для сортировки в UI;
  - `status` — `"open"` (элементы пропадают автоматически, когда условие перестаёт выполняться);
  - `conversation_id`, `assigned_admin_id`, `assigned_admin_name`, `has_comment`, `last_comment_preview` — заполняются по тем же правилам, что и для follow‑up (см. 2.5), если есть активный диалог.

2.3. **Conflicts (жалобы / сложные клиенты) и флаги пациента**

- Проверить, есть ли сейчас модель флагов пациента:
  - если есть `patient_flags`/`patient.tags` — использовать её;
  - если нет — на v1 ограничиться:
    - поиск по тегам/типам сообщений в чате (например, `message_type="complaint"` или теги, если есть);
    - дополнительный nullable JSON/ARRAY‑поле `flags` в таблице `patients` добавлять **необязательно** на этом этапе.
- Логика включения в ленту:
  - пациенты, у которых за последние N дней (по умолчанию 30) есть:
    - сообщения с тегами/типами жалоб/негатива (`complaint`, `negative_feedback` и т.п.);
    - и/или флаг `"conflict"` / `"angry"` / `"no_show_often"`, если такие уже заведены.
- Расчёт `priority`:
  - базовое значение 90;
  - при наличии нескольких конфликтных сигналов можно поднимать до 100.
- Формирование `AttentionItemRead`:
  - `id` — `patient.id`;
  - `kind` — `"conflict"`;
  - `title` — `f"Конфликт/жалоба: {patient_name or patient_phone}"`;
  - `description` — короткое описание: тип жалобы, дата последнего инцидента;
  - `status` — `"open"` (элементы пропадают автоматически, когда флаги/жалобы гаснут);
  - `conversation_id`, `assigned_admin_id`, `assigned_admin_name`, `has_comment`, `last_comment_preview` — заполняются по тем же правилам, что и для follow‑up (см. 2.5), если есть активный диалог.

2.4. **Обогащение данными пациента и тегами**

- Для всех типов AttentionItem:
  - собрать множество пациентских `id` по итоговому списку;
  - одним запросом получить пациентов (через SQLAlchemy `select(Patient)`), как это уже делается в `ChatService.list_conversations_for_admin`;
  - `patient_tags`:
    - если есть текущая реализация флагов/тегов — отобразить их как строки;
    - если нет — на v1 оставить пустой список.

#### 2.5. Статус open/done, назначение на админа и короткий комментарий

- **Статус задачи (`status`)**:
  - для follow‑up:
    - `"open"`, если `follow_up_closed = FALSE`;
    - `"done"`, если `follow_up_closed = TRUE`;
  - для `retention_gap` и `conflict`:
    - всегда `"open"` в v1; элементы исчезают из ленты автоматически, когда исходные условия перестают выполняться.
- **Назначение на админа (`assigned_admin_id` / `assigned_admin_name`)**:
  - использовать уже существующее поле `Conversation.assigned_admin_id`:
    - по `patient_id` найти активный `Conversation` (если есть);
    - подставить `assigned_admin_id` в DTO AttentionItem;
    - `assigned_admin_name` можно получить одним запросом по таблице `admin_user` (по списку id) либо оставить `None`, если привязки нет.
  - это позволяет:
    - фильтровать ленту по «моим задачам»;
    - реализовать кнопки «Назначить себя» / «Снять назначение» через уже существующий эндпоинт `/admin/chat/conversations/{conversation_id}/assign`.
- **Короткий комментарий (`has_comment`, `last_comment_preview`)**:
  - отдельную таблицу «заметок» не вводим;
  - в v1 используем историю чата как источник комментариев:
    - по `conversation_id` можно взять последнее сообщение от администратора (или последнее сообщение определённого типа, если появится `message_type="internal_note"`);
    - `has_comment = True`, если такой комментарий найден;
    - `last_comment_preview` — первые N символов (`body[:120]`) этого сообщения без переносов строк.
  - UI будет подсвечивать карточки с `has_comment=True` и показывать превью, не дублируя хранение данных.

#### 3. Backend: действия «отметить выполненным» (v1 — только follow‑up)

3.1. **Закрытие follow‑up**

- Реализовать метод в `AttentionFeedService`:

```python
    async def close_follow_up(self, clinic_id: UUID, message_id: UUID) -> bool:
        ...
```

- Логика:
  - найти `ChatMessage` по `id`;
  - проверить:
    - совпадает `clinic_id`;
    - `follow_up_at IS NOT NULL`;
  - установить `follow_up_closed = True`, `updated_at = utc_now()`, сохранить через репозиторий;
  - вернуть `True` / `False`.

3.2. **Retentioн / Conflicts**

- В v1 **не добавлять** отдельную таблицу статусов для retention/conflicts.
- Кнопка «Отметить выполненным» в UI для этих типов:
  - может быть отключена или выполнять только навигацию (например, открыть карточку пациента/чат);
  - реальные статусы и snooze‑логика для них — отдельный этап после валидации ленты в бою.

#### 4. Backend: API для админки

4.1. **Маршруты**

- В `src/api/v1/routers` создать новый модуль, например `admin_attention_feed.py`, и зарегистрировать его в общем `api_router` admin‑части.
- Реализовать эндпоинты:
  - `GET /api/v1/admin/clinics/{clinic_id}/attention-feed`:
    - зависимости аутентификации/авторизации такие же, как в других admin‑роутах;
    - внутри создавать `AttentionFeedService(session)` и вызывать `get_feed(clinic_id)`;
    - возвращать `AttentionFeedRead`.
  - `POST /api/v1/admin/clinics/{clinic_id}/attention-feed/follow-up/{message_id}/close`:
    - вызывать `AttentionFeedService.close_follow_up(...)`;
    - возвращать `{ "ok": bool }`.

4.2. **Авторизация и ограничения**

- Проверка, что админ имеет доступ к `clinic_id`, как и в других admin‑роутах.
- Лимитировать количество элементов в каждой группе:
  - для `retention_gap` и `conflicts` — по умолчанию top‑50;
  - для `follow_up` — можно не ограничивать, либо также отсекать по разумному лимиту (например, 200).

#### 5. Frontend (admin‑UI): страница «Лента внимания»

5.1. **Типы и API‑клиент**

- В `frontend/src/api/types.ts`:
  - добавить интерфейсы `AttentionItem` и `AttentionFeed`:
    - поля выровнять с `AttentionItemRead` / `AttentionFeedRead`.
- В `frontend/src/api/client.ts` (или аналогичном файле API‑клиента):
  - добавить методы:
    - `getAttentionFeed(clinicId: string): Promise<AttentionFeed>`;
    - `closeFollowUp(clinicId: string, messageId: string): Promise<{ ok: boolean }>;`.

5.2. **Хук для загрузки ленты**

- Создать хук, например `useAttentionFeed(clinicId: string)` на базе React Query:
  - ключ запроса включает `clinicId`;
  - повторная загрузка по кнопке «Обновить» на странице.

5.3. **Страница/вкладка в админке**

- В admin‑части (примерно там же, где отчёты) создать страницу:
  - путь: `/admin/attention` или `/admin/reports/attention`;
  - заголовок: «Лента внимания».
- Макет:
  - три вертикальных блока/колонки:
    - «Обещали перезвонить» (follow_up);
    - «Давно не были» (retention_gap);
    - «Конфликты» (conflicts).
  - каждая карточка содержит:
    - имя + телефон пациента;
    - короткое описание (первые 1–2 строки `description`);
    - срок/дату (`due_at` или `last_visit_at` в описании);
    - бейдж приоритета (например, цвет/число).

5.4. **Экшены на карточке**

- Для `follow_up`:
  - кнопки:
    - «Открыть чат» → навигация в существующий admin‑чат по `conversation_id` (если получить его легко через API чата) или по `patient_id`;
    - «Создать запись» → переход к форме создания записи с предзаполненным пациентом;
    - «Отметить выполненным»:
      - вызывает `closeFollowUp` и по успеху обновляет ленту (invalidate query).
- Для `retention_gap` и `conflicts`:
  - минимум:
    - «Открыть карточку пациента»;
    - «Открыть чат» (если есть диалоги).
  - кнопку «Отметить выполненным» можно либо не показывать, либо отображать в неактивном состоянии с подсказкой, что статус автоматический (на v1).

5.5. **Фильтры и удобство для администратора**

- На странице добавить:
  - фильтр по типу (по умолчанию «Все типы»);
  - переключатель «Только просроченные follow‑up» (по умолчанию включён);
  - поиск по имени/телефону (фильтрация по уже загруженным данным).

#### 6. Тесты и проверка

6.1. **Backend**

- Unit/интеграционные тесты для `AttentionFeedService`:
  - кейс с несколькими follow‑up в прошлом и будущем (в ленту попадают только `follow_up_at <= now`);
  - кейс с пациентами с и без визитов для `retention_gap`;
  - кейс с жалобами/флагами для `conflicts`.
- Тесты API:
  - `GET /attention-feed` возвращает структуру согласно схеме;
  - `POST .../follow-up/{message_id}/close` меняет `follow_up_closed`.

6.2. **Frontend**

- Smoke‑тесты/ручная проверка:
  - загрузка страницы «Лента внимания» при наличии данных;
  - отображение трёх колонок;
  - работа кнопки «Отметить выполненным» для follow‑up (элемент исчезает из списка после обновления ленты).

---

### Завершение

По окончании выполнения этого DEV_PROMPT должно быть выполнено:

- Владелец и старший админ видят в админке отдельную ленту внимания по клинике с тремя типами элементов: follow‑up, retention gap, конфликты.
- Лента собирается **без отдельной таблицы attention_items**, на лету из `chat_messages` / `bookings` / `patients`.
- Follow‑up‑элементы управляемы: администратор может закрыть задачу, и она исчезает из ленты.
- Для retention/conflicts владелец получает видимость по рисковым клиентам; дальнейшее развитие (ручные статусы, snooze, интеграция с AI‑оператором) можно делать отдельным этапом.

