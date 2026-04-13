# Admin Channels

## Метаданные

- **Path:** `/admin/channels`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminChannelsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminChannelsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminChannelsPage.tsx`<br>`frontend/src/hooks/useChannelConfigs.ts ← импорт из frontend/src/admin/pages/AdminChannelsPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminChannelsPage.tsx`<br>`frontend/src/shared/emptyStateHint.tsx ← импорт из frontend/src/admin/pages/AdminChannelsPage.tsx`<br>… +2 файлов |
| Строк (сумма по фрагментам) | 570 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminSession`, `useBusinessLexicon`, `useChannelConfigs`, `useClinics`, `useMutation`, `useQuery`, `useQueryClient`, `useUpsertChannelConfig` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Настройка каналов уведомлений клиники: Telegram (бот и chat id), SMS через SMSC.ru (логин, пароль, отправитель), Email SMTP. Каждый канал — отдельная карточка с переключателем «Включено» и сохранением в API.

## Логика и данные

- **Хуки:** `useAdminClinic`, `useChannelConfigs`, `useUpsertChannelConfig` (`frontend/src/hooks/useChannelConfigs.ts`).
- **queryKey:** `["channel-configs", clinicId]`.
- **API:** `GET /v1/admin/clinics/{clinic_id}/channel-configs`; `PUT /v1/admin/clinics/{clinic_id}/channel-configs/{channel}` для `telegram`, `sms` или `email`.

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для сегмента `channels` ключа нет (**fact**).
- Без выбранной клиники — `EmptyStateHint`; Box не блокирует сегмент.

## UI-скелет (as-built)

`ContextBar` («Каналы уведомлений») — поясняющий текст — колонка карточек (`ChannelCard` / `Card`) с полями под тип канала и кнопкой «Сохранить». Загрузка — `PageSkeleton`; ошибка — `Alert` с `error.message`.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` / `GlassModal` / `Modal`:** на странице нет.
- **Состояние сохранения:** общий `upsertMut.isPending` на все три карточки (при сохранении одной кнопка «Сохранить» на остальных тоже в состоянии loading).

## Целевой UX (target vs as-built)

- *target:* отдельный `isPending` по каналу или оптимистичные обновления.
- *as-built:* простая форма на `Card` без overlay.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Общий флаг сохранения для трёх карточек может путать при параллельных правках.
