## 🗂 ARCH_REAUDIT_BOARD_TEMPLATE — борд для полного реаудита

> Этот файл — готовый шаблон для Jira / Notion / Trello.  
> Его можно:
> - скопировать как таблицу в Notion / Confluence;
> - импортировать в Jira/Trello (через CSV) после небольшого форматирования;
> - использовать как «источник правды» по структуре борда.

---

## 1. Колонки борда (статусы / списки)

Рекомендуемая структура колонок:

- **BACKLOG** — всё, что ещё не взято в работу.
- **IN PROGRESS** — активные задачи реаудита (по фазам).
- **REVIEW** — артефакт написан, ждёт просмотра @LEAD/@ARCH.
- **DONE** — утверждённые артефакты и закрытые аудиты.

Внутри каждой задачи в поле `Phase` хранится одна из фаз F1…F7:

- `F1 — Business inventory`
- `F2 — Routes & UX flows`
- `F3 — Backend audit`
- `F4 — Frontend audit`
- `F5 — QA / UX gaps`
- `F6 — Non-functional audit`
- `F7 — Refactoring roadmap`

---

## 2. Роли и ответственные (для быстрого назначения)

Заполни реальными именами/командами:

```text
@LEAD          = <ФИО / команда>
@DOMAIN_EXPERT = <ФИО / команда>
@BACKEND_ARCH  = <ФИО / команда>
@FRONT_ARCH    = <ФИО / команда>
@QA_ARCH       = <ФИО / команда>
@SEC_ARCH      = <ФИО / команда>
@DEVOPS        = <ФИО / команда>
```

Эти псевдонимы можно использовать в описаниях задач и в Jira components/labels.

---

## 3. Ключевые ссылки (добавить в Description борда / Wiki)

Рекомендация: создать отдельную страницу «Dental Booking — Reaudit» и вставить туда:

- `./ARCH_REAUDIT_PLAYBOOK.md`
- [`../../artifacts/BUSINESS_LOGIC.md`](../../artifacts/BUSINESS_LOGIC.md) (актуальный канон бизнес-логики)
- [`../../artifacts/BUSINESS_ROUTES.md`](../../artifacts/BUSINESS_ROUTES.md) (маршруты и UX-срезы)

Также можно привести прямые ссылки на репозиторий и CI.

---

## 4. Шаблон задач (CSV / таблица для импорта)

Ниже — минимальный набор задач для старта. Колонки:  
`Key,Summary,Description,Assignee,Phase,Status,Labels`

```text
Key,Summary,Description,Assignee,Phase,Status,Labels
F1-1,F1: Обновить ARCH по доменам,"Пройти по docs/artifacts/BUSINESS_LOGIC.md и при необходимости архивным ARCH_*_NEXT.md, создать/обновить ARCH_*.md по доменам (Booking, CRM, ERP, Loyalty, Paperless, Tasks, Omnichannel, Marketing/Recall/Attribution).",@DOMAIN_EXPERT,F1,BACKLOG,arch,domain
F1-2,F1: Свести отличия CURRENT vs V2,"Для каждого домена зафиксировать, что реализовано сейчас и что является целью V2 (в отдельном разделе в ARCH_*.md).",@DOMAIN_EXPERT,F1,BACKLOG,arch,domain
F2-1,F2: Описать UX-флоу пациента,"На базе BUSINESS_ROUTES и кода описать ключевые сценарии пациента (регистрация, запись, история, чат, лояльность, формы) в UX_FLOWS_AND_GAPS.md.",@FRONT_ARCH,F2,BACKLOG,ux,front
F2-2,F2: Описать UX-флоу администратора,"Описать сценарии администратора (расписание, лист ожидания, чаты, CRM, финансы, задачи, отчёты) и зафиксировать дыры (пустые окна, UUID и т.п.).",@FRONT_ARCH,F2,BACKLOG,ux,front
F3-1,F3: Backend-аудит Booking/Prepayment/Payments,"Проанализировать сервисы и роутеры Booking/Prepayment/Payments, сверить с инвариантами (один слот — одна запись, политики предоплаты и т.п.), оформить BACKEND_GAPS_Booking.md.",@BACKEND_ARCH,F3,BACKLOG,backend,booking
F3-2,F3: Backend-аудит CRM,"Проанализировать admin_crm + LeadService: соответствие Sales/Kanban из BUSINESS_LOGIC_V2, автодвижения по событиям, оформить BACKEND_GAPS_CRM.md.",@BACKEND_ARCH,F3,BACKLOG,backend,crm
F3-3,F3: Backend-аудит ERP (Finance/Payroll/Inventory),"Проверить транзакционный узел при завершении визита и ERP-сервисы, оформить BACKEND_GAPS_ERP.md.",@BACKEND_ARCH,F3,BACKLOG,backend,erp
F3-4,F3: Backend-аудит Loyalty,"Проанализировать admin_loyalty/patient_loyalty + LoyaltyService, оформить BACKEND_GAPS_Loyalty.md.",@BACKEND_ARCH,F3,BACKLOG,backend,loyalty
F3-5,F3: Backend-аудит Tasks & AttentionFeed,"Проверить Task и AttentionFeedService, соответствие AI Task Manager из V2, оформить BACKEND_GAPS_Tasks.md.",@BACKEND_ARCH,F3,BACKLOG,backend,tasks
F3-6,F3: Backend-аудит AI Agent,"Проверить ai_agent роутер, AiClient/Omnichannel, зафиксировать, что реализовано (stubs vs целевой function calling), оформить BACKEND_GAPS_AI_Agent.md.",@BACKEND_ARCH,F3,BACKLOG,backend,ai
F4-1,F4: Frontend-аудит PWA /app,"Проверить все страницы /app и хуки: консистентность UX, отображение имён/статусов, пустые состояния, оформить FRONTEND_GAPS_AppPWA.md.",@FRONT_ARCH,F4,BACKLOG,front,pwa
F4-2,F4: Frontend-аудит админки /admin,"Пройти по всем страницам админки, свериться с ARCH/UX_FLOWS, оформить FRONTEND_GAPS_Admin.md.",@FRONT_ARCH,F4,BACKLOG,front,admin
F5-1,F5: QA-прогон ролей,"Сделать смоук- и регрессионный прогон ключевых сценариев пациента/админа/owner, оформить QA_GAPS_RUN_<date>.md.",@QA_ARCH,F5,BACKLOG,qa
F6-1,F6: Security & non-functional audit,"Проверить секреты, авторизацию, перфоманс ключевых эндпоинтов, наблюдаемость; оформить NONFUNCTIONAL_AUDIT.md.",@SEC_ARCH,F6,BACKLOG,security,perf
F7-1,F7: Собрать REFACTORING_ROADMAP,"На основе всех *_GAPS_* и *_AUDIT*.md сформировать REFACTORING_ROADMAP.md с пакетами улучшений и приоритизацией.",@LEAD,F7,BACKLOG,lead,roadmap
```

---

## 5. Как использовать этот шаблон

- **Jira:**
  - Скопировать блок CSV в `.csv` файл.
  - В импорте Jira выбрать колонки `Summary`, `Description`, `Assignee`, `Status`, `Labels` и кастомное поле `Phase`.
  - После импорта расставить реальные аккаунты вместо псевдонимов.

- **Notion / Trello:**
  - Скопировать таблицу из блока CSV в виде текста.
  - Вставить как таблицу/board.
  - Преобразовать колонку `Status` в колонки борда.

После этого борд будет полностью соответствовать `ARCH_REAUDIT_PLAYBOOK.md`,  
и можно сразу начинать работу по фазам F1–F7.

