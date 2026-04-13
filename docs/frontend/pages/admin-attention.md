# Admin Attention

## Метаданные

- **Path:** `/admin/attention`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminEmergencyNotificationsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminEmergencyNotificationsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminEmergencyNotificationsPage.tsx`<br>`frontend/src/hooks/useAdminSession.ts ← импорт из frontend/src/admin/pages/AdminEmergencyNotificationsPage.tsx`<br>`frontend/src/hooks/useAdminAdmins.ts ← импорт из frontend/src/admin/pages/AdminEmergencyNotificationsPage.tsx`<br>`frontend/src/hooks/useStaffCollab.ts ← импорт из frontend/src/admin/pages/AdminEmergencyNotificationsPage.tsx`<br>… +2 файлов |
| Строк (сумма по фрагментам) | 1788 |
| Хуки (эвристика, union) | `useAckStaffCalendarInvitation`, `useAckStaffFeedPost`, `useAddStaffFeedComment`, `useAdminAdmins`, `useAdminSession`, `useCreateAdminMutation`, `useCreateKnowledgeDocument`, `useCreateStaffCalendarEvent`, `useCreateStaffDmRoom`, `useCreateStaffFeedPost`, `useCreateStaffGroupRoom`, `useDeleteStaffFeedComment`, `useDeleteStaffFeedPost`, `useInviteStaffRoomMember`, `useKnowledgeDocuments`, `useMarkStaffChatRoomRead`, `useMutation`, `usePatchAdminEmploymentMutation`, `usePostStaffChatMessage`, `useQuery`, `useQueryClient`, `useStaffAnnouncementPublishPolicy`, `useStaffAnnouncementPublishPolicyAudit`, `useStaffAnnouncements`, `useStaffCalendarEventDetails`, `useStaffCalendarEvents`, `useStaffCalendarMonthGrid`, `useStaffChatMessages`, `useStaffChatRooms`, `useStaffCollab`, `useStaffFeedComments`, `useStaffFeedPostAckStatus`, `useStaffFeedPosts`, `useStaffTaskChatRoom`, `useToggleStaffFeedPostLike`, `useUpdateKnowledgeDocument`, `useUpdateStaffAnnouncementPublishPolicy`, `useUpdateStaffCalendarEvent`, `useUpdateStaffFeedComment`, `useUpdateStaffFeedPost`, `useUploadStaffChatAttachment`, `useUploadStaffFeedCommentAttachment`, `useUploadStaffFeedPostAttachment` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/admins`, `/v1/admin/auth/login`, `/v1/admin/auth/session`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 1, Menu: 5 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

«Стена объявлений» для персонала: лента объявлений с приоритетом, ознакомлением (`ack`), просмотром кто ознакомился / кто нет, комментарии к постам с модерацией для owner / `staff.feed.comments.moderate`. Публикация объявления с аудиторией по ролям и/или конкретным админам (двухшаговый UI через `Collapse`).

## Логика и данные

- **Хуки:** `useStaffAnnouncements`, `useCreateStaffFeedPost`, `useAckStaffFeedPost`, `useStaffFeedPostAckStatus`, `useStaffFeedComments`, `useAddStaffFeedComment`, `useUpdateStaffFeedComment`, `useDeleteStaffFeedComment`, `useAdminSession`, `useAdminAdmins`.
- **Типовые API (`/v1/...`):** семейство `/v1/admin/staff/feed/` — `announcements`, `posts` (GET list, POST create), `posts/{id}/ack`, `posts/{id}/ack-status`, `posts/{postId}/comments` и мутации комментариев (см. `useStaffCollab.ts`).

## RBAC / entitlements / edition

- **fact:** Сегмент `attention` **не** задан в `SEGMENT_ENTITLEMENT` — отдельного SaaS-ключа в карте навигации нет.
- **fact:** `canPublish` в коде возвращает `Boolean(session)` — форма публикации доступна любому с валидной админ-сессией (ограничения на бэкенде могут быть строже).
- **fact:** Модерация комментариев: роль `owner` или permission `staff.feed.comments.moderate`.

## UI-скелет (as-built)

- `ContextBar` **«Стена объявлений»**, карточка публикации, список постов с бейджами приоритета и прогресса ack, вложенный `CommentList` на пост.

### Evidence / QA (скриншоты)

- Маршрут **`/admin/attention`** — в навигации тот же блок «Сотрудники», визуально ближе к официальным объявлениям, чем общая лента на `/admin`.
- Блок **«Публикация объявления»**: пояснение, что по умолчанию видят все сотрудники, аудиторию можно сузить после **«Опубликовать»**; поля **«Заголовок»**, **«Текст объявления»**; селекторы **«По категориям персонала»** (пусто = всем), **«Индивидуально»**, **«Приоритет»** (напр. «Обычный»); кнопки **«Отмена»** / **«Опубликовать»**.
- В ленте: у поста бейджи приоритета (напр. `NORMAL`), счётчик ознакомления (напр. `1/2`), действия **«Ознакомился»**, **«Кто ознакомился»**, ответы с выбором адресата и полем комментария.

## Инвентарь поверхностей UI (ось H)

- **Mantine `Modal`:** «Статус ознакомления» — списки `acknowledged` / `pending` (`ackStatusPostId`).
- **AdminDrawer / GlassModal:** нет.
- **`Alert`:** ошибки в блоке комментариев.
- **`Menu` / `ActionIcon`:** действия с комментариями (редактирование, удаление при правах).

## Целевой UX (target vs as-built)

- *target:* критичные объявления доводятся до всей клиники с подтверждением прочтения.
- *as-built:* объявления реализованы поверх staff feed API; приоритет визуально выделяет непрочитанное.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** тестов страницы не найдено.

## Gap scan (вторая редакция)

- Уточнить продуктово: `canPublish` на клиенте слишком широкий — сверить с политикой POST на бэкенде и при расхождении сузить UI.
