# REV_IMPLEMENTATION_RUNBOOK — Порядок реализации и артефакты по шагам

> **Назначение:** Единый документ, который диктует **что за чем следует** при реализации революции UI/UX и **собирает по ссылкам** все артефакты, нужные на каждом шаге. Точка входа для @LEAD и @DEV: открыл ранбук — видишь порядок и список документов для текущей фазы.

**Связь:** Детали фаз (критерии, эндпойнты, зависимости) — в `REV_IMPLEMENTATION_PLAN.md`. Приоритеты P0–P5 и чек-лист качества — в `REV_CRITERIA_IMPLEMENTATION.md`. **Пошаговые инструкции для @DEV** по каждой фазе — в стеке артефактов: `DEV_STACK_INDEX.md` и папка `docs/dev_artifacts/` (файлы `DEV_ARTIFACT_<ID>.md`). Здесь — порядок шагов и ссылки на TPF/REV; для кода — открывать соответствующий артефакт из стека.

---

## Как пользоваться

1. Выбери **текущую фазу** (0 → 1 → 2 → 3 → 4 → 5 → 6).
2. Открой **стек артефактов для @DEV:** `docs/DEV_STACK_INDEX.md`. В таблице найди артефакты для этой фазы (колонка «Фаза» / порядок по №).
3. Выполняй артефакты по порядку: открывай `docs/dev_artifacts/DEV_ARTIFACT_<ID>.md` и следуй пошаговым инструкциям. В каждом артефакте указаны входы (TPF/REV) и критерий приёмки.
4. На каждом шаге фазы при необходимости сверяйся с перечисленными ниже **артефактами (документы TPF/REV)** для правил и to-do.
5. Перед переходом к следующей фазе проверь **критерий приёмки** фазы и **зависимости** следующей фазы.

---

## Фаза 0 — Каркас (App Shell)

**Цель:** Единый каркас админки без глобального Header; тёмный Sidebar с Collapse и группами меню; Context Bar на каждой странице.

### Шаги (порядок выполнения)

| № | Действие |
|---|----------|
| 0.1 | Переписать/обновить `AdminLayout.tsx`: убрать `<AppShell.Header>`. |
| 0.2 | Navbar: тёмный фон (`dark.8`), кнопка Collapse (260px ↔ 80px), группы OPERATIONS / BUSINESS / SYSTEM по `TPF_MODULE_SHELL`. |
| 0.3 | Main: светлый фон (`gray.0`), контент в `Paper` с рамкой и радиусом. |
| 0.4 | На каждой админ-странице добавить Context Bar вверху контента (заголовок + главные кнопки). |
| 0.5 | Сохранять состояние сайдбара (развёрнут/свёрнут) в localStorage или контексте. |

### Артефакты (обязательно открыть для Фазы 0)

| Документ | Раздел / что смотреть |
|----------|------------------------|
| `docs/TPF_MODULE_SHELL.md` | Весь документ: структура AppShell, группы меню, Context Bar, Spotlight. |
| `docs/TPF_MASTER.md` | Часть II «Каркас приложения». |
| `docs/REV_CRITERIA_IMPLEMENTATION.md` | Таблица приоритетов: строка P0 (App Shell). |
| `docs/REV_RAG_MAP_INNOVATIONS.md` | Раздел 2 «Каркас приложения». |
| `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md` | Блок «0. КАРКАС ПРИЛОЖЕНИЯ» и to-dos по Shell (если используете). |

### Критерий приёмки

- Все админ-страницы открываются в новом каркасе; Sidebar сворачивается; заголовки и кнопки на месте. Новых API не требуется.

### Артефакты @DEV (пошаговые инструкции кода)

- **F0_SHELL:** `docs/dev_artifacts/DEV_ARTIFACT_F0_SHELL.md` — полная пошаговая реализация каркаса.

### Зависимости следующей фазы

- Фаза 1 опирается на завершённую Фазу 0 (можно частично параллелить 0 и 1).

---

## Фаза 1 — Универсальные законы

**Цель:** Drawer для всех созданий/редактирований; EmptyState и Skeleton на всех списках; ActionMenu в каждой таблице; базовый Spotlight (Cmd+K).

### Шаги (порядок выполнения)

