# DEV_PROMPTS — Kanban Workstation Hardening 2026

> Роль исполнения: `@DEV`
> Архитектурный источник: `docs/artifacts/ARCH_KANBAN_WORKSTATION_TASKS_CHAT_2026.md`
> Смежные источники: `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md`, `docs/artifacts/ARCH_TASKS_NEXT.md`, `docs/artifacts/ARCH_OMNI_AGENT_WORKSTATION_2026.md`

## Цель одним абзацем

Собрать production-контур Kanban Workstation для `/admin/tasks` как единую операционную панель: управляемые статусы, WIP/SLA/aging, устойчивый drag-and-drop, блокировки с причинами, аудит переходов, массовые операции, keyboard-доступность, а также связка с задачным чатом, входящими сообщениями и приглашением участников в смежные процессы (calendar/task-room), без расхождения с multi-tenant и RBAC контрактами.

---

## 1) Порядок реализации (волнами)

### Wave A — Контракты и модель (backend first)

1. Добавить в Task доменную модель:
   - `rank` (int),
   - `blocked` (bool),
   - `blocked_reason` (text nullable),
   - `stage_entered_at` (datetime),
   - `checklist_done` (bool, если нет отдельной чеклист-таблицы).
2. Добавить историю переходов:
   - `task_status_transitions` (task_id, from_status, to_status, actor_admin_id, reason, created_at).
3. Ввести workflow-policy:
   - запрет `done` при `blocked=true`,
   - запрет `done` при `checklist_done=false`,
   - запрет перехода в колонку при превышении WIP (если WIP policy в БД/конфиге).
4. Обновить API:
   - PATCH task: статус + workflow-поля + reason,
   - endpoint истории переходов,
   - endpoint reorder/rank update.

### Wave B — Канбан-ядро фронта

5. Перевести хранение rank/blocked/audit с local persistence на API.
6. Реализовать DnD:
   - межколоночный перенос,
   - позиционирование внутри колонки,
   - optimistic update + rollback при 4xx/5xx.
7. Включить операционный UI:
   - WIP-индикаторы,
   - SLA overdue,
   - aging (48h+/настраиваемо),
   - blocked badge + tooltip.
8. Включить bulk-панель:
   - multi-select карточек,
   - массовый перевод с валидацией workflow.

### Wave C — Messaging/Chat/Invites интеграция

9. Для каждой задачи включить task-room правила:
   - комментарии + служебные сообщения о смене статуса,
   - системные записи "кто перевел и почему".
10. Связка с Omni Chat:
   - быстрый переход к диалогу,
   - сигнал "задача требует подтверждения" в свимлейн.
11. Связка с календарем/участниками:
   - инвайт участников задачи в календарное событие,
   - статус подтверждения участников (ack) в контексте задачи.

### Wave D — Enterprise-hardening

12. Включить RBAC-слой на действия:
   - кто может менять статус,
   - кто может снимать блокировку,
   - кто может bulk/переприоритетизировать.
13. Добавить наблюдаемость:
   - метрики переходов, SLA-нарушений, блокировок,
   - события аудита для расследований.
14. Добавить rate limits и anti-flood на комментарии/системные переходы.

---

## 2) Детальное ТЗ (функциональные требования)

### FR-1. Канбан-колонки и статусы

- Поддержка базовых статусов: `open`, `in_progress`, `on_hold`, `review`, `done`, `cancelled`.
- Поддержка расширяемых пользовательских статусов (если backend возвращает).
- Строгое выравнивание карточек и предсказуемое поведение drop zone.

### FR-2. WIP-политика

- Для каждой колонки WIP limit из backend policy.
- При превышении:
  - визуальный alert,
  - блокировка drop (кроме исключений по policy).

### FR-3. Workflow guardrails

- Переход в `done` только при checklist и без blocked.
- Переходы с обязательной причиной для некоторых маршрутов (policy-driven).
- Backend является final authority, фронт дублирует валидацию для UX.

### FR-4. Rank / порядок внутри колонки

- Перетаскивание карточки на позицию.
- Persist rank через API.
- Конкурентная устойчивость: conflict-safe reorder (версия или серверное нормализующее правило).

### FR-5. Blocked state

- Можно отметить задачу blocked и указать причину.
- Нельзя закрыть blocked-задачу.
- Причина доступна в карточке и деталях.

