# Тема UI (админка и PWA)

> **Версия:** 2026-04-02  
> **Источник в коде:** `frontend/src/theme.ts`, `frontend/src/index.css`, `frontend/src/main.tsx`, `frontend/src/app/layouts/AppLayout.tsx`.

## Название и принцип

Рабочая зона использует **светлую** тему **Mantine v7** с палитрой **Swiss Slate / Ink**: холодные нейтрали, акцент **brand** (графитово-синий), отдельные шкалы для success / warning / danger / info (blue), дополнительная шкала **ai** (фиолетовая) для AI-поверхностей.

Шрифт по умолчанию: **Inter** (подключение через `@fontsource/inter` в цепочке сборки).

## Где задаётся тема

| Файл | Роль |
|------|------|
| `frontend/src/theme.ts` | `createTheme`: цвета, тени, радиусы, типографика, переопределения `Paper` / `Card` / `Button` / `Table` / `Modal` и др. |
| `frontend/src/index.css` | Семантические CSS-переменные (`--bg-main`, `--text-main`, `--divider`, стекла для оверлеев и т.д.), классы зон (`app-patient-root`, маркетинг). |
| `frontend/src/main.tsx` | Корневой `MantineProvider` с `theme={appTheme}`, `defaultColorScheme="light"`. |
| `frontend/src/app/layouts/AppLayout.tsx` | Вложенный `MantineProvider` для PWA с `forceColorScheme="light"` и опциональной подстановкой `--font-family-app` из темы клиники. |

Админка и маркетинг используют тот же `appTheme`, что и корень приложения.

## Палитра Mantine (ключи)

В `theme.ts` зарегистрированы:

- **brand** и алиас **indigo** — одна шкала `swissInk` (primary ~ ink-700).
- **gray** — `slateCool` (фон приложения, границы, текст).
- **red** / **green** / **yellow** / **blue** — semantic danger / success / warning / info.
- **dark** — копия нейтральной шкалы (совместимость API Mantine).
- **ai** — отдельная фиолетовая шкала для AI-элементов.

## Тени

Объект `crispShadows` (xs → xl) — многослойные тени с холодным подтоном; используются как `theme.shadows` и в кнопках (например `filled`).

## Компоненты по умолчанию

Заданы в `theme.ts` (не дублировать «сырые» цвета там, где уже есть токены):

- **Text** — размер `sm` по умолчанию.
- **Badge** — `variant="light"`; для `filled` — фон/бордер из шкалы цвета.
- **Paper / Card** — белый фон, тонкая граница `gray-2`, `shadow="sm"`, `radius="sm"`.
- **Button** — `radius="sm"`, `fw=500`; вариант `default` — белая заливка и серая обводка.
- **Table** — отступы, подсветка строк, фон шапки `gray-0`.
- **Modal** — центрирование, лёгкий blur оверлея, контент с эффектом стекла (`--overlay-glass-surface`).

## Оболочки админки

- **`AdminDrawer`** (`frontend/src/shared/ui/AdminDrawer.tsx`) — единая оболочка выезжающих панелей для сущностей и форм. В админке **нельзя** импортировать «голый» `Drawer` из `@mantine/core` — это ловит ESLint (`eslint-restricted-ui-imports.mjs`).
- **`shellPanelStyles`** — общие стили оверлея/стекла для модалок и дроверов.

## Семантические CSS-переменные

В `index.css` заданы, среди прочего:

- Фон и карточки: `--bg-main`, `--bg-card`, `--bg-sidebar`.
- Текст: `--text-main`, `--text-muted`, `--text-on-primary`.
- Границы: `--divider`.
- Оверлеи: `--overlay-backdrop`, `--overlay-glass-surface`, тени `--shadow-soft-*`.

Лендинг и админские страницы опираются на эти переменные для согласованного «бумажного» вида.

## Персонализация клиники (PWA)

Тема клиники может подставлять **`theme_font_family`** и **`theme_primary_color`** (см. `AppLayout.tsx` и настройки в админке): корневой `--font-family-app` и акцент бренда в chrome пациентского приложения.

## Параллельный UI-kit

Добавление второго UI-фреймворка рядом с Mantine запрещено правилом `no-restricted-imports` (список пакетов в `frontend/eslint-restricted-ui-imports.mjs`). Обоснование — корневой **`DOCUMENTATION_POLICY.md`**.

## См. также

- [STRUCTURE.md](./STRUCTURE.md) — порядок файлов документации  
- [PRODUCT_KNOWLEDGE_BASE.md](./PRODUCT_KNOWLEDGE_BASE.md) §5 — маршруты зон UI