| № | Действие |
|---|----------|
| 1.1 | Вынести переиспользуемые компоненты: `EmptyState`, `PageSkeleton` (или аналог). |
| 1.2 | Заменить все формы создания/редактирования сущностей на открытие в Drawer (справа, size lg/md). Modal — только для Confirm/Alert. |
| 1.3 | На всех страницах со списками/таблицами: при `length === 0` — EmptyState с CTA; при загрузке — Skeleton вместо Loader. |
| 1.4 | В каждой строке таблиц добавить ActionMenu (три точки) с действиями по сущности. |
| 1.5 | Подключить Spotlight (Cmd+K): плейсхолдер в сайдбаре, открытие по хоткею; пока — навигация по разделам (поиск по БД — при наличии API). |

### Артефакты (обязательно открыть для Фазы 1)

| Документ | Раздел / что смотреть |
|----------|------------------------|
| `docs/TPF_MASTER.md` | Часть I «Универсальные законы» (1.1–1.8); Часть V «Микро-взаимодействия». |
| `docs/TPF_MODULE_SHELL.md` | § 2.4 Spotlight; § 4 правила для разработчиков. |
| `docs/REV_CRITERIA_IMPLEMENTATION.md` | P0 (Drawer, EmptyState, Skeleton), P1 (ActionMenu, Spotlight); § 3 чек-лист на фичу. |
| `docs/REV_ARCH_UI_VALUES.md` | Паттерны 2.1 (Drawer > Modal), 2.2 (ActionMenu), 2.6 (Optimistic UI — на будущее). |
| `docs/REV_RAG_MAP_INNOVATIONS.md` | Раздел 1 «Универсальные паттерны»; раздел 2 (Spotlight, AI Command Line). |

### Критерий приёмки

- Нет таблицы без ActionMenu; нет пустого списка без EmptyState; нет полноэкранного Loader; редактирование только в Drawer; Cmd+K открывает Spotlight.

### Артефакты @DEV (пошаговые инструкции кода)

- **F1_COMPONENTS:** `docs/dev_artifacts/DEV_ARTIFACT_F1_COMPONENTS.md`  
- **F1_DRAWER:** `docs/dev_artifacts/DEV_ARTIFACT_F1_DRAWER.md`  
- **F1_EMPTY_SKELETON_APPLY:** `docs/dev_artifacts/DEV_ARTIFACT_F1_EMPTY_SKELETON_APPLY.md`  
- **F1_ACTION_MENU:** `docs/dev_artifacts/DEV_ARTIFACT_F1_ACTION_MENU.md`  
- **F1_SPOTLIGHT:** `docs/dev_artifacts/DEV_ARTIFACT_F1_SPOTLIGHT.md`  

### Зависимости следующей фазы

- Фаза 2 опирается на завершённые Фазы 0 и 1.

---

## Фаза 2 — Ключевые экраны

**Цель:** Dashboard (метрики, Attention Feed, таймлайн); OmniChat (Smart Inbox, Action Bar, контекст клиента); Schedule (Drag-and-Drop, Waitlist, опционально Ghost Slots).

### Шаги (порядок выполнения)

| № | Действие |
|---|----------|
| 2.1 | **Dashboard:** виджеты метрик (записи, выручка, лиды, отмены) с динамикой; левая колонка — Attention Feed с кнопками; правая — таймлайн на сегодня. |
| 2.2 | **OmniChat:** три колонки (Inbox с бейджами и фильтрами, переписка с AI Suggestions и Rich Bubbles, контекст клиента с «Создать запись»); Action Bar: Запись, Счёт, Анкета, AI вкл/выкл. |
| 2.3 | **Schedule:** сетка с Drag-and-Drop (оптимистичное обновление); боковая панель Waitlist; при создании записи опционально Ghost Slots. |

### Артефакты (обязательно открыть для Фазы 2)

| Документ | Раздел / что смотреть |
|----------|------------------------|
| `docs/TPF_MODULE_DASHBOARD.md` | Весь документ (структура, эндпойнты, правила UI). |
| `docs/TPF_MODULE_OMNICHAT.md` | Весь документ (три колонки, эндпойнты, правила UI). |
| `docs/TPF_MODULE_SCHEDULE.md` | Весь документ (сетка, Drag-and-Drop, Waitlist, Ghost Slots). |
| `docs/TPF_MASTER.md` | Разделы 4.1, 4.2, 4.3 (сводка по модулям). |
| `docs/REV_RAG_MAP_INNOVATIONS.md` | Разделы 3 (Dashboard), 4 (OmniChat), 10 (Schedule). |
| `docs/REV_CRITERIA_IMPLEMENTATION.md` | P2 (Dashboard, OmniChat, карточки); таблица согласования V2. |