### FR-6. SLA / Aging

- SLA overdue: по due_at.
- Aging: время в стадии (`now - stage_entered_at`).
- Визуальная индикация уровня риска.

### FR-7. Bulk actions

- multi-select карточек;
- массовая смена статуса;
- отчет по результату (успешно/отклонено по policy).

### FR-8. Audit trail

- История переходов с actor/time/reason.
- Быстрый просмотр в UI + отдельный endpoint для полного журнала.

### FR-9. Keyboard & accessibility

- Полная клавиатурная навигация по карточкам.
- Команды перемещения между колонками.
- Screen-reader labels для ключевых действий.

### FR-10. Чат/сообщения/приглашения

- В карточке/деталях задачи:
  - task chat (команда),
  - переход в omni chat по пациенту,
  - отправка контекстного сообщения участникам,
  - приглашение участников в календарный слот по задаче.
- Действия логируются в transition/event stream.

---

## 3) Нефункциональные требования

- Multi-tenant isolation по `clinic_id`.
- Оптимистичные операции с rollback.
- Защита от race-condition при reorder/status update.
- P95 загрузки канбана <= 1.5s при 500+ задачах (с пагинацией/виртуализацией).
- Наблюдаемость: trace_id в критичных операциях.

---

## 4) Обязательные тесты

1. Интеграционные:
   - переходы по policy (`done` blocked/checklist),
   - WIP limit enforce,
   - reorder с конкуренцией.
2. API:
   - audit endpoint,
   - bulk status update partial success.
3. Frontend:
   - DnD внутри и между колонками,
   - keyboard moves,
   - filter/sla/aging rendering.
4. E2E:
   - полный путь: создать задачу -> чат -> блокировка -> разблокировка -> done.

---

## 5) Domain Checklist

Тип: `CRM/Task Workstation` (Kanban + collaboration)
Источник: `docs/DOMAIN_STANDARDS.md` + `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md`

- [ ] Loading/Empty/Error/Success состояния по канбану и истории.
- [ ] Нет UUID в пользовательских подписях/карточках.
- [ ] Все мутации имеют disabled/loading состояния.
- [ ] Все переходы статусов валидируются и объясняют отказ.
- [ ] DnD доступен мышью и клавиатурой.
- [ ] Аудит переходов доступен оператору/руководителю.
- [ ] Интеграция с чатом и приглашением участников работает через единый контур.

@QA_ARCH проверяет список перед выдачей зеленого статуса.

---

## 6) Definition of Done

- Контракты и миграции приняты, API задокументирован.
- Frontend использует backend source of truth для rank/blocked/audit.
- Все сценарии из FR-1..FR-10 покрыты тестами.
- Нет регрессии по текущим admin-модулям.

---

## 7) TODO статус реализации (операционный)

### Wave A — Контракты и модель

- [x] Task model: `rank`, `blocked`, `blocked_reason`, `checklist_done`, `stage_entered_at`.
- [x] Таблица истории переходов `task_status_transitions`.
- [x] Workflow policy на backend: запрет `done` при blocked/checklist, WIP guardrails.
- [x] API: PATCH workflow-поля, endpoint transitions, endpoint reorder/rank.

### Wave B — Канбан-ядро фронта

- [x] Frontend использует API как source-of-truth для rank/blocked/audit.
- [x] DnD межколоночный + reorder внутри колонки через API.
- [x] Optimistic status update + rollback при ошибках.
- [x] WIP/SLA/Aging/blocked indicators в канбане.
- [x] Bulk status update с отчетом partial success/rejected.
- [x] Conflict-safe reorder (версионирование/серверная нормализация при конкурентных reorder).

### Wave C — Messaging / Chat / Invites

- [x] Task chat comments для карточки/деталей.
- [x] Системная запись в task-room при смене статуса (`from -> to`, причина).
- [x] Быстрый переход в Omni chat по пациенту из карточки.
- [x] Сигнал "требует подтверждения" как отдельный swimlane/queue (сейчас только фильтр).
- [x] Инвайт участников задачи в календарный слот c ACK-статусом.

### Wave D — Enterprise hardening

- [x] Точный RBAC-слой по операциям (отдельно: change-status / unblock / bulk / reprioritize).
- [x] Наблюдаемость: отдельные метрики переходов/SLA/block + аудит-ивенты расследований.
- [x] Rate-limit/anti-flood для task comments и системных transition-сообщений.

