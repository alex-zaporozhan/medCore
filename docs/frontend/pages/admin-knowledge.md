# Admin Knowledge

## Метаданные

- **Path:** `/admin/knowledge`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminKnowledgePage`
- **Файл страницы:** `frontend/src/admin/pages/AdminKnowledgePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminKnowledgePage.tsx`<br>`frontend/src/hooks/useStaffCollab.ts ← импорт из frontend/src/admin/pages/AdminKnowledgePage.tsx` |
| Строк (сумма по фрагментам) | 917 |
| Хуки (эвристика, union) | `useAckStaffCalendarInvitation`, `useAckStaffFeedPost`, `useAddStaffFeedComment`, `useCreateKnowledgeDocument`, `useCreateStaffCalendarEvent`, `useCreateStaffDmRoom`, `useCreateStaffFeedPost`, `useCreateStaffGroupRoom`, `useDeleteStaffFeedComment`, `useDeleteStaffFeedPost`, `useInviteStaffRoomMember`, `useKnowledgeDocuments`, `useMarkStaffChatRoomRead`, `useMutation`, `usePostStaffChatMessage`, `useQuery`, `useQueryClient`, `useStaffAnnouncementPublishPolicy`, `useStaffAnnouncementPublishPolicyAudit`, `useStaffAnnouncements`, `useStaffCalendarEventDetails`, `useStaffCalendarEvents`, `useStaffCalendarMonthGrid`, `useStaffChatMessages`, `useStaffChatRooms`, `useStaffCollab`, `useStaffFeedComments`, `useStaffFeedPostAckStatus`, `useStaffFeedPosts`, `useStaffTaskChatRoom`, `useToggleStaffFeedPostLike`, `useUpdateKnowledgeDocument`, `useUpdateStaffAnnouncementPublishPolicy`, `useUpdateStaffCalendarEvent`, `useUpdateStaffFeedComment`, `useUpdateStaffFeedPost`, `useUploadStaffChatAttachment`, `useUploadStaffFeedCommentAttachment`, `useUploadStaffFeedPostAttachment` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 2, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

База знаний клиники: статьи в Markdown, сгруппированные по ключу папки (`folder_key`), с настройкой видимости по ролям (`owner`, `manager`, `admin`, `doctor`). Создание новой статьи и редактирование существующей через модальные формы.

## Логика и данные

- **Хуки:** `useKnowledgeDocuments`, `useCreateKnowledgeDocument`, `useUpdateKnowledgeDocument` (`frontend/src/hooks/useStaffCollab.ts`); во вложенном `EditDocForm` повторно `useKnowledgeDocuments` + `useUpdateKnowledgeDocument(docId)`.
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/staff/knowledge/documents`
  - `POST /v1/admin/staff/knowledge/documents` (`title`, `body_md`, `folder_key`, `visible_roles`)
  - `PATCH /v1/admin/staff/knowledge/documents/{docId}`

## RBAC / entitlements / edition

- **fact:** Сегмент `knowledge` не задан в `SEGMENT_ENTITLEMENT` — отдельного entitlement-ключа в навигационной карте нет; видимость контента частично моделируется полем `visible_roles` в документе (сервер должен отфильтровать выдачу под роль текущего админа).
- **edition:** не используется на уровне страницы (as-built).

## UI-скелет (as-built)

- `ContextBar` «База знаний», краткое пояснение, кнопка «Новая статья».
- Состояния: `PageSkeleton`, `QueryErrorAlert`, `EmptyState`, либо `Accordion` по папкам; внутри панели — карточки статей (заголовок, бейджи ролей, дата/автор, тело `body_md` как pre-wrap).
- Вложенный компонент `EditDocForm` для модалки редактирования.

### Evidence / QA (скриншоты)

- URL **`/admin/knowledge`**. Подзаголовок: **«Статьи по ролям; видимость настраивается при создании»**. Пустое состояние: **«Пока пусто. Добавьте регламенты и инструкции для команды»**.
- Модалка **«Новая статья»**: **«Папка (ключ)»** (напр. `general`), **«Заголовок»**, **«Видимость для ролей»** (мультивыбор: Владелец, Менеджер, Администратор, Врач / мастер), **«Текст (Markdown)»**, **«Отмена»** / **«Сохранить»**.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer / GlassModal:** нет.
- **Mantine `Modal`:** «Новая статья» (`createOpen`); «Редактировать статью» (`editId`) с формой сохранения (**fact:** `loading` на кнопках от `createMut` / `updateMut`).

## Целевой UX (target vs as-built)

- *target:* регламенты и инструкции доступны релевантным ролям без лишней навигации.
- *as-built:* Markdown хранится и показывается как plain text (без рендера MD) — осознанное упрощение или **gap** для улучшения читаемости.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** тестов страницы не найдено.

## Gap scan (вторая редакция)

- Отсутствие MD-рендера и оглавления при росте базы — зона улучшения продукта.
- Права на создание/редактирование целиком на бэкенде; на фронте нет явного disable кнопок по permissions — при 403 стоит унифицировать сообщения (как на других admin-страницах).