### Критерий приёмки

- Смена управляется с Dashboard; запись из чата без ухода со страницы; перенос записи в календаре мгновенный (Optimistic).

### Зависимости следующей фазы

- Фаза 3 может стартовать после начала Фазы 2 (карточки сущностей открываются из Schedule и Chat).

---

## Фаза 3 — Глубина сущностей

**Цель:** Карточки Patient, Booking, Service, Doctor по матрице вкладок (без «коротких» форм).

### Шаги (порядок выполнения)

| № | Действие |
|---|----------|
| 3.1 | Patient: Drawer с вкладками [Основное], [Визиты], [Финансы], [Медкарта/Заметки], [Коммуникации]. |
| 3.2 | Booking: Drawer с вкладками [Детали], [Услуги и чек], [Расходники], [Задачи]. |
| 3.3 | Doctor: Drawer с вкладками [Профиль], [Расписание], [Зарплата], [Услуги]. |
| 3.4 | Service: Drawer с вкладками [Описание], [Исполнители], [Техкарта], [Онлайн-запись]. |

### Артефакты (обязательно открыть для Фазы 3)

| Документ | Раздел / что смотреть |
|----------|------------------------|
| `docs/TPF_MODULE_ENTITIES.md` | Весь документ (все четыре сущности, вкладки, правила). |
| `docs/TPF_MASTER.md` | Часть III «Матрица обогащённых сущностей» (3.1–3.4). |
| `docs/REV_RAG_MAP_INNOVATIONS.md` | Раздел 9 «Матрица обогащённых сущностей». |
| `docs/REV_CRITERIA_IMPLEMENTATION.md` | P2 (обогащённые карточки); таблица V2. |

### Критерий приёмки

- Открытие любой из сущностей даёт Drawer с вкладками и полными данными; нет «коротких» форм.

### Зависимости следующей фазы

- Фаза 4 — после стабилизации API CRM, Tasks, Finance (BUSINESS_LOGIC_V2).

---

## Фаза 4 — CRM, задачи, финансы

**Цель:** CRM Kanban (суммы на столбцах, Lead Rotting, Drawer чата); задачи (AI-пул, My Focus, Time-Bomb); финансы (кассы, транзакции, Checkout Hub, Liability); **Лояльность (Loyalty Engine):** раздел Loyalty, вкладка «Абонементы» и Family Sharing в Drawer пациента, Auto-Checkout, Digital Pass в PWA, Liability Dashboard.

### Шаги (порядок выполнения)

| № | Действие |
|---|----------|
| 4.1 | **CRM:** Kanban по LeadStage, агрегаты в шапке колонок, Lead Rotting, Drawer лида с чатом и кнопкой «Сгенерировать ссылку на предоплату». |
| 4.2 | **Tasks:** режимы таблица/канбан; блок «Задачи от AI» с «Принять в работу»; My Focus с SLA и Time-Bomb; микро-действия в карточках. |
| 4.3 | **Finance:** таблица касс (Внести/Изъять/Перевод); форма транзакции с обязательными полями; Checkout Hub при завершении визита; при API — Liability («деньги в воздухе»). |
| 4.4 | **Loyalty (Loyalty Engine):** раздел `/admin/loyalty`; в Drawer пациента вкладка «Абонементы» и Family Sharing; в Checkout Hub — подходящие абонементы и «Списать с абонемента»; в PWA — Digital Pass (карточки, «Записаться по абонементу»). |

### Артефакты (обязательно открыть для Фазы 4)