### Тесты (обязательный минимум к закрытию)

- [ ] Интеграционные: workflow policy + WIP + reorder concurrency.
- [ ] API: transitions endpoint + bulk partial success.
- [x] Frontend: DnD (intra/inter-column), keyboard move, filters/SLA/aging.
- [x] E2E: create -> chat -> block -> unblock -> done.

---

## 8) Execution TODO (next actions by priority)

> Формат: `TODO-ID` · Приоритет · Зависимости · Done-критерий

### Sprint P0 (сначала закрыть риски корректности)

- [x] `KB-001` · P0 · deps: none  
  Реализовать conflict-safe reorder на backend (`/admin/tasks/reorder`): optimistic lock (версия/etag) или серверная нормализация рангов в транзакции.  
  **Done:** конкурентные reorder не приводят к дублированию rank и "прыжкам" карточек; API возвращает консистентный порядок.

- [x] `KB-002` · P0 · deps: `KB-001`  
  Добавить интеграционный тест reorder race (две конкурентные перестановки в одной колонке).  
  **Done:** тест стабильно зеленый, воспроизводит конфликт и подтверждает итоговую консистентность.

- [x] `KB-003` · P0 · deps: none  
  Уточнить RBAC по операциям: `change_status`, `unblock`, `bulk_status`, `reprioritize` с явной проверкой прав в API.  
  **Done:** 403 для запрещенных действий, положительные сценарии не деградируют.

### Sprint P1 (операционный контур и наблюдаемость)

- [x] `KB-004` · P1 · deps: none  
  Вынести "requires approval" в отдельный swimlane/queue на UI (не только фильтр) с корректным счетчиком и переходами.  
  **Done:** отдельная визуальная зона в `/admin/tasks`, задачи попадают туда по policy, переходы синхронны с основным канбаном.

- [x] `KB-005` · P1 · deps: `KB-003`  
  Добавить audit/event stream для расследований: события по `blocked/unblocked`, `bulk`, `reorder`, `status_transition`.  
  **Done:** каждое критичное действие пишет событие с actor/clinic/task/timestamp/reason.

- [x] `KB-006` · P1 · deps: none  
  Добавить метрики: transitions total, blocked total, SLA overdue gauge/counter, bulk reject rate.  
  **Done:** метрики экспортируются и имеют clinic/source labels без кардинальности-ловушек.

- [x] `KB-007` · P1 · deps: none  
  Ввести anti-flood/rate-limit для task comments и системных transition-комментариев.  
  **Done:** при превышении лимита API возвращает структурированную ошибку `{"detail","code"}`, UI показывает объяснение.

### Sprint P2 (collaboration integrations)

- [x] `KB-008` · P2 · deps: `KB-003`  
  Реализовать invite участников задачи в календарный слот + ACK статус в контексте задачи.  
  **Done:** из карточки задачи можно пригласить участников, статус подтверждения виден в задаче и сохраняется в API.

- [x] `KB-009` · P2 · deps: `KB-008`  
  Логировать invite/ack действия в transition/event stream.  
  **Done:** действия доступны в аудите задачи и в расследовательском логе.

### Тестовый трек (параллельно спринтам)

- [x] `KB-T01` · P0 · deps: none  
  Интеграционные тесты workflow-policy (`done` blocked/checklist, WIP limit).  
  **Done:** 100% покрытие критичных guardrails переходов.

- [x] `KB-T02` · P0 · deps: `KB-001`  
  API тесты для `/transitions` и `/bulk/status` (partial success + rejected reasons).  
  **Done:** проверяются структура ответа, коды и бизнес-ограничения.

- [x] `KB-T03` · P1 · deps: none  
  Frontend тесты DnD (межколоночный + внутри колонки), keyboard moves, filter/sla/aging rendering.  
  **Done:** тесты проходят стабильно в CI без flaky сценариев.

- [x] `KB-T04` · P2 · deps: `KB-008`  
  E2E сценарий: create -> chat -> block -> unblock -> done (+ invite/ack где применимо).  
  **Done (условно):** сценарий автоматизирован; финальное подтверждение только после прогона в CI/preview clean environment.

Version: 1.2 | 2026-03-26
