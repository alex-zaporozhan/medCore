# Admin Omni Channels

## Метаданные

- **Path:** `/admin/omni-channels`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminOmniChannelsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminOmniChannelsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminOmniChannelsPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminOmniChannelsPage.tsx`<br>`frontend/src/hooks/useOwnerOmniChannels.ts ← импорт из frontend/src/admin/pages/AdminOmniChannelsPage.tsx`<br>`frontend/src/shared/ui/DataSkeleton.tsx ← импорт из frontend/src/admin/pages/AdminOmniChannelsPage.tsx`<br>… +2 файлов |
| Строк (сумма по фрагментам) | 1017 |
| Хуки (эвристика, union) | `useCreateOwnerOmniChannel`, `useMutation`, `useOwnerOmniChannels`, `useQuery`, `useQueryClient`, `useSetOwnerOmniChannelCredentials`, `useUpdateOwnerOmniChannel` |
| Пути в строках `/v1/...` | `/v1/owner/channels` |
| Вхождения UI | AdminDrawer: 1, GlassModal: 9, Modal: 1, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Управление омниканальными каналами организации (тип мессенджера или шлюза, отображаемое имя, статус, признак настроенных credentials): создание канала, правка метаданных, большая форма ввода секретов по типу канала (Telegram, WhatsApp, VK, email IMAP и т.д.) с отправкой на бэкенд как JSON payload.

## Логика и данные

- **Хуки:** `useOwnerOmniChannels`, `useCreateOwnerOmniChannel`, `useUpdateOwnerOmniChannel`, `useSetOwnerOmniChannelCredentials` (`frontend/src/hooks/useOwnerOmniChannels.ts`).
- **queryKey:** `["owner-omni-channels"]`.
- **API (контур owner, не clinic-scoped в path):** `GET /v1/owner/channels`; `POST /v1/owner/channels`; `PUT /v1/owner/channels/{id}`; `POST /v1/owner/channels/{id}/credentials` с телом `provider_type`, `scopes`, строковый `payload` (JSON).

## RBAC / entitlements / edition

- Страница в админской оболочке, но данные идут с эндпоинтов **`/v1/owner/...`** — фактически ожидается учётка с правами владельца/owner API (**fact** для согласования с бэкендом).
- В `SEGMENT_ENTITLEMENT` для `omni-channels` ключа нет (**fact**).
- Box не блокирует сегмент.

## UI-скелет (as-built)

`ContextBar` с кнопкой «Добавить канал», поясняющий текст, счётчик, `EmptyState` или `Table` в `Paper`. Три **`GlassModal`:** создание, редактирование, настройка ключей (крупная форма по `credentialsChannel.type`, для прочих типов — JSON textarea).

## Инвентарь поверхностей UI (ось H)

- **`GlassModal` (3):** создать канал (тип, имя); редактировать (имя, статус); credentials (динамические поля по типу, сохранение через `setCredentials.mutate`, отображение `credentialsError`).
- **`AdminDrawer` / Mantine `Modal`:** нет.

## Целевой UX (target vs as-built)

- *target:* валидация полей до отправки, маскирование секретов после сохранения.
- *as-built:* описания полей в UI, ошибки из мутации в состоянии строки.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Очень длинный модальный сценарий credentials — риск перегрузки на мобильных ширинах.