| Документ | Раздел / что смотреть |
|----------|------------------------|
| `docs/TPF_MODULE_CRM.md` | Весь документ. |
| `docs/TPF_MODULE_TASKS.md` | Весь документ. |
| `docs/TPF_MODULE_FINANCE.md` | Весь документ (кассы, техкарты, Checkout Hub). |
| `docs/TPF_MODULE_LOYALTY.md` | Весь документ (Digital Pass, Family Sharing, Auto-Checkout, Liability). |
| `docs/TPF_MASTER.md` | Разделы 4.4, 4.5, 4.6, 4.6b (Loyalty). |
| `docs/REV_RAG_MAP_INNOVATIONS.md` | Разделы 5 (CRM), 6 (Задачи), 7 (Финансы), 7b (Loyalty Engine). |
| `docs/REV_ARCH_UI_VALUES.md` | Таблица модулей: CRM, Tasks, Finance, Loyalty. |
| `docs/REV_CRITERIA_IMPLEMENTATION.md` | P3; таблица согласования V2 (CRM Kanban, ERP, RBAC & Tasks, Loyalty). |
| `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md` | Фаза B6 (Loyalty Engine) — контракт API. |

### Критерий приёмки

- Воронка и задачи работают по сценариям из техпаспорта; финансы проходят через кассу и техкарты; **раздел Лояльность и абонементы** (Digital Pass, Family Sharing, Auto-Checkout, Liability) по TPF_MODULE_LOYALTY и REV 7b; Relational Integrity для задач и транзакций.

### Зависимости следующей фазы

- Фаза 5 — по приоритету продукта; AI Command Line и Revenue Hunter требуют готовности AI-агента и бэкенд-процессов.

---

## Фаза 5 — Spotlight, AI, дифференциаторы

**Цель:** Spotlight с поиском и опционально AI Command Line; виджет AI Revenue Hunter; Retention; Omni-Vault; PWA 2.0.

### Шаги (порядок выполнения)

| № | Действие |
|---|----------|
| 5.1 | Spotlight: поиск по разделам и пациентам/записям; вкладка «Спросить AI» (текст → AI-агент). |
| 5.2 | Dashboard: виджет «Спасённая выручка (AI)» при реализации Revenue Hunter. |
| 5.3 | По отдельным DEV_PROMPTS: Retention (сегменты, офферы, waterfall, ROI); Omni-Vault (галерея, транскрипты, Export Builder, Backup); PWA (Bottom Nav, Next Visit Ticket, Stories, Wallet). |

### Артефакты (обязательно открыть для Фазы 5)

| Документ | Раздел / что смотреть |
|----------|------------------------|
| `docs/TPF_MODULE_SHELL.md` | § 2.4 Spotlight, AI Command Line. |
| `docs/TPF_MODULE_PWA.md` | Весь документ. |
| `docs/TPF_MASTER.md` | Разделы 4.8–4.12 (аналитика, лента, Retention, Omni-Vault, PWA). |
| `docs/REV_RAG_MAP_INNOVATIONS.md` | Разделы 2 (Spotlight, AI Command), 11 (Маркетинг), 12 (Mission Control), 13 (Retention), 14 (Omni-Vault), 15 (PWA), 16 (продвинутые фичи). |
| `docs/REV_CRITERIA_IMPLEMENTATION.md` | P4, P5; таблица V2 (AI Agent, Loyalty, Attribution и др.). |

### Критерий приёмки

- По каждому подпункту — отдельный критерий в DEV_PROMPTS (Spotlight работает; виджет выручки отображается; и т.д.).

### Зависимости следующей фазы

- Фаза 6 — только фронтенд; можно стартовать после завершения фаз 0–5.

---

## Фаза 6 — The 1% Magic (Полировка UX)

**Цель:** Плавные анимации списков; микро-звуки (success, pop, notification) с Mute; быстрые действия в Spotlight (Создать запись, Создать задачу, Отправить форму); опционально confetti при пустой Ленте внимания.

### Шаги (порядок выполнения)

| № | Действие |
|---|----------|
| 6.1 | Установить `@formkit/auto-animate`; применить хук к колонкам Kanban, списку задач, Ленте внимания (и при необходимости к слотам расписания). |
| 6.2 | Установить `use-sound`; добавить файлы в `public/sounds/` (success, pop, notification); привязать к событиям (завершение визита/задачи, drop в Kanban, новый алерт/сообщение); добавить переключатель Mute в настройках. |
| 6.3 | В Spotlight добавить группу «Быстрые действия»: Создать запись, Создать задачу, Отправить форму — по Enter открывать соответствующие Drawer. |
| 6.4 | (Опционально) Установить `react-confetti`; при пустой Ленте внимания — Empty State с кубком и короткий confetti; при желании — пульсация при сделке > 50 000 ₽. |

