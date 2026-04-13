# Admin Subscription

## Метаданные

- **Path:** `/admin/subscription`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminSubscriptionPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminSubscriptionPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminSubscriptionPage.tsx`<br>`frontend/src/marketing/components/PlatformPricingSection.tsx ← импорт из frontend/src/admin/pages/AdminSubscriptionPage.tsx`<br>`frontend/src/admin/components/AdminSubscriptionCapabilitiesCard.tsx ← импорт из frontend/src/admin/pages/AdminSubscriptionPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminSubscriptionPage.tsx` |
| Строк (сумма по фрагментам) | 741 |
| Хуки (эвристика, union) | `useAdminSession` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Показать включённые опции организации (`AdminSubscriptionCapabilitiesCard`) и **справочный** каталог тарифов с публичной витрины (`PlatformPricingSection` в режиме `catalog_only`: планы и опции без checkout и без создания signup intent). Текст на странице поясняет, что апгрейд существующей организации — через оператора до появления self-service.

## Логика и данные

- **Компоненты:** `AdminSubscriptionCapabilitiesCard` — `useAdminSession`, отображение `entitlement_keys` и режима `entitlement_enforced`; `PlatformPricingSection` — локальный `useState` + `useEffect`, публичные `fetch` без admin Bearer.
- **API (публичный каталог):** `GET /v1/public/platform/catalog/plans`; `GET /v1/public/platform/catalog/options` (заголовок `X-Request-Id`). В режиме `catalog_only` блоки email, Turnstile и `POST /v1/public/platform/signup/checkout` **не** показываются.

## RBAC / entitlements / edition

- Содержимое карточки возможностей зависит от сессии и организации (см. компонент).
- В `SEGMENT_ENTITLEMENT` для `subscription` ключа нет (**fact**).
- Box не блокирует сегмент.

## UI-скелет (as-built)

`ContextBar` («Подписка платформы») — вводный `Text` — `AdminSubscriptionCapabilitiesCard` — `PlatformPricingSection` с заголовком каталога по умолчанию из компонента.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` / `GlassModal` / `Modal`:** на странице нет (внутри `PlatformPricingSection` в режиме каталога — карточки и алерты ошибок загрузки).

## Целевой UX (target vs as-built)

- *target:* self-service апгрейд опций для владельца.
- *as-built:* только просмотр entitlements + публичные цены.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Каталог грузится публично; при сетевой ошибке пользователь видит сообщение внутри секции цен, не в общем `QueryErrorAlert` страницы.
