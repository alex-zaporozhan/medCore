# Admin Settings

## Метаданные

- **Path:** `/admin/settings`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminSettingsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminSettingsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminSettingsPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminSettingsPage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/admin/pages/AdminSettingsPage.tsx`<br>`frontend/src/admin/components/AdminSubscriptionCapabilitiesCard.tsx ← импорт из frontend/src/admin/pages/AdminSettingsPage.tsx` |
| Строк (сумма по фрагментам) | 424 |
| Хуки (эвристика, union) | `useAdminSession` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Единая точка входа в разделы конфигурации: карточка «подписка и возможности» (`AdminSubscriptionCapabilitiesCard`) и список ссылок (`Anchor` + `Link`) на существующие маршруты админки (подписка, касса, соглашения, каналы, омни, интеграции, оформление, RBAC и т.д.). Дубли в боковом меню убраны сознательно (комментарий в коде).

## Логика и данные

- **Хуки / данные:** `AdminSubscriptionCapabilitiesCard` использует `useAdminSession` и поля `organization_id`, `entitlement_enforced`, `entitlement_keys`, `roles` для отображения опций тарифа.
- **API:** неявно через загрузку админ-сессии (как на остальных экранах после логина); отдельных запросов на странице нет.
- **Маршруты ссылок:** задаются массивом `links` с `ROUTE_PATHS.admin.*`.

## RBAC / entitlements / edition

- Карточка подписки учитывает режим enforcement и роль `owner` для ссылки на страницу подписки.
- В `SEGMENT_ENTITLEMENT` для сегмента `settings` ключа нет (**fact**).
- Box не блокирует сегмент.

## UI-скелет (as-built)

`ContextBar` («Настройки») — `AdminSubscriptionCapabilitiesCard` — поясняющий `Text` — вертикальный список ссылок.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` / `GlassModal` / `Modal`:** нет.

## Целевой UX (target vs as-built)

- *target:* группировка ссылок по группам (коммуникации, биллинг, бренд).
- *as-built:* плоский список якорей.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Список ссылок дублирует знание о доступных сегментах; при добавлении нового раздела нужно не забыть обновить `links`.
