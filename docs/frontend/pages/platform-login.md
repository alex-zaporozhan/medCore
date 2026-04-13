# Вход основателя платформы

## Метаданные

- **Path:** `/platform/login` (`ROUTE_PATHS.platform.login`)
- **Зона:** platform
- **Компонент в App.tsx:** `Route path={ROUTE_PATHS.platform.login} element={<PlatformFounderLoginPage />}`
- **Файл страницы:** `frontend/src/marketing/pages/PlatformFounderLoginPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/marketing/pages/PlatformFounderLoginPage.tsx`<br>`frontend/src/auth/SignInShell.tsx ← импорт из frontend/src/marketing/pages/PlatformFounderLoginPage.tsx`<br>`frontend/src/auth/panels/PlatformFounderSignInPanel.tsx ← импорт из frontend/src/marketing/pages/PlatformFounderLoginPage.tsx` |
| Строк (сумма по фрагментам) | 238 |
| Хуки (эвристика, union) | — |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Отдельный вход для роли основателя платформы (JWT `platform_founder`), не смешивается с `/admin/login` клиники.

## Логика и данные

- **UI:** `SignInShell` + `PlatformFounderSignInPanel` (`frontend/src/auth/panels/PlatformFounderSignInPanel.tsx`).
- **API (fact):** `fetch(`${API_BASE}/v1/platform/auth/login`, { POST, JSON email/password })` — без Bearer; разбор тела через `parseFastApiErrorBody`.
  - Ответ `mfa_required` + `mfa_token` → `setPendingPlatformFounderMfaToken`, редирект на `ROUTE_PATHS.platform.loginMfa` — см. [`platform-login-mfa.md`](./platform-login-mfa.md).
  - Иначе `access_token` → `setFounderToken` (`frontend/src/marketing/platformFounderSession.ts`), `navigate` на `returnTo` (безопасный) или dashboard.
- **Хранение токена:** платформенный JWT в хранилище сессии основателя (см. код `setFounderToken`).

## RBAC / entitlements / edition

Публичная страница входа; авторизация определяет доступ к `/platform/dashboard` и внутренним API платформы.

## UI-скелет (as-built)

- `Title` «Основатель платформы», поясняющий `Text`, форма в панели внутри `SignInShell`.

## Инвентарь поверхностей UI (as-built)

`AdminDrawer` / `GlassModal` / `Menu` **нет**.

| Элемент | Триггер | Данные / состояние |
|---------|---------|-------------------|
| `TextInput` email, `PasswordInput` | Ввод учётных данных | Локальный state (**fact**) |
| `Button` «Войти» | Клик | `submitCredentials`, `busy` loading (**fact**) |
| `Alert` (red) | `error !== null` после неуспешного login / 503 | Текст из тела ответа или дефолт (**fact**) |
| `Anchor` «На главную» | Ссылка | `ROUTE_PATHS.marketing.landing` (**fact**) |

## Целевой UX (target vs as-built)

- *target:* жёсткое визуальное и текстовое отличие от входа клиники (снижение фишинга и ошибок пользователя).
- *as-built:* явный текст «Не путайте с входом в админку клиники».

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- `frontend/src/__tests__/routePaths.test.ts` — `/platform/login` в паритете `ALL_PUBLIC_APP_PATHS`.
- Отдельных vitest на `PlatformFounderLoginPage` / панель **не найдено** (**gap**).

## Gap scan

- Токен основателя хранится через `platformFounderSession.ts` (клиентское хранилище) — риски XSS vs httpOnly см. архитектуру в [`../architecture/frontend/routing_and_shells.md`](../../architecture/frontend/routing_and_shells.md).
- Нет e2e на цепочку login → MFA → dashboard.
