# Dental Booking — Buyer-Ready Product Dossier (code-backed)

Этот документ предназначен для реального покупателя/биржи. **Все утверждения ниже опираются только на код** в репозитории `dental_booking` и могут быть проверены по указанным файлам.

## 1) Коротко: что продаётся

**Dental Booking** — web‑платформа для стоматологической клиники/сети:

- Backend: **FastAPI** + Postgres + Alembic + Redis + Celery.
- Frontend: **Vite/React** (админ‑панель).
- Ключевой дифференциатор: **Omnichannel Inbox (omni‑чат) + AI‑помощник** + платежи/предоплата + Enterprise‑уровня RBAC.

Кодовая база содержит инфраструктуру запуска в Docker Compose и тесты (в т.ч. E2E для omni‑чата).

## 2) Стек и инфраструктура (подтверждение кодом)

- **Docker Compose**: Postgres 16 + Redis 7 + backend + celery + frontend + e2e профайл  
  Доказательство: `docker-compose.yml`.
- **Backend**: FastAPI/Starlette/Uvicorn, SQLAlchemy, Alembic, Redis, Celery  
  Доказательство: `pyproject.toml`.
- **Frontend**: React 18, Mantine UI, React Query, Playwright  
  Доказательство: `frontend/package.json`.

## 3) Omnichannel Inbox (omni‑чат): что умеет (подтверждение кодом)

### 3.1 Админ‑API omni‑чата

Роутер omni‑чата: `src/api/v1/routers/admin_omni_chat.py`.

Подтверждённые возможности:

- **Список чатов** с фильтрами по статусу/поиску/каналам/назначению  
  Доказательство: `list_omni_chats(...)` в `src/api/v1/routers/admin_omni_chat.py`.
- **Claim/назначение в работу** (идемпотентно, конфликт при захвате другим админом)  
  Доказательство: `claim_omni_chat(...)`.
- **События присутствия/leases (OPEN/HEARTBEAT/CLOSE)** + идемпотентность по `client_event_id`  
  Доказательство: `omni_chat_presence(...)`.
- **Закрытие чата** с обязательным outcome/tags/comment (внутренние сущности closure/tags)  
  Доказательство: `close_omni_chat(...)`.
- **Resolve**: снепшот переписки в lead‑лог + артефакт task “done”  
  Доказательство: `resolve_omni_chat(...)` и `_resolve_chat_to_lead_log_task(...)`.
- **Сообщения**: получение, отправка текста, отправка файла, скачивание вложений  
  Доказательство: `get_omni_chat_messages(...)`, `send_admin_omni_message(...)`, `send_admin_omni_message_upload(...)`, `download_omni_message_attachment(...)`.
- **Quick replies** (шаблоны быстрых ответов)  
  Доказательство: `list_omni_quick_replies(...)`, `create_omni_quick_reply(...)`, `update_omni_quick_reply(...)`, `delete_omni_quick_reply(...)`.
- **SSE для realtime‑обновлений** + short‑lived `sse-token`  
  Доказательство: `issue_omni_chat_sse_token(...)`, `omni_chat_event_stream(...)`.
- **Аналитика по omni‑чатам** (owner reports)  
  Доказательство: `omni_chat_analytics(...)`.
- **Переключение ai_mode на чат** (быстрый тумблер)  
  Доказательство: `update_omni_chat_ai_mode(...)`.

### 3.2 Realtime слой (Redis pub/sub + SSE)

- Публикация событий “message.created” и “chat.updated” в Redis‑канал клиники  
  Доказательство: `src/infrastructure/realtime/omni_pubsub.py`.
- SSE‑подписка на `omni:events:<clinic_id>` и keepalive  
  Доказательство: `omni_chat_event_stream(...)` в `src/api/v1/routers/admin_omni_chat.py`.

### 3.3 Frontend‑страница omni‑чата (UI)

UI‑экран админки: `frontend/src/admin/pages/AdminOmniChatPage.tsx`.

Подтверждённые элементы UX:

- Inbox “Все / Новые”, поиск, фильтр по `channel_types`, подсветка “needs attention”.
- Work pane “Мои заявки (в работе/закрытые)”.
- Reply‑цитирование через `reply_to:` и скрытие raw‑строки в bubble.
- Вложения (preview + скачивание).
- Переключатель AI режима.
- Presence heartbeats из браузера (OPEN/HEARTBEAT/CLOSE).

E2E‑покрытие (mocked API): `frontend/e2e/admin-omni-chat.spec.ts`.

## 4) AI‑помощник для omni‑чата: что реализовано (подтверждение кодом)

