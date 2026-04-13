# Архитектура светлой UI-логики админки (репозиторий)



**Назначение:** единая точка для **внедрения** норм светлой рабочей зоны и токенов **Swiss Slate / Ink** в этом репозитории. Общий канон UI-логики — `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md` (§1–6, **§7** светлая тема, **§8** Roadmap, **§9** Premium Micro-Design Codex — **эталон микро-вёрстки Mantine v7**). Маршруты и стек — `docs/artifacts/BUSINESS_ROUTES.md` и код (`frontend/`).



**Текущее состояние кода:** `frontend/src/theme.ts` — `primaryColor: "brand"` (шкала **ink**), многослойные тени с подтоном `rgba(15,20,25,…)`, ключ `indigo` в `colors` — **алиас** той же шкалы для обратной совместимости; `Paper`/`Card`/`Button` — см. шапку файла.



---



## 1. Файлы



| Файл | Роль |

|------|------|

| `frontend/src/theme.ts` | `createTheme`: `colors.brand` (ink), `colors.indigo` (алиас), `shadows`, `components` (`Paper`, `Card`, `Button`, `Modal`, …), `primaryColor` |

| `frontend/src/index.css` | Глобальные классы (например `.glass-light`), `:root` токены (`--primary`, `--focus-ring`, `--primary-alpha-*` из **RGB ink**) |

| `frontend/src/admin/layouts/AdminLayout.tsx` | Фон `AppShell.Main`, оболочка админки |

| Страницы с «тяжёлыми» виджетами | Например `frontend/src/admin/pages/AdminDashboardPage.tsx` — убрать сплошные цветные заливки в пользу белых карточек + цветные иконки |



---



## 2. Целевые токены (синхронизация с `TECH_PASSPORT` §7 и §3.6 Enterprise)



### 2.1. Фон и elevation



- **Уровень 0:** фон main — `gray.0` / **`#f4f6f8`** (Mantine `colors.gray[0]` или `--bg-main` / `--surface-app`).

- **Уровень 1:** карточки — белый фон `#ffffff` + граница `1px solid var(--mantine-color-gray-2)` (или `#e2e6ea`).



### 2.2. Тени (Crisp × Ink)



В `createTheme` заданы **многослойные** тени с холодным подтоном (не чистый `#000`), см. `docs/design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6.4:



- `xs`: `0 1px 2px rgba(15, 20, 25, 0.05)`

- `sm`: `0 1px 2px rgba(15,20,25,0.05), 0 4px 12px rgba(15,20,25,0.06)`

- `md`: `0 4px 8px rgba(15,20,25,0.06), 0 16px 40px rgba(15,20,25,0.08)`

- `lg` / `xl`: см. `theme.ts`



### 2.3. `Paper` / `Card`



- По умолчанию: `withBorder: true`, белый фон, `shadow: 'sm'` (или согласованное с §2.2), `radius` из темы.

- При необходимости явно задать `borderColor` через `styles.root` на `gray.2`.



### 2.4. Кнопки



- **`primaryColor`:** **`brand`** (шкала **ink** `#1c2e45` на индексе 6). Для существующих JSX с `color="indigo"` сохранён алиас `indigo` = та же шкала.

- **`Button` `variant="default"`:** белый фон, граница `gray.3`, текст `gray.7`, лёгкая тень `xs`; `:hover` — фон `gray.0`.

- **`variant="filled"`:** основные CTA; на странице — ограниченное число экземпляров.



### 2.5. Светлое стекло (sticky / context)



В `index.css` (или модуль стилей), класс для липких шапок таблиц и контекст-баров:



```css

.glass-light {

  background: rgba(255, 255, 255, 0.7);

  backdrop-filter: blur(12px);

  -webkit-backdrop-filter: blur(12px);

  border-bottom: 1px solid var(--mantine-color-gray-2);

}

```



При необходимости усилить непрозрачность до `0.85` для читаемости на плотных таблицах.



### 2.6. Sidebar — активный пункт



- Фон: **`brand.0`** (`#e8eef3`) или эквивалент из темы.

- Текст и иконка: **`brand.6`** (`#1c2e45`).

- CSS-переменные: `--admin-nav-active-*` в `index.css` ссылаются на `--mantine-color-brand-*`.

- Избегать нейтральной серой «подушки» без оттенка бренда для активного состояния.



### 2.7. Дашборд



- Все KPI-виджеты — единообразные белые карточки §2.1; акцент — **иконки/индикаторы тренда**, не сплошная заливка карточки (в т.ч. убрать тяжёлый единый синий блок, если он есть в разметке).



---



## 3. Чеклист внедрения (@FRONTEND)



1. [ ] `AppShell.Main` / обёртка main: фон `gray.0` / `#f4f6f8`.

2. [ ] `theme.ts`: `shadows` — значения §2.2; `primaryColor` → **`brand`**; шкала ink в `colors.brand`.

3. [ ] `theme.ts`: `Paper`/`Card` — дефолты с рамкой и согласованной тенью.

4. [ ] `theme.ts`: `Button` — стили для `default` §2.4.

5. [ ] `index.css`: `--primary`, `--focus-ring`, `--primary-alpha-*` из **RGB ink** (28, 46, 69); класс `.glass-light` §2.5.

6. [ ] `AdminLayout.tsx` (nav): активный пункт §2.6.

7. [ ] `AdminDashboardPage.tsx` (и аналоги): виджеты §2.7.



---



## 4. Смежные документы

- `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md` — полный канон UI (§7–§9).
- Унификация палитры — задачи @LEAD / @DESIGN; исторические промпты — git.
- `docs/TEMPLATE_DESIGN_UX.md` — только маркетинговые страницы, не админка.

Version: 1.4 | 2026-04-02 — ссылки обновлены после консолидации `docs/artifacts/`


