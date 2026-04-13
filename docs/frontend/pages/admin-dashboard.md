# Дашборд админки

## Метаданные

- **Path:** `/admin` (index под `AdminLayout`)
- **Зона:** admin
- **Компонент в App.tsx:** `Route index element={<AdminDashboardPage />}`
- **Файл страницы:** `frontend/src/admin/pages/AdminDashboardPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminDashboardPage.tsx`<br>`frontend/src/hooks/useAdminReports.ts ← импорт из frontend/src/admin/pages/AdminDashboardPage.tsx`<br>`frontend/src/hooks/useStaffCollab.ts ← импорт из frontend/src/admin/pages/AdminDashboardPage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/admin/pages/AdminDashboardPage.tsx`<br>… +7 файлов |
| Строк (сумма по фрагментам) | 3413 |
| Хуки (эвристика, union) | `useAckStaffCalendarInvitation`, `useAckStaffFeedPost`, `useAddStaffFeedComment`, `useAdminClinic`, `useAdminReports`, `useAdminReportsDashboard`, `useAdminReportsDashboardAggregate`, `useAdminReportsDashboardByClinics`, `useAdminReportsNoShow`, `useAdminReportsRevenue`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreateKnowledgeDocument`, `useCreateStaffCalendarEvent`, `useCreateStaffDmRoom`, `useCreateStaffFeedPost`, `useCreateStaffGroupRoom`, `useDeleteStaffFeedComment`, `useDeleteStaffFeedPost`, `useInviteStaffRoomMember`, `useKnowledgeDocuments`, `useMarkStaffChatRoomRead`, `useMutation`, `useOwnerDashboard`, `usePostStaffChatMessage`, `useQuery`, `useQueryClient`, `useRevenueHunterSaved`, `useStaffAnnouncementPublishPolicy`, `useStaffAnnouncementPublishPolicyAudit`, `useStaffAnnouncements`, `useStaffCalendarEventDetails`, `useStaffCalendarEvents`, `useStaffCalendarMonthGrid`, `useStaffChatMessages`, `useStaffChatRooms`, `useStaffCollab`, `useStaffFeedComments`, `useStaffFeedPostAckStatus`, `useStaffFeedPosts`, `useStaffTaskChatRoom`, `useToggleStaffFeedPostLike`, `useUpdateKnowledgeDocument`, `useUpdateStaffAnnouncementPublishPolicy`, `useUpdateStaffCalendarEvent`, `useUpdateStaffFeedComment`, `useUpdateStaffFeedPost`, `useUploadStaffChatAttachment`, `useUploadStaffFeedCommentAttachment`, `useUploadStaffFeedPostAttachment`, `useWebAudio` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 3, Modal: 0, Menu: 10 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Операционный «дом» после входа: сводка по клиникам, staff feed (посты, комментарии, вложения), встройки отчётов и быстрые ссылки в модули.

## Логика и данные

- **Хуки:** `useAdminReportsDashboardByClinics`, `useStaffFeedPosts`, `useCreateStaffFeedPost`, `useUpdateStaffFeedPost`, `useDeleteStaffFeedPost`, `useToggleStaffFeedPostLike`, `useStaffFeedComments`, `useAddStaffFeedComment`, `useUploadStaffFeedCommentAttachment`, `useUpdateStaffFeedComment`, `useDeleteStaffFeedComment`, `useAdminSession`, `useAdminClinic`, `useRevenueHunterSaved`, `useQueryClient`; прямой `api.getBlob` / `api.postFormData` для вложений ленты.
- **Ключевые HTTP (типовые, см. `useStaffCollab.ts` / `useAdminReports.ts`):**
  - `GET /v1/admin/reports/dashboard-aggregate?...` — сводка по клиникам (мультивыбор).
  - `GET /v1/admin/staff/feed/posts`, `GET .../announcements`, `POST .../posts`, `PATCH/DELETE .../posts/{id}`, `POST .../like`, `POST .../ack`, `GET .../ack-status`, `POST .../attachments`, `GET .../attachments/{id}/file`.
  - Комментарии: `GET .../posts/{id}/comments`, `POST .../comments`, `PATCH .../comments/{id}`, `DELETE .../comments/{id}`, вложения к комментариям.
- **Инвалидация:** через мутации staff collab и `queryKeys` (детали в хуках).

## RBAC / entitlements / edition

Доступ через `AdminAuthGuard`; детали прав на уровне API для каждого действия — сверять с роутерами админки. Сегмент shell не используется (index), edition-блокировки сегментов на дашборде не применяются напрямую.

## UI-скелет (as-built)

- `ContextBar`, карточки метрик, лента staff feed (посты объявлений и обычные), комментарии к постам, `EmojiMartPopoverPicker` в композиторе, `PageSkeleton`, `EmptyState`, `QueryErrorAlert` из `@/shared/ui`.
- Контекст клиники: `useAdminClinic`, переключение клиник в layout (родитель).

### Evidence / QA (скриншоты)

- Раздел сайдбара **«СОТРУДНИКИ»**: первая точка — **«Лента»** (`/admin` index). В шапке контента — баннер подписки («режим без ограничений по SKU») при включённом сценарии платформы.
- Заголовок страницы **«Лента»**, бейдж **«Приоритетные сообщения»**, фильтр **«Клиники»** (мультивыбор тегами; пусто = все клиники с доступом).
- Карточки сводки (пример подписей): **Всего посещений** (завершённые записи), **Новые пациенты** (за день), **Отмены / неявки**, **Количество обращений** (уникальные в чате), **Настроение дня** (коэф. занятые/пустые), **Пустые окна** (часы свободных слотов).
- Лента: кнопка **«Добавить пост»**, карточки постов с автором/датой, вложениями, меню «⋯», у постов — **«Ответить»** и тред комментариев; композитор комментария с подсказкой про вложения без текста и кнопкой **«Отправить»**.

## Инвентарь поверхностей UI (as-built)

| Поверхность | Где в UI | Триггер | Мутация / данные | Примечание |
|-------------|----------|---------|------------------|------------|
| `GlassModal` «Редактировать пост» | Низ страницы (после ленты) | `Menu` поста → «Редактировать» (`setEditingPost(p)`) | `updatePost.mutate` из staff collab (title, body, file); `loading={updatePost.isPending}` | Вложения, превью файла, `input type="file"` (**fact**) |
| `Menu` (пост) | Шапка карточки поста (при `canPostToStaffFeed`) | `ActionIcon` «Действия с постом» | «Редактировать» → модалка; «Удалить» → `window.confirm` + `deletePost.mutateAsync` | (**fact**) |
| `Menu` (комментарий) | Строка комментария (автор или модератор) | `ActionIcon` «Действия» | «Редактировать» → inline-редактирование; «Удалить» → `window.confirm` + `deleteComment` | Не отдельное модальное окно (**fact**) |
| `EmojiMartPopoverPicker` | Область создания/редактирования поста (композитор) | Кнопка выбора emoji | Вставка в textarea | Поповер, не `Modal` (**fact**) |

`AdminDrawer` на этой странице **нет** (все детальные формы — inline или `GlassModal`).

## Целевой UX (target vs as-built)

- *target:* одна «живая» лента и понятные KPI без перегруза.
- *as-built:* высокая плотность контента; `BACKEND_HINT` при проблемах загрузки.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Нет выделенного `AdminDashboardPage.test.tsx` в быстром поиске по репозиторию (**gap**); косвенно — интеграционные сценарии staff feed, если появятся.

## Gap scan

- Таблица выше закрывает основной контур UI↔API для ленты и aggregate dashboard; узкие отчёты (no-show, revenue и т.д.) на этой странице — только если подтянуты в виджеты (сверять с кодом при изменениях).
- `BACKEND_HINT` в коде — dev-подсказка; не показывать сырой текст ошибок продакшена (**fact** `QueryErrorAlert`).
