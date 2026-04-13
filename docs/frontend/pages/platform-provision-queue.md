# Platform Provision Queue

## Метаданные

- **Path:** `/platform/provision-queue` (`ROUTE_PATHS.platform.provisionQueue`)
- **Зона:** platform
- **Компонент(ы) в App.tsx:** `PlatformFounderProvisionQueuePage` (под `PlatformFounderLayout`)
- **Файл страницы:** `frontend/src/marketing/pages/PlatformFounderProvisionQueuePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/marketing/pages/PlatformFounderProvisionQueuePage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/marketing/pages/PlatformFounderProvisionQueuePage.tsx`<br>`frontend/src/marketing/contexts/PlatformFounderSessionContext.tsx ← импорт из frontend/src/marketing/pages/PlatformFounderProvisionQueuePage.tsx` |
| Строк (сумма по фрагментам) | 953 |
| Хуки (эвристика, union) | `useMutation`, `usePlatformFounderSession`, `useQuery`, `useQueryClient` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 1, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Операционный экран основателя: таблица signup-intent / провижининга после оплаты, ручной retry провижининга, ручное закрытие intent (reconcile), опциональная подмена JWT для dev/ops.

## Логика и данные

- **Контекст:** `usePlatformFounderSession` — `token`, `setToken`; запросы с `Authorization: Bearer ${token.trim()}`.
- **React Query — список:**  
  `queryKey: ["platform-founder", "provision-queue", token]`  
  `GET /v1/platform/internal/provision-queue`  
  `enabled: !!token.trim()`; ошибки 401/403/503 с человекочитаемыми сообщениями.
- **Мутации (TanStack Query):**
  - **Retry:** `POST /v1/platform/internal/signup-intents/{intent_id}/retry-provision` — по кнопке в строке; `onSuccess` → `invalidateQueries` для `provision-queue` и `health` с тем же `token`.
  - **Manual close:** `POST /v1/platform/internal/signup-intents/{intent_id}/manual-close` — JSON `{ note }`; успех закрывает модалку и инвалидирует очередь.

## RBAC / entitlements / edition

Только при наличии JWT основателя и успешном прохождении layout-guard (**fact**). Права на бэкенде — контур `platform/internal/*`.

## UI-скелет (as-built)

- `Container` + `Stack`: заголовок, пояснение про Bearer.
- `Paper`: кнопка «Обновить очередь», вывод общей ошибки (`queueQ` / мутации), `Accordion` «Расширенно: заменить Bearer-токен вручную» (`PasswordInput` + «Применить»).
- Mantine `Modal` — форма ручного закрытия intent (`Textarea` заметки, Отмена / «Закрыть intent»).
- `Table` с колонками intent, статус, email, org, ошибка, оплата, revoke, попытки, DLQ, действия.

## Инвентарь поверхностей UI (ось H)

| Тип | Триггер | Поведение |
|-----|---------|-----------|
| `Accordion` | Раскрыть «заменить токен» | Ручной `setToken` для отладки (**fact**) |
| `Modal` | Кнопка «Закрыть» в строке (статусы `provision_failed`, `dead_letter`) | `manualCloseMut`, блокировка закрытия при `isPending` (**fact**) |
| `Button` «Обновить очередь» | Клик | `queueQ.refetch()`, `loading={isFetching}` (**fact**) |
| `Button` «Retry» | Строка таблицы | `retryMut.mutate(intent_id)` (**fact**) |
| `Tooltip` / `CopyButton` / `ActionIcon` | Ячейки UUID | Копирование intent/org id (**fact**) |
| Текст ошибки | Красный под блоком управления | Агрегат `queueQ` / `retryMut` / `manualCloseMut` (**fact**) |

`AdminDrawer` / `GlassModal` (кроме стандартного Mantine `Modal`) **нет**.

## Целевой UX (target vs as-built)

- *as-built:* полный ops-набор для расследования зависших intent.
- *target:* аудит: подтвердить, что ручное закрытие согласовано с финансовым runbook (**gap** процесса, не кода).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Маршрут в `ALL_PUBLIC_APP_PATHS`.
- Отдельных vitest на страницу **не найдено** (**gap**).

## Gap scan (вторая редакция)

- Кнопка «Закрыть» активна только для части статусов — при смене enum на бэкенде сверять с `includes(row.status)`.
- Подмена токена в Accordion — только для доверенных сред; в проде ограничить политикой (**gap** ops).
