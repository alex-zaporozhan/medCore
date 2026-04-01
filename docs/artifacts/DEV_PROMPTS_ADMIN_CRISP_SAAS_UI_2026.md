# DEV_PROMPTS — глобальный редизайн светлой админки (Crisp SaaS)

> **Роль:** исполняет @DEV (или агент с контекстом фронта).  
> **Канон:** `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md` §7 · **чеклист и токены:** `docs/ARCH_FRONTEND_UI_LOGIC.md` · **палитра Swiss Slate / Ink:** `docs/artifacts/85 plus/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6 · **стек/файлы:** `docs/artifacts/ARCH_FRONTEND_TECH_PASSPORT_DENTAL_BOOKING.md`.

**Цель одним абзацем:** вынести светлую рабочую зону админки на **Crisp SaaS** — серый фон уровня 0 (`#f4f6f8`), белые карточки с микрограницами, многослойные тени с подтоном ink, понятная иерархия кнопок (`filled` primary **brand/ink** vs белый `default`), активный пункт сайдбара с лёгким **brand.0**-тинтом, без тяжёлых сплошных заливок на KPI; при необходимости — класс `.glass-light` для sticky-шапок. В коде `primaryColor: "brand"`; `color="indigo"` — алиас той же шкалы.

**Вне скоупа (без отдельного согласования @LEAD):** смена IA/роутов; правки бэкенда; полный ребрендинг маркетингового лендинга (`TEMPLATE_DESIGN_UX.md`).

---

## 1. Порядок работ (рекомендуемый)

| Шаг | Что сделать | Зачем |
|-----|-------------|--------|
| 1 | Прочитать §7 техпаспорта и `ARCH_FRONTEND_UI_LOGIC.md` целиком | Единые ожидания |
| 2 | `frontend/src/theme.ts` — `shadows`, `Paper`/`Card`, `Button`, `primaryColor: brand` (шкала ink; опционально алиас `indigo`) | Глобальный эффект без правок каждой страницы |
| 3 | `frontend/src/index.css` — `:root` (`--bg-main` ≈ `gray.0`), переменные админ-навигации под §2.6 ARCH, класс `.glass-light` | Согласование с существующими `var(--admin-*)` |
| 4 | `AdminLayout.tsx` — убедиться, что main и сайдбар используют обновлённые токены; при смене активного состояния — **фон `brand.0` + текст/иконка `brand.6`** (или `indigo.*` как алиас) вместо/в дополнение к текущей полоске `.admin-nav-link` (не ломать collapsed-режим и бейджи) | Навигация читается с первого взгляда |
| 5 | `AdminDashboardPage.tsx` — KPI: единый белый каркас; блоки с градиентной заливкой (например Revenue Hunter) привести к **белой карточке** + акцент через `ThemeIcon`/семантику | §7.6 техпаспорта |
| 6 | Пройтись по страницам с явными `bg="dark.*"` / тяжёлыми градиентами в админке (поиск по репо) — выровнять | Консистентность |
| 7 | `npm run build`, `npm test` (frontend), визуальный смок: `/admin`, `/admin/omni-chat`, одна табличная страница | Регресс |

---

## 2. Критерии приёмки (Definition of Done)

- [ ] Фон main (`AppShell.Main` / `--bg-main`) визуально **не чисто белый**, а нейтральный серый уровня Mantine **`gray.0`** (Swiss: **`#f4f6f8`**).
- [ ] `createTheme.shadows` переопределены **многослойными** значениями из `ARCH_FRONTEND_UI_LOGIC.md` §2.2 (допустима лёгкая подстройка альфа).
- [ ] `Paper`/`Card` по умолчанию: рамка + согласованная тень `sm` (не «плоский» white на white без границы).
- [ ] `primaryColor: "brand"` (ink); главные CTA — `variant="filled"`; `default` — белый фон, видимая серая обводка, hover `gray.0` (через `Button.extend` в теме).
- [ ] В `index.css` добавлен `.glass-light` (как в ARCH §2.5); хотя бы одно осмысленное применение **или** явная пометка TODO с якорем на `ContextBar`/sticky-таблицы — по усмотрению @DEV, но класс должен существовать.
- [ ] Активный пункт левого меню: **brand.0 / brand.6** (через `--mantine-color-brand-*` или алиас indigo), без «грязной» серой подложки как единственного отличия.
- [ ] Дашборд: нет доминирующих сплошных цветных блоков на метриках; акцент — иконки/семантика.
- [ ] Сборка и тесты фронта зелёные; пациентское PWA (`/app`) не ломаем: сохранить **`forceColorScheme="light"`** там, где уже задано.

