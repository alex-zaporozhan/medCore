## План QA_ARCH: Lead‑logs routing + funnel (multitenant, enterprise‑ready MVP++)

### Зачем этот документ
Вы попросили:
- **строгую мультитенант‑изоляцию** по клиникам (никаких кросс‑клиник данных на странице лидов)
- **полную автоматизацию** (без кнопок “взять в работу” / “закрыть лид”)
- управляемую систему лидов/отчётов: канал → outcome → визит → “ценные услуги”, с возможностью эволюции под другие бизнесы (салоны и т.п.)

Этот план фиксирует **решения‑победители**, API/данные/UX, и последовательность реализации без “мёртвых кнопок”.

---

## 0) Принципы и границы

### 0.1 Multitenant‑изоляция (строго)
- Любая сущность leads/log/funnel **всегда** привязана к `clinic_id`.
- Любой list/detail endpoint фильтрует по `clinic_id` из контекста (JWT/clinic context) и не позволяет “перескакивать”.
- Любые индексы/уникальности — с учётом `clinic_id` (или гарантированная глобальная уникальность только для UUID).
- Owner “общие отчёты по сети” — **не сейчас**, а отдельный модуль позже.

### 0.2 Immutable log vs operational workflow
- `OmniLeadLog` — **immutable** snapshot (истина для отчётов).
- “Управление” (kanban) — через `Task`‑артефакты и `TaskStream` (UX поверхность).
- Важное: **не превращаем лог в процесс**. Для процесса — отдельный stream “Лиды (в работе)” (опционально позже).

### 0.3 Автоматизация вместо кнопок
Кнопки “взять/закрыть” дают UX‑спор и ошибки. Победитель: **автоматические события** на открытие/смену/закрытие диалога.

---

## 1) Winner decisions (ключевые решения)

### 1.1 Auto‑claim (без кнопки “Взять в работу”) — revised winner
**Победитель**: **lease‑on‑open + hard‑claim‑on‑commit**, чтобы избежать случайных “захватов” при просмотре.

- **Lease (мягкий просмотр)**: когда оператор открывает чат, backend выдаёт “lease” с TTL (например 60–90с), обновляемый heartbeat’ом.
- **Hard claim (ответственность)**: выполняется автоматически **только** при “commit action”:
  - отправка первого исходящего сообщения
  - явная привязка booking/lead
  - (опционально) “пометить исход” — если появится отдельный workflow

Это сохраняет “0 кнопок” и убирает войну операторов/менеджеров, которые просто смотрят диалоги.

### 1.2 Auto‑resolve/close (без кнопки “Закрыть диалог”) — revised winner
**Победитель**: resolve только по **server‑side policy** на основе “last meaningful activity” и отсутствия активного lease, а не по “переключению чатов”.

Правило (MVP):
- чат может resolve’иться, если:
  - есть hard claim (есть owner/assignee)
  - нет активного lease (никто прямо сейчас не “внутри” диалога)
  - с момента last meaningful activity прошло ≥ X минут (настраиваемо)

Почему так:
- корректно при multiple tabs, crash, sleep
- минимизирует ложные закрытия (переключение ≠ “готово”)

Escape hatch:
- можно оставить скрытую “Force resolve” для owner/manager как аварийный механизм (не основной UX).

### 1.3 Роутинг лид‑логов в потоки (streams)
**Победитель**: routing policy на стороне backend (owner/manager настраивает), применяемая при resolve:

`(clinic_id, channel_type, optional source/campaign) -> target TaskStream.slug`

MVP оси:
- **channel_type** (TG/WA/VK/Email/…)
- outcome (BOOKED/NOT_BOOKED/UNKNOWN) — как фильтр/колонки, но не обязательно как stream

### 1.4 Фаннел: outcome → визит → ценные услуги
**Победитель**: хранить funnel‑флаги/метрики в отдельной отчётной сущности, вычисляемой по связям:
- BOOKED: есть связанный booking
- VISITED: booking перешёл в “completed/visited” (или эквивалент)
- VALUABLE_SERVICE_PURCHASED: после визита есть оказанная услуга из набора “ценных услуг”

### 1.5 “Ценные услуги” как кросс‑бизнес абстракция
**Победитель**: ввести справочник “ValuableServices” на клинику (owner управляет), который может ссылаться на:
- медицинские услуги (стоматология) / прайсовые позиции
- услуги салона/другого бизнеса (универсальная “service catalog item”)

MVP дизайн:
- `valuable_service_definitions`:
  - `id`, `clinic_id`, `title`, `service_id?` (если есть общий каталог), `price_floor?`, `is_active`, `created_at`
