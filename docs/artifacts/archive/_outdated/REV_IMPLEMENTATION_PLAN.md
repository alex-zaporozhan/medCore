# REV_IMPLEMENTATION_PLAN — План введения революции UI/UX

> **Префикс REV_** — документы революции операционной системы.  
> **Назначение:** Сводный план внедрения элементов из TPF_MASTER и REV_RAG_MAP с фазами, артефактами и порядком работ. Согласован с REV_CRITERIA_IMPLEMENTATION.

**Точка входа для порядка шагов и ссылок на артефакты:** `REV_IMPLEMENTATION_RUNBOOK.md` — по каждой фазе: что делать по шагам и какие документы открыть.

**Входы:** `REV_CRITERIA_IMPLEMENTATION.md`, `TPF_MASTER.md`, `REV_ARCH_UI_VALUES.md`, `REV_RAG_MAP_INNOVATIONS.md`.

---

## Фаза 0 — Каркас (App Shell)

**Цель:** Единый каркас админки без глобального Header; тёмный Sidebar с Collapse и группами меню; Context Bar на каждой странице.

**Артефакты:**

- Обновить/переписать `AdminLayout.tsx` по `TPF_MODULE_SHELL.md`.
- Убрать `<AppShell.Header>`.
- Navbar: тёмный фон, кнопка Collapse (260px ↔ 80px), группы OPERATIONS / BUSINESS / SYSTEM.
- Main: светлый фон; контент в Paper. На каждой странице — Context Bar (заголовок + главные кнопки).

**Эндпойнты:** Не требуются.

**Критерий завершения:** Все админ-страницы открываются в новом каркасе; Sidebar сворачивается; заголовки и кнопки на месте.

**Ссылки:** TPF_MODULE_SHELL, REV_CRITERIA (P0).

---

## Фаза 1 — Универсальные законы

**Цель:** Drawer для всех созданий/редактирований; EmptyState и Skeleton на всех списках; ActionMenu в каждой таблице.

**Артефакты:**

- Вынести переиспользуемые компоненты: `EmptyState`, `PageSkeleton` (или аналог).
- Заменить все формы создания/редактирования сущностей на открытие в Drawer (справа, size lg/md). Modal оставить только для Confirm/Alert.
- На всех страницах со списками/таблицами: при `length === 0` рендер EmptyState с CTA; при загрузке — Skeleton вместо Loader.
- В каждой строке таблиц добавить ActionMenu (три точки) с действиями по сущности (Редактировать, Удалить, контекстные).

**Эндпойнты:** Существующие CRUD; при необходимости точечные эндпойнты для новых действий в Menu.

**Критерий завершения:** Нет таблицы без ActionMenu; нет пустого списка без EmptyState; нет полноэкранного Loader; редактирование только в Drawer.

**Ссылки:** TPF_MASTER (Часть I), REV_CRITERIA (P0, P1), REV_ARCH_UI_VALUES (паттерны 2.1, 2.2).

---

## Фаза 2 — Ключевые экраны

**Цель:** Dashboard с метриками, Attention Feed и таймлайн; OmniChat с Smart Inbox, Action Bar и контекстом клиента; Schedule с Drag-and-Drop и при необходимости Waitlist/Ghost Slots.

**Артефакты:**

- **Dashboard:** виджеты метрик (записи, выручка, лиды, отмены) с динамикой; левая колонка — Attention Feed с кнопками; правая — таймлайн на сегодня. См. TPF_MODULE_DASHBOARD.
- **OmniChat:** три колонки (Inbox с бейджами и фильтрами, переписка с AI Suggestions и Rich Bubbles, контекст клиента с «Создать запись»). Action Bar: Запись, Счёт, Анкета, AI вкл/выкл. См. TPF_MODULE_OMNICHAT.
- **Schedule:** сетка с Drag-and-Drop (оптимистичное обновление); боковая панель Waitlist; при создании записи опционально Ghost Slots. См. TPF_MODULE_SCHEDULE.

**Эндпойнты:** Агрегаты для метрик; attention-feed (или аналог); schedule на сегодня; чаты с флагами; suggest-replies (AI); пациент, next booking, lead stage для контекста; reschedule/booking CRUD.

**Критерий завершения:** Смена управляется с Dashboard; запись из чата без ухода со страницы; перенос записи в календаре мгновенный (Optimistic).

**Ссылки:** TPF_MODULE_DASHBOARD, TPF_MODULE_OMNICHAT, TPF_MODULE_SCHEDULE; REV_RAG_MAP (разделы 3, 4, 10).

---

## Фаза 3 — Глубина сущностей

**Цель:** Карточки Patient, Booking, Service, Doctor по матрице вкладок (TPF_MASTER, TPF_MODULE_ENTITIES).

**Артефакты:**

- Patient: Drawer с вкладками [Основное], [Визиты], [Финансы], [Медкарта/Заметки], [Коммуникации].
- Booking: Drawer с вкладками [Детали], [Услуги и чек], [Расходники], [Задачи].
- Doctor: Drawer с вкладками [Профиль], [Расписание], [Зарплата], [Услуги].
- Service: Drawer с вкладками [Описание], [Исполнители], [Техкарта], [Онлайн-запись].

**Эндпойнты:** Расширение GET by id с вложенными коллекциями (bookings, payments, notes, consumables, service_doctor и т.д.) или отдельные запросы по вкладкам.

**Критерий завершения:** Открытие любой из этих сущностей даёт Drawer с вкладками и полными данными; нет «коротких» форм.

**Ссылки:** TPF_MODULE_ENTITIES, TPF_MASTER (Часть III).

---

## Фаза 4 — CRM, задачи, финансы