### Артефакты (обязательно открыть для Фазы 6)

| Документ | Раздел / что смотреть |
|----------|------------------------|
| `docs/ARCH_PHASE6_MAGIC.md` | Весь документ (ADR, стек, ограничения). |
| `docs/dev_artifacts/DEV_ARTIFACT_F6_MAGIC.md` | Пошаговые инструкции по всем четырём столпам. |
| `docs/REV_ARCH_UI_VALUES.md` | Микро-взаимодействия (если есть). |

### Критерий приёмки

- Анимации на динамических списках; три звука привязаны к событиям, Mute в настройках; Spotlight открывает Drawer записи/задачи/формы по быстрым действиям; при желании — confetti при пустой Ленте.

### Артефакты @DEV (пошаговые инструкции кода)

- **F6_MAGIC:** `docs/dev_artifacts/DEV_ARTIFACT_F6_MAGIC.md` — Fluid Animations, Acoustic UX, Action-Driven Spotlight, Gamification.

---

## Буфер задач (для @ARCH)

Задачи, запланированные в буфере для передачи @DEV. Перед реализацией @DEV открывает указанный артефакт и выполняет to-dos по порядку.

| Задача | Фаза | Артефакт @DEV | Описание |
|--------|------|----------------|----------|
| **Checkout Hub при завершении визита** | 4 | `docs/dev_artifacts/DEV_ARTIFACT_CHECKOUT_HUB.md` | При нажатии «Завершить» в списке записей открывать Drawer: запрос checkout-info, отображение подходящих абонементов, выбор «Списать с абонемента» или «Оплатить в кассу», вызов complete с опциональным `use_subscription_id`. |

---

## Сводная таблица: фаза → ключевые артефакты

| Фаза | Главные документы для открытия |
|------|--------------------------------|
| **0** | `TPF_MODULE_SHELL.md`, `TPF_MASTER.md` (Часть II), `REV_CRITERIA_IMPLEMENTATION.md` (P0), `REV_RAG_MAP_INNOVATIONS.md` (§2). |
| **1** | `TPF_MASTER.md` (Часть I, V), `TPF_MODULE_SHELL.md` (Spotlight), `REV_CRITERIA_IMPLEMENTATION.md` (P0–P1, чек-лист), `REV_ARCH_UI_VALUES.md` (паттерны). |
| **2** | `TPF_MODULE_DASHBOARD.md`, `TPF_MODULE_OMNICHAT.md`, `TPF_MODULE_SCHEDULE.md`, `REV_RAG_MAP_INNOVATIONS.md` (§3, 4, 10). |
| **3** | `TPF_MODULE_ENTITIES.md`, `TPF_MASTER.md` (Часть III), `REV_RAG_MAP_INNOVATIONS.md` (§9). |
| **4** | `TPF_MODULE_CRM.md`, `TPF_MODULE_TASKS.md`, `TPF_MODULE_FINANCE.md`, `TPF_MODULE_LOYALTY.md`, `REV_RAG_MAP_INNOVATIONS.md` (§5, 6, 7, 7b). |
| **5** | `TPF_MODULE_SHELL.md`, `TPF_MODULE_PWA.md`, `TPF_MASTER.md` (4.8–4.12), `REV_RAG_MAP_INNOVATIONS.md` (§2, 11–16). |
| **6** | `ARCH_PHASE6_MAGIC.md`, `DEV_ARTIFACT_F6_MAGIC.md`, `REV_ARCH_UI_VALUES.md`. |

---

## Связь с другими документами

- **Полное описание фаз (критерии, эндпойнты, зависимости):** `REV_IMPLEMENTATION_PLAN.md`.
- **Приоритеты и чек-лист качества:** `REV_CRITERIA_IMPLEMENTATION.md`.
- **Навигация по всем REV_/TPF_:** `REV_INDEX.md`.
- **Оформление задач для @DEV:** для каждой фазы создавать `DEV_PROMPTS_[НАЗВАНИЕ].md` со ссылками на артефакты из этого ранбука (см. раздел «Артефакты для передачи @DEV» в `REV_IMPLEMENTATION_PLAN.md`).

---

*Этот документ — точка входа для порядка реализации и сбора артефактов по шагам. Детали правил и API — в перечисленных TPF_* и REV_*.*
