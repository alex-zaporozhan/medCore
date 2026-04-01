# DEV_ARTIFACT_F0_SHELL — App Shell и Context Bar

> **Фаза:** 0  
> **Зависимости:** нет  
> **Оценка:** 1–1.5 дня

---

## 1. Цель

Перестроить каркас админки: убрать глобальный Header; сделать тёмный Sidebar (Navbar) с кнопкой Collapse (260px ↔ 80px) и группами меню OPERATIONS / BUSINESS / SYSTEM; светлый Main с контентом в Paper; на каждой админ-странице — Context Bar вверху (заголовок + главные кнопки). Состояние сайдбара (развёрнут/свёрнут) сохранять в localStorage.

---

## 2. Входы (обязательно открыть перед выполнением)

| Документ | Раздел / что смотреть |
|----------|------------------------|
| `docs/TPF_MODULE_SHELL.md` | Весь документ: § 2.1 AppShell (без Header, Navbar, Main), § 2.2 группы навигации, § 2.3 Context Bar, § 4 правила. |
| `docs/TPF_MASTER.md` | Часть II «Каркас приложения». |
| `docs/REV_RAG_MAP_INNOVATIONS.md` | Раздел 2 «Каркас приложения». |

---

## 3. Предусловия

- [ ] В проекте используется Mantine `AppShell`, роутинг через `Outlet` в `AdminLayout.tsx`.
- [ ] Текущий layout: `frontend/src/admin/layouts/AdminLayout.tsx` (есть Header, Navbar, Main).

---

## 4. Пошаговые инструкции

### Шаг 4.1. Удалить AppShell.Header и перенести выбор клиники/выход в Navbar

**Файл:** `frontend/src/admin/layouts/AdminLayout.tsx`

**Действие:**

1. Удалить весь блок `<AppShell.Header>...</AppShell.Header>` (включая выбор клиники, «На главную», «Выйти»).
2. В `AppShell` убрать проп `header={{ height: 60 }}` — заголовка больше нет.
3. Выбор клиники и ссылки «На главную» / «Выйти» перенести в **верхнюю часть Navbar** (внутрь `<AppShell.Navbar>`): компактный блок сверху (Select клиники + две ссылки). Использовать те же компоненты (`Select`, `Anchor`, `Group`), стилизовать под тёмный фон (светлый текст, полупрозрачные границы при необходимости).

**Проверка:** После перезагрузки страницы нет верхней шапки; выбор клиники и выход доступны из сайдбара.

---

### Шаг 4.2. Задать тёмный фон Navbar и ширину с поддержкой Collapse

**Файл:** `frontend/src/admin/layouts/AdminLayout.tsx`

**Действие:**

1. Добавить состояние для свёрнутого сайдбара, например:
   - `const [navbarCollapsed, setNavbarCollapsed] = useState(() => { ... read from localStorage key `admin_navbar_collapsed` ... });`
   - При переключении вызывать `localStorage.setItem('admin_navbar_collapsed', ...)`.
2. Задать `navbar` в `AppShell`:
   - Ширина: развёрнуто `260`, свёрнуто `80` (использовать `navbarCollapsed ? 80 : 260`).
   - Не использовать `breakpoint` для скрытия на мобильных, если в ТЗ не указано иное — только ручное Collapse.
3. Стили Navbar:
   - Фон: `backgroundColor: 'var(--mantine-color-dark-8)'` или, если в теме есть, `var(--bg-dark)`. Иначе задать в `theme` или CSS переменную `--bg-dark` (тёмный цвет, например `#1a1b1e`).
   - Текст и иконки: светлые, например `color: 'var(--mantine-color-gray-3)'` или `var(--text-sidebar)`.

**Проверка:** Сайдбар тёмный; ширина меняется 260 / 80 в зависимости от состояния (пока переключение можно сделать заглушкой кнопки — шаг 4.4).

---

### Шаг 4.3. Перегруппировать пункты меню по OPERATIONS / BUSINESS / SYSTEM

**Файл:** `frontend/src/admin/layouts/AdminLayout.tsx`

**Действие:**

1. Заменить текущий `navGroups` на три группы с заголовками (uppercase, мелкий шрифт):
   - **OPERATIONS:** Dashboard (`/admin`), Schedule & Bookings (`/admin/schedule`), Chat & AI (`/admin/omni-chat`).
   - **BUSINESS:** CRM & Sales (`/admin/sales`), Finance & ERP (`/admin/finance`), Loyalty (`/admin/loyalty`), Tasks (`/admin/tasks`), Analytics (`/admin/reports`).
   - **SYSTEM:** Настройки, Команда, интеграции — сгруппировать существующие пункты (Settings, Administrators, Integrations, Channels, …) под заголовком SYSTEM.
