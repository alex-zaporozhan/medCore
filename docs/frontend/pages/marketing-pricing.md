# Marketing Pricing

## Метаданные

- **Path:** `/pricing` (`ROUTE_PATHS.marketing.pricing`)
- **Зона:** marketing
- **Компонент(ы) в App.tsx:** `PricingPage`
- **Файл страницы:** `frontend/src/marketing/pages/PricingPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/marketing/pages/PricingPage.tsx`<br>`frontend/src/marketing/components/PlatformPricingSection.tsx ← импорт из frontend/src/marketing/pages/PricingPage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/marketing/pages/PricingPage.tsx` |
| Строк (сумма по фрагментам) | 773 |
| Хуки (эвристика, union) | — |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Публичная витрина тарифов платформы для клиник: заголовок, краткое пояснение (каталог планов, оплата через YooKassa), встроенный блок выбора плана и оплаты, ссылка на лендинг.

## Логика и данные

- **Хуки (страница):** только композиция; состояние и сеть — в дочернем компоненте.
- **Вложенный UI:** `PlatformPricingSection` из `frontend/src/marketing/components/PlatformPricingSection.tsx` (режим по умолчанию `mode="full"` — полный checkout).
- **API (fetch из компонента, не React Query):**
  - `GET /v1/public/platform/catalog/plans` — список планов (`API_BASE` из `frontend/src/api/client.ts`, заголовок `X-Request-Id`).
  - `GET /v1/public/platform/catalog/options` — справочник опций для подписей модулей.
  - `POST /v1/public/platform/signup/checkout` — создание intent и редирект на `payment_url` (YooKassa).
- **Мутации / кэш:** нет React Query; локальный `useState` + `useEffect` для загрузки каталога; при ошибке каталога — `Alert`, при успехе checkout — `window.location.href`.
- **Captcha:** при ответе `captcha_required` показывается `TurnstileWidget` (`frontend/src/marketing/components/TurnstileWidget.tsx`), повторное нажатие «Оплатить» с токеном.

## RBAC / entitlements / edition

Публичная страница; гейтов админки и JWT нет (**fact**).

## UI-скелет (as-built)

- `Box` на всю высоту viewport, фон `var(--bg-main)`, отступы.
- `Container size="lg"` → `Stack`: заголовок `Title` + пояснение `Text`, затем `PlatformPricingSection` с заголовком секции «Планы», внизу `Anchor` «← На главную».

## Инвентарь поверхностей UI (ось H)

`Drawer` / `GlassModal` / `Menu` / `Modal` на странице **нет**. Поверхности задаются внутри `PlatformPricingSection`:

| Тип | Триггер / условие | Данные / поведение |
|-----|-------------------|-------------------|
| `Alert` | Ошибка загрузки каталога (`catalogState === "error"`) | Текст `catalogErr` (**fact**) |
| `Alert` | Каталог пуст при `ready` | «Нет планов» (**fact**) |
| `Alert` | Только при `mode="catalog_only"` (на `/pricing` не используется) | На этой странице **нет** |
| `Card` (сетка) | Клик / Enter / Space по карточке плана | Выбор `selectedSlug` (**fact**) |
| `Checkbox` | Доп. модули (addon) | Массив `extraSelectedKeys` в теле checkout (**fact**) |
| `TextInput` | Email владельца | Обязателен перед оплатой; валидация через сообщение `checkoutErr` (**fact**) |
| `TurnstileWidget` | После ответа API `captcha_required` | Токен в повторный `POST` checkout (**fact**) |
| `Button` «Оплатить» | Месяц / год | `loading={checkoutBusy}`, disabled если нет цены периода (**fact**) |
| Текст ошибки | `checkoutErr` | Красный `Text`, не `Alert` (**fact**) |

## Целевой UX (target vs as-built)

- *as-built:* загрузка каталога, выбор плана, опциональные модули, email, оплата с редиректом на YooKassa; антиспам по требованию бэкенда.
- *target:* совпадает с текущим контуром self-service signup; уточнение юридических текстов — вне кода страницы.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Покрытие маршрута: `frontend/src/__tests__/routePaths.test.ts` (путь `/pricing` в производном списке).
- Отдельных vitest на `PricingPage` / `PlatformPricingSection` **не найдено** (**gap**).

## Gap scan (вторая редакция)

- Нет e2e на успешный checkout и редирект (внешний YooKassa).
- Ошибки checkout выводятся текстом; при желании унифицировать с `Alert` (косметика, не зафиксировано в коде).
