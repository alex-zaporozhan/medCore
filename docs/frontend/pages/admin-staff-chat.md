# Admin Staff Chat

## Метаданные

- **Path:** `/admin/staff-chat` (+ query: `?task=…`, `?dm_peer_id=…`)
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminStaffChatPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminStaffChatPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminStaffChatPage.tsx`<br>`frontend/src/hooks/useAdminAdmins.ts ← импорт из frontend/src/admin/pages/AdminStaffChatPage.tsx`<br>`frontend/src/hooks/useStaffCollab.ts ← импорт из frontend/src/admin/pages/AdminStaffChatPage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/admin/pages/AdminStaffChatPage.tsx`<br>… +6 файлов |
| Строк (сумма по фрагментам) | 2567 |
| Хуки (эвристика, union) | `useAckStaffCalendarInvitation`, `useAckStaffFeedPost`, `useAddStaffFeedComment`, `useAdminAdmins`, `useAdminSession`, `useCreateAdminMutation`, `useCreateKnowledgeDocument`, `useCreateStaffCalendarEvent`, `useCreateStaffDmRoom`, `useCreateStaffFeedPost`, `useCreateStaffGroupRoom`, `useDeleteStaffFeedComment`, `useDeleteStaffFeedPost`, `useInviteStaffRoomMember`, `useKnowledgeDocuments`, `useMarkStaffChatRoomRead`, `useMutation`, `usePatchAdminEmploymentMutation`, `usePostStaffChatMessage`, `useQuery`, `useQueryClient`, `useStaffAnnouncementPublishPolicy`, `useStaffAnnouncementPublishPolicyAudit`, `useStaffAnnouncements`, `useStaffCalendarEventDetails`, `useStaffCalendarEvents`, `useStaffCalendarMonthGrid`, `useStaffChatMessages`, `useStaffChatRooms`, `useStaffCollab`, `useStaffFeedComments`, `useStaffFeedPostAckStatus`, `useStaffFeedPosts`, `useStaffTaskChatRoom`, `useToggleStaffFeedPostLike`, `useUpdateKnowledgeDocument`, `useUpdateStaffAnnouncementPublishPolicy`, `useUpdateStaffCalendarEvent`, `useUpdateStaffFeedComment`, `useUpdateStaffFeedPost`, `useUploadStaffChatAttachment`, `useUploadStaffFeedCommentAttachment`, `useUploadStaffFeedPostAttachment` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/admins`, `/v1/admin/auth/login`, `/v1/admin/auth/session`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 4, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Внутренний чат персонала клиники: список комнат (DM, группа, привязка к задаче), переписка с текстом, вложениями и голосовыми, создание DM/группы, приглашение в GROUP/TASK-комнату. Deep-link по `task` открывает/подтягивает task-room; `dm_peer_id` инициирует создание DM с коллегой.

## Логика и данные

- **Хуки:** `useAdminSession`, `useAdminAdmins`, `useStaffChatRooms`, `useStaffTaskChatRoom`, `useStaffChatMessages`, `usePostStaffChatMessage`, `useUploadStaffChatAttachment`, `useMarkStaffChatRoomRead`, `useCreateStaffDmRoom`, `useCreateStaffGroupRoom`, `useInviteStaffRoomMember`, плюс прямой `api.getBlob` для скачивания файла вложения.
- **queryKey:** см. `useStaffCollab` (rooms, messages по `roomId`, task-room по `taskId`).
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/staff/chat/rooms`
  - `GET /v1/admin/staff/chat/task-rooms/{taskId}`
  - `POST /v1/admin/staff/chat/rooms/dm` · `POST .../rooms/group`
  - `POST /v1/admin/staff/chat/rooms/{roomId}/read`
  - `GET /v1/admin/staff/chat/rooms/{roomId}/messages?limit=100`
  - `POST /v1/admin/staff/chat/rooms/{roomId}/messages` (body)
  - `POST /v1/admin/staff/chat/messages/{messageId}/attachments`
  - `POST /v1/admin/staff/chat/rooms/{roomId}/members` (invite)
  - `GET /v1/admin/staff/attachments/{attachmentId}/file` (blob)
  - `GET /v1/admin/admins`

## RBAC / entitlements / edition

- **fact:** Сегмент `staff-chat` **не** входит в `SEGMENT_ENTITLEMENT` / `adminShellSegmentEntitlementKey` (`adminEntitlementNav.ts`) — SaaS-gate по entitlement-ключу для этого пункта не применяется из этой карты (остаётся сессия админа и бэкенд).
- **fact:** `allowAudioAttachmentDownload` — только роль `owner` в `adminSession.roles` влияет на возможность скачивания аудио-вложений (as-built в этом файле).

## UI-скелет (as-built)

- `ContextBar` «Чат команды» + поясняющий подзаголовок (текст/голос, без видео-кружков).
- Двухколоночный layout: слева список комнат с поиском и кнопками действий; справа тред сообщений, поле ввода (`AppleEmojiOverlayTextarea`), вложения, голос.
- `ClinicChatAttachments`, `VoiceNoteRecorderButton`, стили пузырей из `adminChatChrome`.

### Evidence / QA (скриншоты)

- URL **`/admin/staff-chat`**. Слева: **«Поиск чатов…»**, **«Новая группа»**, список комнат (DM, очередь, общий чат и т.д.), снизу **«Персонал клиники»**.
- Справа: заголовок собеседника/комнаты, история с изображениями и аудио-плеером, поле **«Сообщение…»**, **«Отправить»**, подсказка про **Ctrl+Enter**, голос и вложение к последнему сообщению.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer / GlassModal:** нет.
- **Mantine `Modal` (centered):** «Личный чат» (DM), «Персонал клиники» (finder), «Пригласить в комнату», «Новая группа» — открытие по кнопкам; закрытие сбрасывает локальный стейт (**fact:** мутации `dmMut`, `groupMut`, `inviteMut` с `isPending`/ошибками на уровне страницы).
- **`QueryErrorAlert`:** ошибки загрузки комнат/сообщений.
- **Скрытый `<input type="file">`:** выбор файла для вложения.

## Целевой UX (target vs as-built)

- *target:* быстрый обмен внутри клиники без внешних мессенджеров, предсказуемые deep-link’и.
- *as-built:* полный набор сценариев + модалки для создания/приглашения; скачивание аудио ограничено ролью owner.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** отдельных тестов страницы не найдено.

## Gap scan (вторая редакция)

- Много критичной логики в одном файле (~700+ строк) — при изменениях выше риск регрессий без e2e/контрактных тестов.
- Entitlement-карта не покрывает staff-chat — если продукт требует гейта по тарифу, нужно согласовать с бэкендом и `ADMIN_NAV_PATH_ENTITLEMENT_KEY`.