- Логика “ценной покупки”:
  - после визита (`VISITED`) ищем связанные оказанные услуги/позиции чека, пересекающиеся с `valuable_service_definitions`
  - если нет общего механизма чеков/оказанных услуг — флаг остаётся UNKNOWN, но схема уже готова

Почему так:
- owner сам определяет “ценность” без жёсткой привязки к стоматологии
- сохраняем универсальность для других вертикалей

---

## 2) Архитектура данных (Backend)

### 2.1 OmniLeadLog (уже есть, но требования к multitenant)
- все запросы обязаны фильтровать по `clinic_id`
- индексы: `(clinic_id, closed_at)`, `(clinic_id, outcome, closed_at)`, `(clinic_id, contact_id, closed_at)`
- уникальность: `omni_chat_id` может оставаться global unique, но при желании можно поменять на `(clinic_id, omni_chat_id)` (не обязательно)

### 2.2 LeadLog Task‑артефакт (уже есть)
Требования:
- `Task.clinic_id` всегда соответствует клинике lead‑log
- `Task.stream_id` определяется routing policy (см. ниже)
- `Task.trace_id = omni_lead_log:<uuid>` — обязательная связь в MVP

### 2.3 Routing policy сущность (новая)
Нужно хранить правила маршрутизации per clinic.

MVP:
- `lead_log_routing_rules`:
  - `id`, `clinic_id`
  - `channel_type` (nullable: “любое”)
  - `source_key` (nullable: “любое”; позже — campaign/атрибуция)
  - `target_stream_id` (UUID, FK на `task_streams`, строго в рамках clinic_id)
  - `target_stream_slug` (string, optional для удобства UI; не источник истины)
  - `is_active`, `sort_order`

Алгоритм (после прожарки @ARCH):
- при resolve выбираем первое совпавшее правило (по sort_order)
- если нет совпадений — fallback в `leads-log`
- **не** создаём потоки “лениво” в resolve: правила должны ссылаться на заранее созданные streams (governance, без неожиданных side-effects)

### 2.4 Funnel projection (новая, опционально этап 2)
Не смешиваем immutable log и вычисляемую аналитику.

`lead_log_funnel_snapshots` (или materialized view позже):
- `clinic_id`, `lead_log_id` (unique)
- `booked` bool/tri-state
- `visited` bool/tri-state
- `valuable_purchase` bool/tri-state
- `computed_at`

---

## 3) API contracts (Backend)

### 3.1 Auto-claim
Winner API (presence/lease):
- `POST /api/v1/admin/omni-chats/{chat_id}/presence`
  - body: `client_event_id`, `tab_id`, `event=OPEN|HEARTBEAT|CLOSE`
  - создаёт/продлевает lease
  - идемпотентность: unique `(clinic_id, client_event_id)`

Hard claim:
- выполняется автоматически на backend при commit action (первый outbound send / link booking).

Legacy:
- `POST /claim` можно оставить (ручной/override сценарии), но UI не использует как primary.

### 3.2 Auto-resolve
- `POST /api/v1/admin/omni-chats/{chat_id}/resolve` (уже есть)
- Изменения:
  - применить routing policy для выбора stream
  - обеспечить идемпотентность (уже)
  - закрывать только если нет активного lease (или есть force‑право)

### 3.3 Routing policy management (owner/manager)
- `GET /api/v1/admin/leads-log/routing-rules`
- `PUT /api/v1/admin/leads-log/routing-rules` (replace set)
- RBAC:
  - view: `leads.log.view`
  - manage: новый `leads.log.manage` (owner/manager)
  - опасные omni‑операции:
    - `omni.chat.claim` / `omni.chat.claim.override`
    - `omni.chat.resolve` / `omni.chat.resolve.override`

### 3.4 Reports (MVP)
- `GET /api/v1/admin/leads-log/stats?date_from&date_to`
  - counts by outcome
  - per-admin counts (opened_by_admin_id)
  - SLA-like: time-to-first-response (если есть данные)

---

## 4) UX/Frontend

### 4.1 /admin/omni-chat (полная автоматизация)
- убрать primary кнопки claim/resolve из header
- lease presence: OPEN + heartbeat пока диалог активен
- hard claim на commit action (первый outbound)
- auto-resolve — только по server policy (idle since last meaningful activity + no active lease)
- всегда показывать статус:
  - “В работе у …”
  - “Закрыт”

### 4.2 /admin/leads-log (kanban surface)
- это канбан задач, но фиксирован поток “лиды”
- сверху: day picker + stream picker (если несколько lead streams)
- карточка: контакт/канал/время/short title
- modal: structured transcript, outcome badge, “Открыть исходный чат”

