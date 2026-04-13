# Marketing Signup

## Метаданные

- **Path:** `/signup` (`ROUTE_PATHS.marketing.signup`)
- **Зона:** marketing
- **Компонент(ы) в App.tsx:** `SignupPage`
- **Файл страницы:** `frontend/src/marketing/pages/SignupPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/marketing/pages/SignupPage.tsx`<br>`frontend/src/marketing/components/PlatformPricingSection.tsx ← импорт из frontend/src/marketing/pages/SignupPage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/marketing/pages/SignupPage.tsx` |
| Строк (сумма по фрагментам) | 812 |
| Хуки (эвристика, union) | — |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Регистрация новой клиники на платформе: два обязательных согласия (ПДн и условия), затем тот же сценарий, что на `/pricing` — выбор плана, email, оплата через YooKassa и создание организации после успешной оплаты (описание в копирайте страницы).

## Логика и данные

- **Хуки (страница):** `useState` для `consentPd`, `consentTerms`; `canProceed = consentPd && consentTerms`.
- **Вложенный UI:** при `canProceed` рендерится `PlatformPricingSection` с заголовком «Выбор плана и оплата» (`frontend/src/marketing/components/PlatformPricingSection.tsx`, режим `full` по умолчанию).
- **API:** те же вызовы, что на `/pricing`: `GET /v1/public/platform/catalog/plans`, `GET /v1/public/platform/catalog/options`, `POST /v1/public/platform/signup/checkout` (см. паспорт `marketing-pricing.md`).
- **Навигация:** ссылки на [`/legal/privacy`](./marketing-legal-privacy.md) и [`/legal/terms`](./marketing-legal-terms.md) из текста чекбоксов (`target="_blank"`).

## RBAC / entitlements / edition

Публичная страница; гейтов нет (**fact**).

## UI-скелет (as-built)

- `Box` fullscreen, `Container` + `Stack`: заголовок «Регистрация клиники», пояснение.
- Блок из двух `Checkbox` (согласия с вложенными `Anchor`+`Link`).
- Условный рендер: если не оба согласия — серый `Text` с подсказкой; если оба — `PlatformPricingSection`.
- Внизу `Anchor` «← На главную».

## Инвентарь поверхностей UI (ось H)

Отдельных `Modal` / `Drawer` / `Menu` на странице **нет**.

| Тип | Триггер | Данные / поведение |
|-----|---------|-------------------|
| `Checkbox` | Согласие на ПДн | `consentPd` (**fact**) |
| `Checkbox` | Согласие с условиями | `consentTerms` (**fact**) |
| Вложенный блок тарифов | `canProceed` | См. ось H в `marketing-pricing.md` (те же `Alert`, `Card`, кнопки оплаты и т.д.) (**fact**) |

## Целевой UX (target vs as-built)

- *as-built:* гейт на согласиях перед показом оплаты; соответствует требованию self-service signup с юридическими ссылками.
- *target:* финальные юридические тексты на `/legal/*` — **gap** контента, не логики страницы.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- `frontend/src/__tests__/routePaths.test.ts` — маршрут `/signup`.
- Отдельных тестов на сценарий согласий + checkout **не найдено** (**gap**).

## Gap scan (вторая редакция)

- Нет автоматической проверки, что пользователь открыл юридические страницы (только чекбоксы).
- Дублирование описания API с `/pricing` намеренно; при изменении `PlatformPricingSection` обновлять оба паспорта.
