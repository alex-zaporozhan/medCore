# Дизайн-паспорт: маркетинговый лендинг

> **Версия:** 2026-04-10  
> **Роли:** @DESIGN (визуальный канон и приёмка) · @LEAD (ворота) · @FRONTEND (реализация)  
> **Контур:** публичный маркетинг (не админка, не PWA пациента)

---

## 1. Назначение документа

Фиксирует **визуальный и композиционный контракт** главной маркетинговой страницы: палитра, типографика, иерархия CTA, каркас секций и связь с токенами темы. Для инженерного паспорта маршрута (хуки, API, RBAC) см. [`docs/frontend/pages/marketing-landing.md`](../frontend/pages/marketing-landing.md) — при расхождении **источник правды по визуалу — этот файл и код**, перечисленный в §7.

---

## 2. Метаданные экрана

| Поле | Значение |
|------|----------|
| **Path** | `/` (`ROUTE_PATHS.marketing.landing`) |
| **Компонент** | `frontend/src/marketing/pages/MarketingLandingPage.tsx` |
| **Стили страницы** | `frontend/src/marketing/pages/marketingLanding.css` (импорт в компоненте) |
| **Корневой класс** | `marketing-landing page-gradient` на `<main>` |
| **Смежные маршруты того же визуального контура** | `/pricing`, `/signup`, публичный вход (`SignInShell` + `PublicLoginPage`), фон `.marketing-gradient-bg` в `frontend/src/index.css` |

---

## 3. Принципы (согласованы с каноном Enterprise)

- **Один непрерывный фон** страницы; секции отделяются вертикальным ритмом и карточками, без «зебры» фонов (см. [`docs/TEMPLATE_DESIGN_UX.md`](../TEMPLATE_DESIGN_UX.md) §3.5).
- **Нейтраль = основа:** белые/серые поля, графитовый текст; **корпоративный акцент (slate)** — в первичных действиях и ключевых обводках, а не заливками больших площадей.
- **Семантика цвета:** зелёный акцент для метки «рекомендуемый тариф» (стабильность / деньги), не для основного бренда кнопок.

Подробная философия палитры и ролей: [`DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md`](./DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md) §3.2, §3.6 (маркетинг использует ту же шкалу **slate** как primary в коде).

---

## 4. Палитра и токены (as-built в коде)

### 4.1. Корпоративный primary — Swiss Slate (`slate` в Mantine)

Кортеж в `frontend/src/theme.ts` (индексы 0–9):

| Index | Hex | Роль на лендинге |
|-------|-----|------------------|
| 0 | `#f1f5f9` | Светлые подложки, mix в градиентах карточек |
| 6 | `#334155` | Иконки в карточках возможностей / преимуществ (`ThemeIcon` + `slate`, списочные маркеры `slate.6`) |
| 7 | `#2a3843` | **Заливка primary-кнопок** (filled) |
| 8 | `#1e293b` | **Hover** primary-кнопок |
| 9 | `#0f172a` | Активное состояние кнопки, глубокий текст заголовков |

`primaryColor: "slate"`, `primaryShade: 7`. Алиасы **`brand`** и **`indigo`** в теме указывают на тот же кортеж (совместимость админки и старых пропсов).

### 4.2. Кнопки

- **Primary (filled):** Mantine `Button` `variant="filled"` `color="slate"` (или без `color`, если используется primary по умолчанию). В теме для `slate` / `brand` / `indigo` заданы явные фон **[7]** и hover **[8]**.
- **Вторичные:** `variant="outline"` / `light` / `subtle` с `gray` или `slate` по контексту; не смешивать три разных «главных» цвета на одном экране.

### 4.3. Заголовки H1 / H2

Целевой цвет текста: **`#0f172a`** (почти чёрный, строгий). Задаётся через `Title.extend` в `theme.ts` для `order` 1 и 2; на лендинге не переопределять цвет inline без причины.

### 4.4. Тариф «рекомендуемый»

- Плашка **«РЕКОМЕНДУЕМ»:** `teal.7` (приглушённый тёмно-зелёный, отдельно от primary slate).
- Обводка и градиент featured-карточки: токены **`slate`**, не синий info (см. `marketingLanding.css` — класс `marketing-pricing-card--featured`).

### 4.5. CSS-переменные маркетинга

Глобальные маркетинговые подложки: класс **`.marketing-gradient-bg`** в `frontend/src/index.css` (радиальные блики в нейтрали + лёгкий teal; без индиго).

---

## 5. Типографика

| Элемент | Реализация | Правило |
|---------|------------|---------|
| Латиница H1–H2 на лендинге | `Plus Jakarta Sans` (подключение в компоненте + правила в `marketingLanding.css`) | Кириллица уходит в fallback `Inter` из темы |
| Остальной текст | `Inter` из `theme.ts` `fontFamily` | Единый с админкой базовый гротеск |
| Hero H1 | `Title order={1}` + `clamp` в `style` | Один главный H1 на странице |
| Секции | `Title order={2}` | Единый ритм, `letterSpacing` при необходимости |
| Карточки | `Title order={3}` | Короче секционных |
| Eyebrow | `Text size="xs" tt="uppercase" fw={700}` `c="dimmed"` | Над hero и секциями |