2. В рендере каждой группы: сначала вывести заголовок группы — `<Text size="xs" tt="uppercase" c="gray.5" fw={600} mb={4}>OPERATIONS</Text>` (или аналог), затем список ссылок.
3. Активный пункт меню: если `location.pathname === item.to`, применять стиль `backgroundColor: 'var(--mantine-color-indigo-6)'`, `color: 'white'` (или `bg="indigo.6"` `c="white"` в Mantine).
4. В свёрнутом состоянии (80px) показывать только иконки (без текста и без заголовков групп). Для каждого пункта использовать одну иконку (например из `@tabler/icons-react`: IconDashboard, IconCalendar, IconMessageCircle, IconBriefcase, IconCash, IconGift, IconListCheck, IconChartBar, IconSettings и т.д.). Текст и заголовки групп при `navbarCollapsed` скрыть.

**Проверка:** В развёрнутом виде видны три группы с подписями OPERATIONS, BUSINESS, SYSTEM; активный пункт подсвечен; в свёрнутом виде только иконки.

---

### Шаг 4.4. Кнопка Collapse внизу Navbar

**Файл:** `frontend/src/admin/layouts/AdminLayout.tsx`

**Действие:**

1. Внизу `<AppShell.Navbar>` (после всех групп) добавить кнопку (например `ActionIcon` или `Button` variant subtle):
   - Иконка: при развёрнутом — «свернуть» (например `IconChevronLeft`), при свёрнутом — `IconChevronRight`.
   - По клику: `setNavbarCollapsed(prev => !prev)` и запись в `localStorage`.
2. Разметку Navbar сделать так, чтобы эта кнопка была прижата к низу (например `flex` контейнер с `flex: 1` у блока с меню и кнопка внизу).

**Проверка:** Клик по кнопке сворачивает/разворачивает сайдбар; после перезагрузки страницы состояние сохраняется.

---

### Шаг 4.5. Main: светлый фон и обёртка контента в Paper

**Файл:** `frontend/src/admin/layouts/AdminLayout.tsx`

**Действие:**

1. У `AppShell.Main` задать фон: `backgroundColor: 'var(--mantine-color-gray-0)'` (или `var(--bg-main)` светлый).
2. Контент внутри Main (сейчас `<Container size="xl" py="md">`) обернуть так, чтобы сам `Outlet` рендерился внутри обёртки с фоном и рамкой:
   - Вариант: обернуть `<Outlet />` в `<Paper radius="xl" p="md" withBorder style={{ border: '1px solid var(--mantine-color-gray-2)' }}>...</Paper>`.
   - Либо задать стили контейнера: фон белый/серый, `borderRadius: theme.radius.xl`, `border: '1px solid ...'`. Итог: контент страниц визуально в «карточке» с тонкой рамкой и скруглением.

**Проверка:** Рабочая зона светлая; контент страницы внутри блока с рамкой и скруглением.

---

### Шаг 4.6. Context Bar на каждой админ-странице

**Файл(ы):** Все страницы, которые рендерятся через `<Outlet />` из AdminLayout (например `AdminDashboardPage.tsx`, `AdminPatientsPage.tsx`, `AdminTasksPage.tsx`, …). Список брать из роутов админки (см. `App.tsx` или роутер).

**Действие:**

1. На **каждой** такой странице вверху контента (первым блоком внутри страницы) добавить Context Bar:
   - Слева: заголовок страницы (например `<Title order={3}>Пациенты</Title>` или текущее название раздела).
   - Справа: одна или несколько главных кнопок действия (например «Новая запись», «Создать задачу», «Добавить пациента»). Использовать `Group justify="space-between" mb="md"` (или аналог).
2. Если на странице уже есть заголовок и кнопка — привести к единому виду: один ряд, слева заголовок, справа действия.
3. Минимальный набор страниц для проверки: Dashboard, Schedule, Omni-Chat, Patients, Tasks, Finance, Settings (или их текущие пути). Остальные страницы перечислить и добавить Context Bar по тому же правилу.

**Проверка:** На любой открытой админ-странице вверху виден заголовок и кнопка(и) действия; глобальной шапки нет, контекст задаётся страницей.

---

## 5. Критерий приёмки

- [ ] Глобальный `<AppShell.Header>` удалён; выбор клиники и «Выйти» доступны из сайдбара.
- [ ] Navbar тёмный; ширина 260px (развёрнуто) / 80px (свёрнуто); состояние сохраняется в localStorage.
- [ ] Меню сгруппировано: OPERATIONS, BUSINESS, SYSTEM с заголовками; активный пункт с акцентом (indigo.6); в свёрнутом виде только иконки.
- [ ] Внизу сайдбара кнопка Collapse; по клику сайдбар сворачивается/разворачивается.
- [ ] Main светлый; контент в блоке с рамкой и радиусом (Paper или аналог).
- [ ] На каждой админ-странице вверху — Context Bar (заголовок слева, кнопки справа).

---

## 6. Ссылки на архитектуру

- Техпаспорт: `docs/TPF_MODULE_SHELL.md`
- RAG: `docs/REV_RAG_MAP_INNOVATIONS.md`, раздел 2
- Runbook: `docs/REV_IMPLEMENTATION_RUNBOOK.md`, Фаза 0