### 4.3 Routing policy UI (owner/manager)
- простая таблица правил:
  - канал → поток
  - порядок правил
  - тест “куда попадёт лид из канала X”

---

## 5) “Прожарка” рисков и как не сделать мёртвый UI

### 5.1 Auto-resolve опасность
Если оператор читает долго и переключается — автозакрытие может быть неожиданным.

Снижения риска:
- автозакрытие только если чат “тихий” ≥ M минут и нет черновика сообщения
- показывать подсказку “Диалог будет закрыт автоматически после …”
- “escape hatch” для owner/admin (скрытый)

### 5.2 Multiple tabs
- auto-claim должен быть “best effort” с 409 конфликтом
- auto-resolve должен учитывать “last_activity_at_by_admin” (см. возможное расширение)

### 5.3 Multitenant
- на каждом endpoint проверить clinic filter
- в routing rules ключ `clinic_id` обязателен

---

## 6) План реализации (итерации)

### Итерация 1 (MVP++)
- FE: auto-claim при select, скрыть кнопки claim/resolve
- FE: auto-resolve при переключении чатов после idle
- BE: routing rules модель + API + применение при resolve
- FE: stream picker на leads-log (если потоков >1)
- Тесты: контрактные на конфликт claim + идемпотентность resolve + routing

### Итерация 2 (отчёты)
- BE: stats endpoint
- FE: owner modal/страница “Отчёты лидов”

### Итерация 3 (funnel)
- “visited” и “valuable purchase” если есть данные в домене
- valuable services definition UI

---

## 7) Метрики и наблюдаемость (обязательно)

Цель: чтобы “Лиды (лог)” и автоматизация не были чёрным ящиком. Метрики должны позволять:
- видеть объём и качество лидов per clinic (изолированно)
- ловить ошибки/регрессии automation (presence/lease, hard-claim, resolve)
- понимать эффективность операторов (в рамках клиники)
- понимать влияние routing rules (куда распределяются обращения)

### 7.1 Lead-log метрики (immutable truth)
- **`omni_lead_logs_resolved_total{clinic_bucket,outcome}`**: сколько resolve создало lead-log (уже добавлено).
- **`omni_lead_logs_resolve_errors_total{clinic_bucket,reason}`**: ошибки resolve (например: NOT_CLAIMED, FORBIDDEN, DB_ERROR).
- **`omni_lead_logs_transcript_bytes_histogram{clinic_bucket}`**: размер transcript (чтобы контролировать стоимость/лимиты).

### 7.2 Presence/lease метрики (automation health)
- **`omni_presence_events_total{clinic_bucket,event}`**: OPEN/HEARTBEAT/CLOSE.
- **`omni_presence_idempotent_replays_total{clinic_bucket}`**: сколько событий пришло повторно (client_event_id уже видели).
- **`omni_active_leases_gauge{clinic_bucket}`**: текущие активные leases (по expires_at > now).
- **`omni_lease_duration_seconds_histogram{clinic_bucket}`**: фактическая длительность lease‑сессий (OPEN→CLOSE).

### 7.3 Hard-claim метрики (без кнопок)
- **`omni_auto_claim_total{clinic_bucket,source}`**: hard-claim по commit action (message / upload / booking link).
- **`omni_auto_claim_conflicts_total{clinic_bucket}`**: 409 “already claimed” на попытку commit другим оператором.

### 7.4 Auto-resolve policy метрики
- **`omni_auto_resolve_attempts_total{clinic_bucket,result}`**: attempted / skipped_active_lease / skipped_not_idle / resolved / error.
- **`omni_time_to_first_outbound_seconds_histogram{clinic_bucket}`**: claimed_at → first outbound (если есть данные).

### 7.5 Routing rules метрики
- **`lead_log_routing_matches_total{clinic_bucket,channel_type,stream_slug}`**: какое правило куда направило.
- **`lead_log_routing_fallback_total{clinic_bucket,channel_type}`**: не нашли правило → fallback stream.

### 7.6 Логи/аудит (структурировано)
- Структурированные логи по ключевым событиям:
  - presence OPEN/CLOSE (chat_id, admin_id, tab_id, lease_expires_at)
  - auto_claim_commit (chat_id, admin_id)
  - resolve (chat_id, admin_id, lead_log_id, task_id, outcome, stream_id)
  - routing (matched_rule_id, target_stream_id)

> Примечание: все метрики/логи строго в рамках clinic_id (через clinic_bucket_label), owner-агрегации — отдельным модулем позже.

