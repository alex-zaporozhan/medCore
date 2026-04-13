# Admin Omni AI Settings

## Метаданные

- **Path:** `/admin/omni-ai-settings`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminOmniAiSettingsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminOmniAiSettingsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminOmniAiSettingsPage.tsx`<br>`frontend/src/hooks/useOwnerOmniAiSettings.ts ← импорт из frontend/src/admin/pages/AdminOmniAiSettingsPage.tsx`<br>`frontend/src/shared/ui/DataSkeleton.tsx ← импорт из frontend/src/admin/pages/AdminOmniAiSettingsPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminOmniAiSettingsPage.tsx` |
| Строк (сумма по фрагментам) | 312 |
| Хуки (эвристика, union) | `useMutation`, `useOwnerOmniAiSettings`, `useQuery`, `useQueryClient`, `useUpdateOwnerOmniAiSettings` |
| Пути в строках `/v1/...` | `/v1/owner/omni-ai-settings` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Настройка режима AI для омниканального ассистента: глобальный режим для «бизнеса» и переопределения по каждому подключённому каналу (`DISABLED`, `AUTO_REPLY`, `SUGGEST_ONLY`). Две независимые кнопки сохранения — для бизнес-режима и для таблицы каналов (вторая появляется только при изменениях в строках).

## Логика и данные

- **Хуки:** `useOwnerOmniAiSettings`, `useUpdateOwnerOmniAiSettings`, константа `OMNI_AI_MODES` (`frontend/src/hooks/useOwnerOmniAiSettings.ts`).
- **queryKey:** `["owner-omni-ai-settings"]`.
- **API:** `GET /v1/owner/omni-ai-settings`; `PUT /v1/owner/omni-ai-settings` с телом `{ business?: { ai_mode }, channels?: [{ channel_id, ai_mode }] }`.

## RBAC / entitlements / edition

- Данные с **`/v1/owner/...`** при монтировании в `/admin/omni-ai-settings` — ожидается owner-доступ на API (**fact**).
- В `SEGMENT_ENTITLEMENT` для `omni-ai-settings` ключа нет (**fact**).
- Box не блокирует сегмент.

## UI-скелет (as-built)

Загрузка — `ContextBar` + `DataSkeleton`; ошибка — `QueryErrorAlert`. Успех: `ContextBar`, текст, два `AdminSettingsSectionCard` — «Режим по умолчанию» с `Select` и кнопкой «Сохранить»; «По каналам» с `Table` и построчным `Select`, кнопка «Сохранить изменения по каналам» при `hasChannelChanges`.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` / `GlassModal` / `Modal`:** нет.

## Целевой UX (target vs as-built)

- *target:* одна кнопка «Сохранить всё» или автосейв с дебаунсом.
- *as-built:* раздельные мутации на бизнес и список каналов через один `updateMutation`.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Поля `working_hours_policy`, `confidence_thresholds`, `prompt_profile_id`, `kb_profile_id` есть в типах ответа API, в UI страницы не выведены (**gap** для полного управления профилем AI).
