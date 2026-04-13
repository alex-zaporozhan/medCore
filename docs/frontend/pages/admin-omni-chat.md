# Admin Omni Chat

## Метаданные

- **Path:** `/admin/omni-chat`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminOmniChatPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminOmniChatPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminOmniChatPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminOmniChatPage.tsx`<br>`frontend/src/shared/emptyStateHint.tsx ← импорт из frontend/src/admin/pages/AdminOmniChatPage.tsx`<br>`frontend/src/hooks/useAdminOmniChat.ts ← импорт из frontend/src/admin/pages/AdminOmniChatPage.tsx`<br>… +6 файлов |
| Строк (сумма по фрагментам) | 3087 |
| Хуки (эвристика, union) | `useAdminOmniChat`, `useAdminOmniChatDetail`, `useAdminOmniChatMessages`, `useAdminOmniChatMessagesInfinite`, `useAdminOmniChatPresence`, `useAdminOmniChats`, `useAdminSession`, `useClaimAdminOmniChat`, `useCloseAdminOmniChat`, `useHideAdminOmniMessage`, `useInfiniteQuery`, `useMutation`, `useOmniChatAnalytics`, `useOmniChatClosureTags`, `useOmniChatSse`, `useOmniQuickReplies`, `usePatchOmniChat`, `useQuery`, `useQueryClient`, `useResolveAdminOmniChat`, `useSendAdminOmniMessage`, `useSendAdminOmniMessageWithFile`, `useUpdateOmniChatAiMode` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/admin/auth/session`, `/v1/admin/omni-chat-closure-tags`, `/v1/admin/omni-chats/quick-replies`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 1, Menu: 5 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Рабочее место оператора омниканальных диалогов: списки чатов (все / новые без назначения / «мои»), центральная лента сообщений с ответом, вложениями, голосовыми заметками, быстрыми ответами, цитированием, AI-режимом чата, закрытием и разрешением; правая колонка «рабочий список». Опционально модальное окно аналитики по периоду для пользователей с правом `erp.owner_reports.read`. Поддержка SSE для обновлений (токен через API).

## Логика и данные

- **Хуки (основные):** `useAdminSession`, `useQueryClient`, `useAdminOmniChats`, `useAdminOmniChatDetail`, `useAdminOmniChatMessagesInfinite`, `useSendAdminOmniMessage`, `useSendAdminOmniMessageWithFile`, `useResolveAdminOmniChat`, `useAdminOmniChatPresence`, `useUpdateOmniChatAiMode`, `useOmniQuickReplies`, `useOmniChatAnalytics`, вспомогательные `getAdminOmniAttachmentBlob` / `getAdminClinicChatAttachmentBlob` (`frontend/src/hooks/useAdminOmniChat.ts`).
- **queryKey (примеры):** `["admin-omni-chats", filters]`, `["admin-omni-chat-detail", chatId]`, `["admin-omni-chat-messages", chatId, ...]`, `["admin-omni-quick-replies"]`, `["admin-omni-chat-analytics", params]`.
- **API (типовые `/v1/...`):** `GET /v1/admin/omni-chats`; `GET /v1/admin/omni-chats/{id}`; `GET /v1/admin/omni-chats/{id}/messages`; `POST` сообщений и upload; `POST .../resolve`, `.../claim`, `.../close`, `.../presence`, `.../ai-mode`; `GET /v1/admin/omni-chats/analytics`; `GET /v1/admin/omni-chats/sse-token` и URL событий SSE; вложения — blob-эндпоинты под `/v1/admin/omni-chats/.../attachments/.../file` и legacy `/v1/admin/chat/...`; быстрые ответы и теги закрытия — см. хук.

## RBAC / entitlements / edition

- **Permissions:** переключение AI по чату — `omni.inbox.manage` (`canToggleAi`); аналитика — `erp.owner_reports.read` (`canViewAnalytics`). Флаг `isOwner` используется для части UI (например контекстных действий).
- В `SEGMENT_ENTITLEMENT` для `omni-chat` ключа нет (**fact**).
- Box не блокирует сегмент.

## UI-скелет (as-built)

`ContextBar` → в области контента **три** колонки (`Flex`): инбокс слева (**300px**), центральный диалог (**flex: 1**), правая **`OmniWorkPane`** (**320px**). Глобальный сайдбар админки — снаружи этого `Flex`. Слева: **«Входящие»**, вкладки **«Все чаты»** / **«Новые (n)»**, поиск **«Поиск по контакту»**, фильтр **«Каналы: все»**. В центре: заголовок **«Диалог»**, статус, переключатель **«ИИ»** (при праве `omni.inbox.manage`), лента сообщений, пояснение про автозакрытие при неактивности, композер (**«Написать ответ…»**, Ctrl+Enter), быстрые ответы. Правая колонка — см. ниже. Контекстное меню по сообщению — `Menu` Mantine.

### Правая панель «Мои заявки» — логика и типичное «пусто»

- **Данные:** отдельный запрос `useAdminOmniChats({ assignee: "me", page, page_size })` — только диалоги, где текущий админ указан как исполнитель.
- **Вкладки:** **«В работе»** — элементы со статусом не `CLOSED`; **«Закрытые»** — со статусом `CLOSED`.
- **Пустое состояние:** при отсутствии строк текст **«Нет чатов в работе.»** / **«Нет закрытых заявок.»** — это **нормально**, если у оператора нет назначенных на него чатов в соответствующем статусе.
- **Почему центр заполнен, а справа пусто:** центральная колонка показывает **выбранный в левом списке** чат (в т.ч. общий инбокс / чужой / неназначенный). Правая колонка **не дублирует** текущий чат — она только **«мои» по assignee**. Поэтому сценарий «открыт диалог слева, справа пусто» **соответствует коду**, а не обязательно ошибке загрузки (**fact:** путаница UX — **gap**: подсказка в UI или переименование панели).

### Evidence / QA (скриншоты)

- URL **`/admin/omni-chat`**, заголовок в духе **«Omni-чат — только работа»**, ссылка **«Аналитика»** при наличии права на отчёты.

## Инвентарь поверхностей UI (ось H)

- **`Modal` (Mantine):** «Аналитика omni-чата» — диапазон дат, карточки метрик, данные из `useOmniChatAnalytics`.
- **`Menu`:** контекст по сообщению (ответ, копирование текста).
- **`AdminDrawer` / `GlassModal`:** на корне страницы нет; детали — колонки и одна **`Modal`** для аналитики.

## Целевой UX (target vs as-built)

- *target:* единый паттерн модалок (`GlassModal`) при желании команды.
- *as-built:* большой монолитный экран, одна аналитическая `Modal`.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Файл страницы очень большой; регрессии удобнее ловить e2e или срезанными тестами хуков.
- Уточнить продуктово: какие кнопки в инбоксе считаются основными в 2026 и какие оставлены для обратной совместимости — отдельный проход по `AdminOmniChatPage.tsx` + копирайт.
- Модалка аналитики (`Modal` Mantine) и остальной экран — разные паттерны окон; см. также общий долг по унификации размеров модалок в админке (**см. `admin-schedule.md`**).
