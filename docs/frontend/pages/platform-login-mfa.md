# Platform Login Mfa

## Метаданные

- **Path:** `/platform/login/mfa` (`ROUTE_PATHS.platform.loginMfa`)
- **Зона:** platform
- **Компонент(ы) в App.tsx:** `PlatformFounderMfaPage`
- **Файл страницы:** `frontend/src/marketing/pages/PlatformFounderMfaPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/marketing/pages/PlatformFounderMfaPage.tsx`<br>`frontend/src/auth/SignInShell.tsx ← импорт из frontend/src/marketing/pages/PlatformFounderMfaPage.tsx`<br>`frontend/src/auth/panels/PlatformFounderMfaPanel.tsx ← импорт из frontend/src/marketing/pages/PlatformFounderMfaPage.tsx` |
| Строк (сумма по фрагментам) | 256 |
| Хуки (эвристика, union) | — |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Второй шаг входа основателя платформы: ввод одноразового TOTP после успешной проверки email/пароля на [`/platform/login`](./platform-login.md). Ожидается, что промежуточный **`mfa_token`** уже сохранён в session-обёртке (см. `frontend/src/auth/platformFounderMfaSession.ts`) после ответа первого шага.

## Логика и данные

- **Хуки:** `useNavigate`, `useSearchParams` — в `PlatformFounderMfaPanel`; на странице только разметка.
- **Панель:** `PlatformFounderMfaPanel` (`frontend/src/auth/panels/PlatformFounderMfaPanel.tsx`).
- **API:** `POST /v1/platform/auth/login/mfa` — тело `{ mfa_token, totp_code }`, без Bearer; при успехе `access_token` → `setFounderToken`, очистка pending MFA, редирект на `returnTo` через `safeAuthReturnTo` / `defaultReturnToForTab("founder")`.
- **Нет React Query:** одиночный `fetch` по клику «Подтвердить», локальный `busy` / `error`.

## RBAC / entitlements / edition

Публичный шаг входа; доступ к `/platform/*` после выдачи JWT основателя (**fact**). Бэкенд может требовать TOTP для внутренних маршрутов — см. настройки сервера.

## UI-скелет (as-built)

- `SignInShell` → `Stack`: заголовок «Двухфакторный вход», подзаголовок «Шаг 2 из 2», затем `PlatformFounderMfaPanel`.

## Инвентарь поверхностей UI (ось H)

`AdminDrawer` / `GlassModal` **нет**.

| Тип | Триггер | Поведение |
|-----|---------|-----------|
| Состояние «нет mfa_token» | Инициализация без токена в session | Текст + кнопка «К форме входа» → очистка pending, редирект на `/platform/login` (**fact**) |
| `TextInput` | Код TOTP | `totpCode`, `autoComplete="one-time-code"` (**fact**) |
| `Button` «Назад» | Клик | `goBackToLogin` (**fact**) |
| `Button` «Подтвердить» | Клик | `submitMfa`, `loading={busy}` (**fact**) |
| `Alert` (red) | `error !== null` | Сообщение об ошибке MFA (**fact**) |
| `Anchor` | На главную | `ROUTE_PATHS.marketing.landing` (**fact**) |

## Целевой UX (target vs as-built)

- *as-built:* явная ветка при устаревшей MFA-сессии с возвратом к логину.
- *target:* совпадает с текущим контуром; опционально — deeplink-документация для ops.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- `frontend/src/__tests__/routePaths.test.ts` — путь в `ALL_PUBLIC_APP_PATHS`.
- Отдельных тестов на панель MFA **не найдено** (**gap**).

## Gap scan (вторая редакция)

- Нет автотеста на истечение `mfa_token` и редирект.
- Поведение при прямом заходе на `/platform/login/mfa` без шага 1 задокументировано в UI, но не в e2e.
