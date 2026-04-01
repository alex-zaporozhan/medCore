# Runbook: миграции Alembic и заполнение БД демо-данными

**Назначение:** Запустить все миграции и заполнить БД данными на месяц назад и 1.5 месяца вперёд (записи, чаты, лиды, заметки, recall), чтобы продукт работал наглядно без пустых экранов.

**Требования:** PostgreSQL запущен, переменные окружения заданы (`.env` или `DATABASE_URL`). В проекте используется `poetry` для зависимостей (в т.ч. `asyncpg`).

---

## 1. Цепочка миграций

Активные миграции в `alembic/versions/` (от корня к голове):

| Порядок | Revision | Описание |
|--------|----------|----------|
| 1 | `schema_v2_initial` | Базовый полный схема v2 |
| 2 | `expand_alembic_ver_64` | Расширение `alembic_version.version_num` до 128 символов |
| 3 | `c3d4e5f6g7h8_erp_finance_inventory` | ERP: кассы, фин.операции, склады |
| 4 | `a1b2c3d4e5f6_form_link_tokens` | Токены для отправки форм по ссылке |
| 5 | `d5e6f7g8h9i0_package_family_links` | FamilyLink для пакетов лояльности |
| 6 | `e6f7g8h9i0j1_owner_integration_settings` | Настройки Owner Brief и AI Supervisor (Telegram) |

При первой установке или пустой БД выполняется вся цепочка от `schema_v2_initial` до головы.

---

## 2. Команды (по порядку)

Выполнять из корня репозитория.

### 2.1. Миграции Alembic

**Вариант A: полностью пустая БД (нет таблиц)**  
Выполнить один раз:

```bash
poetry run python -m alembic upgrade head
```

**Вариант B: БД уже создана из базовой схемы `schema_v2_initial` (все таблицы, включая `cashboxes`, уже есть)**  
Миграция `c3d4e5f6g7h8_erp_finance_inventory` создаёт те же таблицы, что и база. Чтобы не падать на "relation already exists", пометить ревизию как применённую и доехать до головы:

```bash
poetry run python -m alembic stamp c3d4e5f6g7h8_erp_finance_inventory
poetry run python -m alembic upgrade head
```

При успехе в консоли будет текущая ревизия (например `e6f7g8h9i0j1_owner_integration_settings`).

Цепочка: `expand_alembic_ver_64` зависит от `schema_v2_initial` (без промежуточной миграции `b2c3d4e5f6g7_clinic_gateways`). При расхождении истории с @ARCH согласовать вручную.

### 2.2. Базовые демо-данные (клиника, врачи, пациенты, услуги, админ)

```bash
poetry run python -m src.scripts.seed_demo_data
```

Создаёт одну клинику, 4 врачей, 10 пациентов, 10 услуг, одного админа (`admin@example.com` / `admin12345`).

### 2.3. Расширенное демо: записи, кассы, скидки, чаты, настройки владельца

```bash
poetry run python -m src.scripts.dev.seed_dev_full_demo
```

- Записи: **30 дней назад** (completed/cancelled/no_show/confirmed) + **45 дней вперёд** (pending/confirmed).
- Кассы и скидки при отсутствии.
- Платежи и финансовые операции по завершённым визитам.
- Настройки Owner integration (таблица `owner_integration_settings`) для клиники.
- **Чаты:** для 7 пациентов создаются диалоги (Conversation + несколько ChatMessage), чтобы раздел коммуникаций не был пустым.

### 2.4. Лиды, заметки, recall (CRM и маркетинг)

```bash
poetry run python -m src.scripts.dev.seed_dev_leads_notes_recall
```

- Воронка CRM (LeadPipeline + стадии) при отсутствии.
- Несколько лидов (LeadCard) с заметками (LeadNote).
- Сегмент, шаблон и кампания recall (RecallCampaign) и логи рассылки (RecallLog) для наглядного ROI.

### 2.5. Липовые финансы и искусственные чаты (без реальных продаж)

```bash
poetry run python -m src.scripts.dev.seed_dev_fake_finance_chats
```

- **Финансы:** только ручные операции (income/expense/transfer) без привязки к записям и платежам (`booking_id`/`payment_id` = null) — за 90 дней назад и 14 вперёд; для демо-отчётов без реальной кассы/продаж.
- **Чаты:** для каждого пациента без диалога создаётся беседа с 8–20 искусственными сообщениями (вопросы клиента, ответы админа, запись, напоминания, благодарности).

### 2.6. Персонал, задачи, касса (админы, роли, задачи, отчёты)

```bash
poetry run python -m src.scripts.dev.seed_dev_staff_tasks_cash
```

- **Права и роли:** при отсутствии создаются права (permissions) и глобальные роли (owner, manager, admin, doctor) с привязкой прав (RolePermission).
- **Админы:** добавляются 4 сотрудника — manager@example.com, executor1@example.com, executor2@example.com, reception@example.com (пароль для всех: `admin12345`). Первый админ — owner, второй — manager, остальные — admin (UserRole).
- **Задачи:** десятки задач (open, in_progress, done, cancelled) с назначенными, сроками, привязкой к записям/пациентам/лидам и комментариями (TaskComment).
- **Касса/отчёты:** дополнительные финансовые операции (income/expense/transfer) за последние 30 дней и вперёд — ручные расходы и доходы, переводы между кассами — чтобы отчёты и касса выглядели загруженными.

---

## 3. Итог

После выполнения всех шагов в БД есть:

- Клиника, врачи, пациенты, услуги, админ (+ менеджер, исполнители, рецепция — всего 5 админов с ролями).
- Записи на месяц назад и 1.5 месяца вперёд, с платежами и кассой.
- Чаты с сообщениями у части пациентов.
- Лиды с заметками и воронка.
- Recall-кампания с логами отправок.
- Настройки владельца (Owner Brief / AI Supervisor) — при включении в UI и указании `telegram_chat_id` рассылки будут уходить в Telegram.
- Задачи (tasks) с назначенными, сроками, комментариями и привязкой к записям/пациентам/лидам.
- Дополнительные операции по кассе (ручные доходы/расходы/переводы) для наглядных отчётов.
- Липовые финансы (только ручные операции без привязки к продажам) и искусственные чаты с клиентами (диалоги запись/вопросы/ответы).

---

## 4. Docker

Если приложение и БД поднимаются через Docker:

```bash
docker compose run --rm backend poetry run python -m alembic upgrade head
docker compose run --rm backend poetry run python -m src.scripts.seed_demo_data
docker compose run --rm backend poetry run python -m src.scripts.dev.seed_dev_full_demo
docker compose run --rm backend poetry run python -m src.scripts.dev.seed_dev_leads_notes_recall
docker compose run --rm backend poetry run python -m src.scripts.dev.seed_dev_staff_tasks_cash
docker compose run --rm backend poetry run python -m src.scripts.dev.seed_dev_fake_finance_chats
```

(Имя сервиса может быть `api` или `backend` — смотрите `docker-compose.yml`.)

---

## 5. Откат миграций (осторожно)

Откат на одну ревизию назад:

```bash
poetry run python -m alembic downgrade -1
```

Откат до базовой схемы (удалит все таблицы, созданные миграциями после неё):

```bash
poetry run python -m alembic downgrade schema_v2_initial
```

Данные в таблицах при откате теряются; сиды при необходимости нужно запускать заново после повторного `upgrade head`.
