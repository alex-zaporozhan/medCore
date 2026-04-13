# Marketing Legal Terms

## Метаданные

- **Path:** `/legal/terms` (`ROUTE_PATHS.marketing.legalTerms`)
- **Зона:** marketing
- **Компонент(ы) в App.tsx:** `LegalTermsPage`
- **Файл страницы:** `frontend/src/marketing/pages/LegalTermsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/marketing/pages/LegalTermsPage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/marketing/pages/LegalTermsPage.tsx` |
| Строк (сумма по фрагментам) | 222 |
| Хуки (эвристика, union) | — |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Публичная страница-заглушка пользовательского соглашения / оферты: маршрут для витрины и signup; финальный текст согласуется с юридической службой вне кода (комментарий в исходнике: Phase 1b / МП §5).

## Логика и данные

- **Хуки:** нет.
- **API / React Query:** нет.
- **Навигация:** `Anchor` «На главную» → `ROUTE_PATHS.marketing.landing`.

## RBAC / entitlements / edition

Публичная страница; ограничений нет (**fact**).

## UI-скелет (as-built)

- `Container size="sm" py="xl"` → `Paper` → `Stack`: заголовок «Пользовательское соглашение», поясняющий `Text`, ссылка на главную (аналогично `LegalPrivacyPage`).

## Инвентарь поверхностей UI (ось H)

Модалок, `Drawer`, `Menu`, `Alert` **нет**; только ссылка на главную.

## Целевой UX (target vs as-built)

- *as-built:* честный плейсхолдер до продакшена self-service signup.
- *target:* публичная оферта и согласованность с `/signup` и оплатой (**gap** контента).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- `frontend/src/__tests__/routePaths.test.ts` — `ROUTE_PATHS.marketing.legalTerms` в паритете `ALL_PUBLIC_APP_PATHS`.
- Отдельных vitest на разметку страницы **не найдено** (**gap**).

## Gap scan (вторая редакция)

- Синхронизация с реальной офертой и ссылками из `SignupPage` после публикации текста.
- Возможен общий layout для пары legal-страниц (сейчас дублирование разметки с privacy — не дефект продукта, **gap** рефакторинга).
