# Архитектура: Kanban Workstation (Tasks + Chat + Invites)

Режим:    SAAS
Backend:  Python + FastAPI
Frontend: TypeScript + React (Mantine + React Query + dnd-kit)
БД:       PostgreSQL
Почему:   Текущий стек проекта уже в этом контуре; цель — усиление без платформенной миграции.

---

## ADR (ключевые решения)

### ADR-1. Backend — единственный источник workflow-истины

- Все правила переходов статусов (WIP, blocked/checklist, обязательные причины) проверяются сервером.
- Фронт может показывать pre-check, но не принимает финальное решение.

### ADR-2. Rank и аудит — серверные, не локальные

- `rank` хранится в Task.
- Все изменения порядка/статуса попадают в transition log.
- Local storage допускается только как временный fallback до rollout.

### ADR-3. Task-room как часть Kanban, не отдельный "остров"

- Комментарии, сервисные ноты и вызовы в чат/календарь связаны с `task_id`.
- История статусов и коммуникации доступны в одном контексте задачи.

### ADR-4. Инвайты участников через единый collaboration контур

- Приглашение участников из задачи в календарное событие делается через существующий staff-collab API.
- Подтверждение приглашений отображается как task-signal.

---

## Схема БД (добавления)

### Таблица `tasks` (расширение)

- `rank` int not null default 1000
- `blocked` bool not null default false
- `blocked_reason` text null
- `checklist_done` bool not null default false
- `stage_entered_at` timestamptz not null default now()
- `updated_by_admin_id` uuid null (FK admin_users.id)

Индексы:

- `(clinic_id, status, rank)`
- `(clinic_id, assignee_id, status)`
- `(clinic_id, stage_entered_at)`

### Таблица `task_status_transitions`

- `id` uuid pk
- `clinic_id` uuid not null
- `task_id` uuid not null fk tasks(id)
- `from_status` text not null
- `to_status` text not null
- `reason` text null
- `actor_admin_id` uuid null fk admin_users(id)
- `created_at` timestamptz not null default now()
- `metadata` jsonb not null default '{}'

Индексы:

- `(clinic_id, task_id, created_at desc)`
- `(clinic_id, created_at desc)`

### Таблица `task_wip_policies` (опционально)

- `id` uuid pk
- `clinic_id` uuid not null
- `status` text not null
- `wip_limit` int not null
- unique `(clinic_id, status)`

---

## API-контракты

### 1) Обновление задачи

`PATCH /v1/admin/tasks/{task_id}`

Поддерживаемые поля:

- `status`
- `rank`
- `blocked`
- `blocked_reason`
- `checklist_done`
- `transition_reason` (для workflow логов)

Ответ: Task DTO с актуальными workflow-полями.

### 2) Пакетный переход

`POST /v1/admin/tasks/bulk/status`

Body:

- `task_ids: string[]`
- `to_status: string`
- `reason?: string`

Response:

- `applied: string[]`
- `rejected: [{task_id, code, detail}]`

### 3) Reorder внутри колонки

`POST /v1/admin/tasks/reorder`

Body:

- `status: string`
- `ordered_task_ids: string[]`

Response:

- `status`
- `updated_ranks`

### 4) История переходов

`GET /v1/admin/tasks/{task_id}/transitions?limit=50&before=...`

### 5) WIP policy

`GET /v1/admin/tasks/policies/wip`

---

## Контракт ошибок

Единый формат:

`{"detail":"...", "code":"SNAKE_CASE", "field":null|string}`

Коды:

- `WORKFLOW_RULE_VIOLATION`
- `WIP_LIMIT_EXCEEDED`
- `TASK_BLOCKED`
- `CHECKLIST_REQUIRED`
- `INVALID_STATUS_TRANSITION`
- `TENANT_FORBIDDEN`
- `VALIDATION_ERROR`
- `NOT_FOUND`

---

## Интеграции: чат, сообщения, приглашения

### Task Chat

- Используем существующий контур `/v1/admin/tasks/{id}/comments`.
- Добавляем тип записи `system_event` (опционально): статус изменен, блокировка, разблокировка.

### Omni Chat bridge

- Из задачи доступен переход в omni-chat с параметром `patient_id`/`lead_id`.
- Логируем событие перехода как UI audit event.

### Calendar/Invites bridge

- Из задачи можно создать/обновить календарное событие и передать участников.
- Статус подтверждения участников отображается как contextual badge в задаче.

---

## Наблюдаемость

Метрики:

- `tasks_status_transition_total{from,to,clinic_id}`
- `tasks_wip_violation_total{status,clinic_id}`
- `tasks_blocked_total{clinic_id}`
- `tasks_sla_overdue_total{clinic_id}`
- `tasks_bulk_transition_total{clinic_id}`

Логи:

- обязательно `clinic_id`, `task_id`, `actor_admin_id`, `from_status`, `to_status`, `trace_id`
- без утечек чувствительного контента сообщений в INFO.

---

## Безопасность / RBAC

- Tenant isolation по `clinic_id` для всех операций.
- RBAC:
  - `manage_tasks_status`
  - `manage_tasks_blocked`
  - `manage_tasks_bulk`
  - `view_task_audit`
- Комментарии/чат задачи — по праву `view_tasks` + `comment_tasks`.

---

## Domain Checklist

Тип: `CRM / Task workstation`
Источник: `docs/DOMAIN_STANDARDS.md` + TPF/tech passport

- [ ] Полный state matrix (L/E/E/S) в канбане и деталях.
- [ ] Workflow-ограничения валидируются backend и объясняются в UI.
- [ ] WIP/SLA/Aging отражены и в API, и в UI.
- [ ] Переходы аудируются.
- [ ] Мышь + клавиатура поддержаны.
- [ ] Интеграция с task-chat и participant invites согласована.

@QA_ARCH проверяет этот список перед выдачей зеленого статуса.

---

## Указания для @DEV

1. Начать с миграций и API контрактов (Wave A).
2. Затем фронт перевести на серверные rank/blocked/audit (Wave B).
3. После этого связать task-room, omni, invites (Wave C).
4. Завершить тестами и наблюдаемостью (Wave D).

---

## NFR (паспорт)

Релевантные разделы `docs/ARCHITECTURE_EXCELLENCE_PASSPORT.md`:

- Миграционная безопасность
- Транзакционная целостность
- Multi-tenant и RBAC
- Наблюдаемость и эксплуатация
- Тестовая зрелость

Version: 1.0 | 2026-03-26