---

## 6. Композиция секций (сверху вниз)

| # | Секция | Дизайн-контракт |
|---|--------|-----------------|
| 1 | **Sticky header** | Полупрозрачный светлый бар, нижняя граница; логотип/название слева; навигация + **primary CTA** «Подключить организацию» справа |
| 2 | **Hero** | Двухколоночная сетка: слева eyebrow, H1, лид, **две CTA** (демо — filled slate; тарифы — outline); справа **пьедестал** с product shot (`marketing-hero-*` классы), 3D-лёгкий наклон, крупная тень, `prefers-reduced-motion` сбрасывает transform |
| 3 | **Аудитории** | Сетка карточек `marketing-bento-card`; иконки **gray** (нейтральный блок) |
| 4 | **Возможности** | Блок `marketing-bento-section`; карточки `marketing-capability-card`; иконки **slate** (иконка ≈ `#334155`) |
| 5 | **Преимущества** | Список групп с иконкой слева, тот же **slate** для иконок |
| 6 | **Тарифы** | Карточки `marketing-pricing-card`; featured — `marketing-pricing-card--featured`; список фич с маркерами `slate.6`; CTA рядом с планом |
| 7 | **Enterprise** | Пунктирная обводка, вторичная кнопка (outline slate / dark по контексту — не конкурировать с главным slate CTA) |
| 8 | **Нижний CTA** | Повтор primary «Подключить организацию» + ссылки |

Модальные поверхности: **`EnterpriseLeadModal`** (триггер с лендинга — уточнить в коде по `openEnterprise`).

---

## 7. Карта «дизайн → код»

| Тема | Файл / символ |
|------|----------------|
| Тема Mantine, slate, кнопки, Title H1/H2 | `frontend/src/theme.ts` |
| Глобальные primary / marketing gradient | `frontend/src/index.css` |
| Лендинг разметка и контент секций | `frontend/src/marketing/pages/MarketingLandingPage.tsx` |
| Bento, hero, pricing card стили | `frontend/src/marketing/pages/marketingLanding.css` |
| Планы и копирайт карточек (данные) | `frontend/src/marketing/marketingPublicPlans.ts` |
| Публичные URL hero | `frontend/src/marketing/landingPublicAssets.ts`, `frontend/public/marketing/` |

Общая навигация дизайн-системы: [`DESIGN_CODE_MAP.md`](./DESIGN_CODE_MAP.md).

---

## 8. Состояния, a11y, motion

- **Focus:** кольцо через токены `--focus-ring` (slate-tinted в `index.css`).
- **Motion:** в `marketingLanding.css` для bento и hero заданы transitions; при `prefers-reduced-motion: reduce` — отключение transform на hero и transition на bento-card.
- **Изображения:** hero — `loading="eager"`, цепочка fallback URL + SVG; осмысленный `alt` на русском.

---

## 9. Чеклист приёмки (@DESIGN / @LEAD)

- [ ] Primary CTA визуально **slate [7]**, hover **темнее [8]**, без «дешёвого» насыщенного синего/индиго.
- [ ] H1 и H2 — **строгий тёмный** `#0f172a` (или эквивалент через тему), без цветного «маркетингового» заголовка.
- [ ] Иконки в блоках «Возможности» и «Преимущества» — **сдержанный графит** (`slate.6`), не brand.7.
- [ ] Featured-тариф: обводка/градиент **slate**; надпись «Рекомендуем» — **teal.7**, не primary slate.
- [ ] Фон страницы — **единое поле**; нет резкой смены цвета фона между каждой секцией.
- [ ] Sticky header не ломает контраст и не перекрывает якоря при скролле.
- [ ] Сверка с [`TEMPLATE_DESIGN_UX.md`](../TEMPLATE_DESIGN_UX.md) §3–5 (композиция hero, протокол фона, кнопки).

---

## 10. Связанные документы

| Документ | Зачем |
|----------|--------|
| [`TEMPLATE_DESIGN_UX.md`](../TEMPLATE_DESIGN_UX.md) | Шаблон маркетинговой страницы (композиция, фон, типографика) |
| [`DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md`](./DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md) | Общий канон Enterprise 85+, роли цвета |
| [`docs/frontend/pages/marketing-landing.md`](../frontend/pages/marketing-landing.md) | Инженерный паспорт маршрута (требует синхронизации с текущим `MarketingLandingPage.tsx`, если устарел) |
| [`docs/design/README.md`](./README.md) | Индекс папки `docs/design/` |

---

*Паспорт отражает целевое состояние кода на дату версии в шапке; при смене палитры или секций обновляйте §4–6 и при необходимости `DESIGN_TOKENS_85_PLUS.json` / `DESIGN_CODE_MAP.md`.*
