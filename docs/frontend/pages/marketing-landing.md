# Лендинг (маркетинг)

## Метаданные

- **Path:** `/` (`ROUTE_PATHS.marketing.landing`)
- **Зона:** marketing
- **Компонент в App.tsx:** `LandingPage` (локальная функция в том же файле)
- **Файл страницы:** логика в `frontend/src/App.tsx` (не выделена в `marketing/pages/`)

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/App.tsx (стр. 212–437, фрагмент `marketing-landing`)` |
| Строк (сумма по фрагментам) | 226 |
| Хуки (эвристика, union) | — |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Публичная точка входа: объяснение продукта, вход клиники в админку, маршрутизация пациента по slug клиники, ссылки на тарифы и регистрацию клиники.

## Логика и данные

- **Хуки:** `useNavigate`, `useSearchParams`, `useMemo`, локальный `useState` для поля slug.
- **API:** на самом лендинге запросов к API нет (навигация и ссылки).
- **Query-параметры:** ключ **`patientEntry`**; значения, задающие текст `Alert` «Вход для пациентов»: `need-clinic`, `patient-url-needs-clinic-slug`, `session-expired`, `oauth-cancelled`, `oauth-error` (все сравниваются с `searchParams.get("patientEntry")` в `App.tsx`).

## RBAC / entitlements / edition

Публичная страница; ограничений нет.

## UI-скелет (as-built)

- Полноэкранный `Box` с `minHeight: 100vh`, фон `var(--bg-main)`.
- Опциональный `Alert` (teal), два крупных `Paper` (hero и блок «Модули»), нижние `Anchor` на тарифы и юридические страницы, ссылка на `provision-queue` в футере группы.

## Инвентарь поверхностей UI (as-built)

Модалок, `Drawer` и `Menu` на странице **нет**.

| Элемент | Триггер | Данные / состояние |
|---------|---------|-------------------|
| `Alert` «Вход для пациентов» | Query `patientEntry=<значение из списка выше>` | Только копирайт, без API (**fact**) |
| `TextInput` «Адрес клиники» + `Button` «Войти» | Ввод slug, Enter или клик | `navigate` на `/c/{slug}/sign-in` (**fact**) |
| `Button` / `Link` | CTA админки, тарифы, signup, юридические ссылки | Навигация по `ROUTE_PATHS` (**fact**) |

## Целевой UX (target vs as-built)

- *target:* однозначное разделение «клиника» vs «пациент», без путаницы URL.
- *as-built:* подсказки по query закрывают типичные ошибки slug; поле «Адрес клиники» и переход на `/c/{slug}/sign-in`.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md). Тексты на экране — продуктовый RU.

## Тесты

- Структурные: `frontend/src/__tests__/routePaths.test.ts` (путь `/` в производном списке).

## Gap scan

- Нет отдельного файла страницы — при росте лендинга вынести из `App.tsx` в `marketing/pages/` для снижения связности.
- Нет vitest/e2e на сценарии `patientEntry` и переход `/c/{slug}/sign-in` (**gap**).
- Ссылка «Очередь провижининга» в футере ведёт на платформенный маршрут — см. паспорт `platform-provision-queue` при аудите смежности маркетинга и platform.