AI orchestrator: `src/application/services/omnichannel_ai_orchestrator.py`.

Подтверждённые режимы:

- `DISABLED`: no‑op.
- `SUGGEST_ONLY`: генерирует черновик ответа как `TEMPLATE` сообщение (видно админам).
- `AUTO_REPLY`: отправляет исходящее AI‑сообщение клиенту при достаточной уверенности.
- “Agent mode”: function‑calling агент, который выполняет tools loop и пишет итоговый AI‑ответ в чат.

Также есть UI‑эндпоинт доступных инструментов для Omni:  
`src/api/v1/routers/admin_omni_tools.py` (`GET /admin/omni/available-tools`).

## 5) Интеграции каналов (важные границы по outbound)

### 5.1 Inbound (входящие сообщения) через вебхуки

Integration Gateway роутер: `src/api/v1/routers/integrations_gateway.py`.  
Нормализация payload: `src/application/services/integration_gateway_service.py`.

Подтверждено наличие inbound‑входа для:

- Telegram webhook: `/integrations/webhooks/telegram`
- WhatsApp webhook: `/integrations/webhooks/whatsapp` (MVP, упрощённая структура payload)
- VK webhook: `/integrations/webhooks/vk` (MVP, упрощённая структура payload)
- Instagram webhook: `/integrations/webhooks/instagram` (MVP)
- Email inbound webhook: `/integrations/webhooks/email` (MVP)
- Webchat widget: `/webchat/messages` + long‑poll `/webchat/poll`

### 5.2 Outbound (исходящие ответы оператора)

Критично: политика выбора канала для ответа оператора ограничивает outbound только каналами:

- `TELEGRAM_BOT`
- `WEB_WIDGET`
- `WEB_APP`

Доказательство:

- `channel_type_allows_admin_outbound(...)` в `src/application/services/omni_outbound_policy.py`.
- `OmnichannelOutboundDispatcher.dispatch_to_channel(...)` в `src/application/services/omnichannel_outbound_dispatcher.py`.

Следствие для продажи/внедрения: если бизнес‑требование — “оператор отвечает прямо в WhatsApp/VK”, это требует отдельного исходящего адаптера (в данном репозитории он не подтверждён кодом).

## 6) Платежи/кассы (подтверждение кодом)

### 6.1 YooKassa

- Создание платежа для записи (предоплата)  
  Доказательство: `POST /payments` в `src/api/v1/routers/payments.py`, сервис `src/application/services/payment_service.py`.
- Webhook YooKassa и синхронизация статуса брони  
  Доказательство: `POST /payments/webhook` и `PaymentService.handle_webhook(...)`.

### 6.2 Хранилище кредитеншелов платежных шлюзов (для расширений)

- Зашифрованное хранение provider‑payload per clinic  
  Доказательство: `src/api/v1/routers/admin_payment_gateway.py`, `src/application/services/clinic_payment_gateway_service.py`.

## 7) RBAC (enterprise‑уровень) (подтверждение кодом)

- Канонический список permissions и базовая матрица ролей  
  Доказательство: `src/application/rbac_matrix.py`.
- Полноценный admin‑API для RBAC: роли, пресеты, назначения, overrides, политики, audit‑лог  
  Доказательство: `src/api/v1/routers/admin_rbac_management.py`.

## 8) Тесты и проверяемость

- Backend тесты (pytest) — в `tests/`.
- Frontend unit tests (vitest) — `frontend/`.
- Frontend e2e (Playwright) — `frontend/e2e/` (в частности omni‑чат).

## 9) Что обычно покупателю важно уточнить заранее (и как это подтвердить)

Этот раздел фиксирует “вопросы due diligence”, которые проверяются кодом/конфигом.

- **Какие каналы поддерживают исходящие ответы операторов?**  
  См. §5.2 (строго по `omni_outbound_policy.py` + dispatcher).
- **Как хранятся секреты интеграций/касс?**  
  Интеграции omni: `src/application/services/omnichannel_integrations_config_service.py` (encrypted + audit).  
  Платежные шлюзы: `src/application/services/clinic_payment_gateway_service.py` (encrypted).
- **Есть ли AI и как он включается/ограничивается?**  
  См. `src/application/services/omnichannel_ai_orchestrator.py` + admin toggle в `src/api/v1/routers/admin_omni_chat.py`.

---

## Appendix A — “Что входит в поставку”

Поставка репозитория включает:

- backend (`src/`)
- frontend (`frontend/`)
- docker compose окружение (`docker-compose.yml`)
- миграции БД (alembic)
- тесты backend+frontend

