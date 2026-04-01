## LEADS_LOG_CONCEPT — «Лиды (лог)» из omni‑чатов

### Problem statement
Сейчас закрытие диалога и фиксация результата завязаны на ручные кнопки/формы. Это даёт:\n
- неполные/несогласованные логи\n
- лишние действия операторов\n
- слабую управляемость маркетинга (нет дневного журнала обращений)\n
\n
Нужна система, где **каждое обращение** фиксируется как лид‑лог, а закрытие диалога — это одно действие, после которого **чат закрывается и лог сохраняется неизменно**.

### Winner decisions (принято)
- **Триггер**: оператор нажимает **«Закрыть диалог»** (явное действие в omni‑чате).\n
- **Outcome**: «записался/не записался» определяется по **связи с Booking/Lead**.\n
- **Title**: без AI — берём **первую фразу клиента** (trim+truncate) + fallback «Обращение».\n
- **Transcript**: immutable snapshot **при закрытии** в отдельной таблице.\n
- **Повторное обращение**: создаёт **новый диалог** и новый lead‑log (старый не переоткрывается).

### Backend: data model
Новая таблица: `omni_lead_logs`.\n
ORM: `src/domain/entities/omni_lead_log.py`.\n
Миграция: `alembic/versions/b8c9d0e1f2a3_omni_lead_logs_snapshot.py`.

Поля (MVP):\n
- `clinic_id`, `omni_chat_id` (unique), `contact_id`\n
- `opened_by_admin_id`, `opened_at`, `closed_at`\n
- `title`\n
- `outcome`: `BOOKED | NOT_BOOKED | UNKNOWN`\n
- `transcript_text` (plain)\n
- `transcript_json` (структура сообщений)\n
- связи: `lead_id`, `booking_id`, `patient_id`\n
\n
Индексы: по клинике + дате, outcome, contact.

### Backend: API contracts
#### Resolve (основной)
`POST /api/v1/admin/omni-chats/{chat_id}/resolve`\n
RBAC: `omni.inbox.manage`.\n
Правила:\n
- чат должен быть **claimed**\n
- закрывать может assignee или owner\n
- endpoint **идемпотентный**: если лог уже создан — вернёт существующий `lead_log_id`\n
\n
Ответ (MVP):\n
```json
{ \"lead_log_id\": \"...\", \"task_id\": \"...\", \"outcome\": \"BOOKED\" }
```

#### Lead logs list/detail
`GET /api/v1/admin/lead-logs?day=YYYY-MM-DD&outcome=BOOKED`\n
`GET /api/v1/admin/lead-logs/{id}`\n
RBAC: `leads.log.view`.\n
day трактуется как UTC‑день (MVP).

### Backend: канбан‑артефакт
При resolve создаётся `Task` со:\n
- `source=\"system\"`, `trace_id=\"omni_lead_log:<id>\"`\n
- `stream_id` = поток `TaskStream(slug=\"leads-log\")` (lazy create)\n
- `status=\"done\"` (это лог, не активная работа)\n
- `title` = auto title\n
- `description` = первые ~1800 символов transcript + ссылка на `LeadLog` id\n
- `booking_id/lead_id/patient_id` выставляются best‑effort.\n

### Frontend: UX
#### Omni‑чат
Файл: `frontend/src/admin/pages/AdminOmniChatPage.tsx`.\n
Победитель:\n
- нет «Заявка обработана/закрыта»\n
- одна primary‑кнопка: **«Закрыть диалог»** (для assignee или owner)\n
- по клику вызывается `resolve`, чат закрывается и уходит из активных списков.

#### Новая страница: Лиды (лог)
Файл: `frontend/src/admin/pages/AdminLeadsLogPage.tsx`.\n
Роут: `/admin/leads-log`.\n
Композиция:\n
- верхняя панель: day picker + outcome фильтр + поиск\n
- колонки по outcome: BOOKED/NOT_BOOKED/UNKNOWN\n
- справа: transcript выбранного лога.\n

### RBAC
Новый permission: `leads.log.view`.\n
Backend matrix: `src/application/rbac_matrix.py`.\n
Миграция: `alembic/versions/c0d1e2f3a4b5_leads_log_view_permission.py`.\n
По умолчанию привязан к ролям: owner + manager.\n
Маркетологам/доверенным — выдаётся через существующий экран RBAC (роль/персональные права).

### Rollout / совместимость
- `/close` остаётся как legacy endpoint (может использоваться другими частями), но UI переходит на `/resolve`.\n
- lead‑logs вводятся как read‑only модуль.\n
- дальше можно улучшать:\n
  - clinic‑timezone для day\n
  - экспорт CSV\n
  - deep link «открыть исходный чат»\n
  - AI‑title generator (с фоллбеком).