**Цель:** CRM Kanban с суммами на столбцах и Lead Rotting; задачи с AI-пулом, My Focus и Time-Bomb; финансы (кассы, транзакции, Checkout Hub).

**Артефакты:**

- **CRM:** Kanban по LeadStage, агрегаты в шапке колонок, Lead Rotting, Drawer лида с чатом и кнопкой «Сгенерировать ссылку на предоплату». TPF_MODULE_CRM.
- **Tasks:** Режимы таблица/канбан; блок «Задачи от AI» с «Принять в работу»; My Focus с SLA и Time-Bomb; микро-действия в карточках. TPF_MODULE_TASKS.
- **Finance:** Таблица касс с действиями Внести/Изъять/Перевод; форма транзакции с обязательными полями; Checkout Hub при завершении визита (чек, касса, расходники). TPF_MODULE_FINANCE.

**Эндпойнты:** lead_stages, lead_cards (PATCH stage), агрегаты; tasks (source=ai, assignee, claim); cashbox, transactions; booking complete + payments + consumables.

**Критерий завершения:** Воронка и задачи работают по сценариям из техпаспорта; финансы проходят через кассу и техкарты; Relational Integrity для задач и транзакций.

**Ссылки:** TPF_MODULE_CRM, TPF_MODULE_TASKS, TPF_MODULE_FINANCE; REV_ARCH_UI_VALUES (таблица модулей).

---

## Фаза 5 — Spotlight, AI, дифференциаторы

**Цель:** Spotlight (Cmd+K) с поиском и опционально AI Command Line; виджет AI Revenue Hunter на Dashboard; при необходимости Retention (AI Segments, офферы), Omni-Vault (медиа, экспорт, бэкап), PWA 2.0.

**Артефакты:**

- Spotlight: интеграция @mantine/spotlight; поиск по разделам и пациентам/записям; вкладка «Спросить AI» (текст → вызов AI-агента). TPF_MODULE_SHELL.
- Dashboard: виджет «Спасённая выручка (AI)» при реализации Revenue Hunter. REV_RAG_MAP (раздел 16).
- По отдельным DEV_PROMPTS: Retention (сегменты, офферы, waterfall, ROI); Omni-Vault (галерея, транскрипты, Export Builder, Backup); PWA (Bottom Nav, Next Visit Ticket, Stories, Wallet). TPF_MODULE_PWA; REV_RAG_MAP (разделы 13, 14, 15).

**Эндпойнты:** search (или фильтрация); ai/agent или function-calling; Revenue Hunter (Celery + виджет); recall, media, export, backup по спецификациям.

**Критерий завершения:** По каждому подпункту — отдельный критерий в DEV_PROMPTS (Spotlight работает; виджет выручки отображается; и т.д.).

**Ссылки:** REV_RAG_MAP (разделы 2, 13–16), TPF_MODULE_PWA, REV_CRITERIA (P4, P5).

---

## Фаза 6 — The 1% Magic (Полировка UX)

**Цель:** Плавные анимации списков (Kanban, Лента внимания, задачи); микро-звуки на ключевые события с Mute; быстрые действия в Spotlight (Создать запись, Создать задачу, Отправить форму); опционально confetti при пустой Ленте внимания и микро-награда при крупной сделке.

**Артефакты:**

- **ARCH:** `docs/ARCH_PHASE6_MAGIC.md` — ADR, стек (@formkit/auto-animate, use-sound, react-confetti), ограничения (без новых API, Mute обязателен).
- **DEV:** `docs/dev_artifacts/DEV_ARTIFACT_F6_MAGIC.md` — пошагово: auto-animate на списках; звуки (success, pop, notification) + настройка Mute; группа «Быстрые действия» в Spotlight; опционально confetti и пульсация.

**Эндпойнты:** Не требуются.

**Критерий завершения:** Анимации на динамических списках; три звука привязаны к событиям, Mute в настройках; Spotlight открывает Drawer записи/задачи/формы по быстрым действиям; при желании — confetti при пустой Ленте.

**Ссылки:** ARCH_PHASE6_MAGIC, DEV_ARTIFACT_F6_MAGIC, REV_ARCH_UI_VALUES (микро-взаимодействия).

---

## Артефакты для передачи @DEV

Для каждой фазы (или подзадачи) создавать или обновлять:

- **DEV_PROMPTS_[НАЗВАНИЕ].md** — с явной ссылкой на TPF_MASTER и/или TPF_MODULE_*, нумерованными to-dos, контрактами API и критерием завершения (по протоколу @LEAD).
- В промптах указывать: «Вход: TPF_MASTER.md, TPF_MODULE_*.md. Действие: выполнить to-dos по порядку. Критерий: [конкретный пользовательский сценарий].»

---

## Порядок и зависимости

- Фаза 0 и 1 могут частично идти параллельно (каркас + первые EmptyState/Drawer на 1–2 страницах).
- Фаза 2 опирается на завершённые 0 и 1.
- Фаза 3 может стартовать после начала фазы 2 (карточки сущностей открываются из Schedule и Chat).
- Фаза 4 — после стабилизации API CRM, Tasks, Finance (BUSINESS_LOGIC_V2).
- Фаза 5 — по приоритету продукта; AI Command Line и Revenue Hunter требуют готовности AI-агента и бэкенд-процессов.
- Фаза 6 — после стабилизации фаз 0–5; только фронтенд, без новых API.

---

*При планировании спринтов брать блок из этого плана → сверить с REV_CRITERIA_IMPLEMENTATION (приоритет, стабильность API) → оформить DEV_PROMPTS со ссылками на TPF_* и REV_ARCH_UI_VALUES.*
