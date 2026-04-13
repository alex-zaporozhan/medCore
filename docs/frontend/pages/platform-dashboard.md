# Platform Dashboard

## Метаданные

- **Path:** `/platform/dashboard` (`ROUTE_PATHS.platform.dashboard`)
- **Зона:** platform
- **Компонент(ы) в App.tsx:** `PlatformFounderDashboardPage` (дочерний route под `PlatformFounderLayout`, маршрут `/platform`)
- **Файл страницы:** `frontend/src/marketing/pages/PlatformFounderDashboardPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/marketing/pages/PlatformFounderDashboardPage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/marketing/pages/PlatformFounderDashboardPage.tsx`<br>`frontend/src/marketing/components/PlatformFounderTotpSetupModal.tsx ← импорт из frontend/src/marketing/pages/PlatformFounderDashboardPage.tsx`<br>`frontend/src/marketing/contexts/PlatformFounderSessionContext.tsx ← импорт из frontend/src/marketing/pages/PlatformFounderDashboardPage.tsx`<br>… +1 файлов |
| Строк (сумма по фрагментам) | 1069 |
| Хуки (эвристика, union) | `usePlatformFounderSession`, `useQuery` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 1, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Краткий обзор для основателя после входа: проверка JWT через внутренний health-эндпоинт и сводка по очереди signup/провижининга (те же данные, что полная таблица на [`platform-provision-queue`](./platform-provision-queue.md)), плюс вход в мастер привязки TOTP.

## Логика и данные

- **Контекст:** `usePlatformFounderSession` — Bearer для запросов (`token` из `PlatformFounderLayout` / `platformFounderSession.ts`).
- **React Query:**
  - `queryKey: ["platform-founder", "health", token]` → `GET /v1/platform/internal/health` с `Authorization: Bearer`.
  - `queryKey: ["platform-founder", "provision-queue", token]` → `GET /v1/platform/internal/provision-queue` — массив строк очереди; на странице считаются агрегаты по `status` и число записей с `organization_id`.
- **Мутации на странице:** нет; обновление списка — при рефетче (pull при переходе) и после действий на странице очереди (инвалидация соседними экранами — **gap** если пользователь ожидает live sync без навигации).

## RBAC / entitlements / edition

- **Layout:** `PlatformFounderLayout` редиректит на `/platform/login?returnTo=…`, если нет токена в клиентском хранилище (**fact**).
- **API:** ответы 401/403/503 обрабатываются как ошибки query (текст в UI).

## UI-скелет (as-built)

- `Container` + `Stack`: заголовок «Обзор», пояснение с упоминанием health API.
- Два `Paper`: «Состояние сессии» (результат health, кнопка TOTP) и «Очередь signup / провижининг» (сводка + ссылка на полную таблицу).
- `PlatformFounderTotpSetupModal` — управляется `useDisclosure`.

## Инвентарь поверхностей UI (ось H)

| Тип | Триггер | Данные / поведение |
|-----|---------|-------------------|
| `Button` «Привязать TOTP…» | Клик | `useDisclosure.open` → модалка (**fact**) |
| `Modal` (`PlatformFounderTotpSetupModal`) | `opened={totpModalOpen}` | `POST /v1/platform/auth/totp/enroll`, `POST /v1/platform/auth/totp/confirm`; при успехе опционально новый `access_token` через `setToken`; внутри `Alert` при ошибке (**fact**) |
| Текст загрузки / ошибки | `healthQ` / `queueQ` | `isLoading`, `error.message` красным `Text` (**fact**) |
| `Anchor` | «Открыть таблицу» | `Link` на `ROUTE_PATHS.platform.provisionQueue` (**fact**) |

`AdminDrawer` **нет**.

## Целевой UX (target vs as-built)

- *as-built:* минимальный операционный дашборд §7.1 (комментарий в коде).
- *target:* при росте нагрузки — автообновление очереди или явная кнопка «Обновить» на этом экране (**gap** продуктовый).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Маршрут в `routePaths` / `ALL_PUBLIC_APP_PATHS`.
- Отдельных vitest на дашборд **не найдено** (**gap**).

## Gap scan (вторая редакция)

- Ошибки health/queue — сырой текст ответа; нет разбора кодов для UX.
- Дублирование запроса очереди с страницей provision-queue (намеренно для сводки).