---

## 3. DEV_PROMPT_CRISP_UI_001 — единый промпт для Cursor / исполнителя

Скопировать блок ниже в задачу или чат агента как **единую** инструкцию.

```text
Ты — @DEV. Задача: глобально внедрить визуальную систему «Crisp SaaS» для светлой админки в репозитории dental_booking (frontend).

Источники правды (прочитай перед правками):
- docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md §7
- docs/ARCH_FRONTEND_UI_LOGIC.md (токены, чеклист, пути файлов)

Сделай изменения в коде:

1) frontend/src/theme.ts
- Установи primaryColor: "brand" и шкалу `colors.brand` (Swiss Slate / Ink); при необходимости `colors.indigo` = та же шкала для совместимости.
- Переопредели объект shadows многослойными значениями из docs/ARCH_FRONTEND_UI_LOGIC.md §2.2 (подтон ink, см. §3.6.4 концепта).
- Paper и Card: defaultProps — withBorder: true, белый фон, shadow: "sm", при необходимости styles.root с borderColor gray.2.
- Button: через Button.extend — для variant "default" белый фон, border gray.3, цвет текста gray.7, лёгкая тень xs, hover фон gray.0. Сохрани читаемость остальных variants (light, subtle, outline).

2) frontend/src/index.css
- Выровняй --bg-main с нейтральным фоном уровня 0 (Mantine gray.0 / #f4f6f8 или согласованно с темой).
- Обнови переменные админ-навигации (--admin-nav-active-* → `--mantine-color-brand-*`) так, чтобы активный пункт использовал лёгкий ink-тинт и brand.6 для текста/акцента; `--primary-alpha-*` из RGB ink (28,46,69), не синий #3b82f6. Сохрани доступность и контраст.
- Добавь класс .glass-light по тексту ARCH_FRONTEND_UI_LOGIC.md §2.5.

3) frontend/src/admin/layouts/AdminLayout.tsx
- Убедись, что AppShell.Main использует обновлённый фон (var(--bg-main) или theme.colors.gray[0]).
- Согласуй разметку нав-ссылок с новыми CSS-переменными; не ломай collapsed navbar и бейджи omni.

4) frontend/src/admin/pages/AdminDashboardPage.tsx
- Приведи карточки метрик к единому белому «листу» с рамкой/тенью по теме.
- Блоки с сильной градиентной заливкой (например карточка «Выручка, спасённая ИИ») упрости до белой карточки; акцент оставь через ThemeIcon/цвет текста, не через сплошной фон карточки.

5) Поиск по frontend/src/admin: исправь явные антипаттерны — тяжёлые сплошные цветные фоны на KPI/панелях там, где это очевидно нарушает §7 (без массового рефакторинга несвязанных экранов).

Ограничения:
- Не меняй бизнес-логику и API-вызовы.
- Не трогай маркетинговый лендинг и пациентское PWA кроме минимально необходимого для согласованности :root (если затронут общий body).
- После правок: npm run build && npm test в каталоге frontend.

В конце кратко перечисли изменённые файлы и что проверить глазами (/admin, одна страница с таблицей).
```

---

## 4. Опционально: разбивка на подзадачи (для трекера)

| ID | Содержание | Зависимость |
|----|------------|-------------|
| **CRISP-01** | `theme.ts` — shadows, Paper/Card/Button, brand (ink) primary | — |
| **CRISP-02** | `index.css` — :root, admin-nav, `.glass-light` | CRISP-01 желательно |
| **CRISP-03** | `AdminLayout.tsx` — main + nav | CRISP-02 |
| **CRISP-04** | `AdminDashboardPage.tsx` + точечный sweep админки | CRISP-01–03 |
| **CRISP-05** | CI: build + test | CRISP-04 |

---

## 5. После мержа (для @LEAD / @QA)

- Обновить скриншоты/запись в дизайн-доке, если есть обязательная визуальная регрессия по процессу.
- При существенном расхождении с `ARCH_FRONTEND_DESIGN_SYSTEM_MIDNIGHT.md` — завести эпик «синхронизация Midnight vs Crisp» или добавить приписку в шапку того документа (не блокер для первого merge).

---

Version: 1.1 | 2026-03-27 — Swiss Slate / Ink (`brand`), синхронизация с `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6
