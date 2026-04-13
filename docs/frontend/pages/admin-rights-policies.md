# Admin Rights Policies

## Метаданные

- **Path:** `/admin/rights-policies`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminRightsPoliciesPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminRightsPoliciesPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminRightsPoliciesPage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/admin/pages/AdminRightsPoliciesPage.tsx`<br>`frontend/src/admin/rbacDomainGlossary.ts ← импорт из frontend/src/admin/pages/AdminRightsPoliciesPage.tsx`<br>`frontend/src/admin/rbacCsvExport.ts ← импорт из frontend/src/admin/pages/AdminRightsPoliciesPage.tsx`<br>… +6 файлов |
| Строк (сумма по фрагментам) | 4429 |
| Хуки (эвристика, union) | `useAckStaffCalendarInvitation`, `useAckStaffFeedPost`, `useAddStaffFeedComment`, `useAdminClinic`, `useAdminRbacManagement`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreateClinicRole`, `useCreateKnowledgeDocument`, `useCreateStaffCalendarEvent`, `useCreateStaffDmRoom`, `useCreateStaffFeedPost`, `useCreateStaffGroupRoom`, `useDeleteClinicRole`, `useDeleteStaffFeedComment`, `useDeleteStaffFeedPost`, `useInviteStaffRoomMember`, `useKnowledgeDocuments`, `useMarkStaffChatRoomRead`, `useMutation`, `usePatchRbacPolicies`, `usePatchRolePermissions`, `usePatchUserPermissions`, `usePatchUserRoles`, `usePostStaffChatMessage`, `useQuery`, `useQueryClient`, `useRbacAudit`, `useRbacCatalog`, `useRbacPolicies`, `useRbacUsers`, `useStaffAnnouncementPublishPolicy`, `useStaffAnnouncementPublishPolicyAudit`, `useStaffAnnouncements`, `useStaffCalendarEventDetails`, `useStaffCalendarEvents`, `useStaffCalendarMonthGrid`, `useStaffChatMessages`, `useStaffChatRooms`, `useStaffCollab`, `useStaffFeedComments`, `useStaffFeedPostAckStatus`, `useStaffFeedPosts`, `useStaffTaskChatRoom`, `useToggleStaffFeedPostLike`, `useUpdateKnowledgeDocument`, `useUpdateStaffAnnouncementPublishPolicy`, `useUpdateStaffCalendarEvent`, `useUpdateStaffFeedComment`, `useUpdateStaffFeedPost`, `useUploadStaffChatAttachment`, `useUploadStaffFeedCommentAttachment`, `useUploadStaffFeedPostAttachment` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/admin/auth/session`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 3, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Единый экран RBAC и смежных политик: каталог ролей и прав, редактирование прав роли и ролей/оверрайдов сотрудника, клинические политики (уведомления пациента, morning brief, AI supervisor), аудит RBAC, для владельца — запреты на публикацию объявлений в ленте сотрудников и журнал изменений. Доступ к основному UI только при праве `ADMIN_PERM_RBAC_MANAGE` в сессии админа.

## Логика и данные

- **Контекст:** `useAdminClinic` задаёт `effectiveClinicId` для query-параметра `effective_clinic_id` на admin RBAC API (сеть клиник у owner).
- **Хуки (RBAC):** из `@/hooks` / `useAdminRbacManagement`: `useRbacCatalog`, `useRbacUsers`, `useRbacPolicies`, `useRbacAudit`, `usePatchRolePermissions`, `usePatchUserRoles`, `usePatchUserPermissions`, `usePatchRbacPolicies`, `useCreateClinicRole`, `useDeleteClinicRole`.
- **Хуки (сессия и коллаб):** `useAdminSession` — permissions, roles; `useStaffAnnouncementPublishPolicy`, `useUpdateStaffAnnouncementPublishPolicy`, `useStaffAnnouncementPublishPolicyAudit` из `useStaffCollab`.
- **queryKey:** префикс `queryKeys.rbac.*` для каталога, пользователей, политик, аудита; staff policy — ключ `staff-collab`, `announcements`, `publish-policy`.
- **API (типовые пути):**
  - `GET /v1/admin/rbac/catalog`, `users`, `policies`; `GET /v1/admin/rbac/audit?limit=…`
  - `POST /v1/admin/rbac/roles`, `DELETE /v1/admin/rbac/roles/{roleId}`, `PATCH …/roles/{id}/permissions`, `PATCH …/users/{id}/roles`, `PATCH …/users/{id}/permissions`, `PATCH /v1/admin/rbac/policies` (все с опциональным query `effective_clinic_id`)
  - Объявления: `GET`/`PUT /v1/admin/staff/feed/announcements/publish-policy`, `GET …/publish-policy/audit?limit=…`
- **Deep link:** query `?user=<admin_id>` переключает вкладку на пользователей и выбирает сотрудника, если он есть в списке.

## RBAC / entitlements / edition

- Вход на страницу: без права RBAC manage показывается `Alert` «нет доступа» (**fact**).
- В `SEGMENT_ENTITLEMENT` для сегмента `rights-policies` отдельного ключа SaaS-entitlement нет (**fact**); гейт — permission из сессии.
- Блок «Права на публикацию объявлений» и журнал аудита объявлений — только для роли owner (плюс отдельное право на просмотр журнала объявлений).

## UI-скелет (as-built)

`ContextBar`, переключатель языка UI (RU/EN) для подписей и ошибок API, информационные `Paper`/`Card`, вкладки Mantine `Tabs`: роли, пользователи, политики, аудит RBAC. Внутри — `Select`/`MultiSelect`, таблицы, `Collapse` со словарём доменов, экспорт CSV в браузере.

## Инвентарь поверхностей UI (ось H)

- **Modal (Mantine), не AdminDrawer:** (1) создание клинической роли — форма с пресетами и копированием прав; (2) подтверждение удаления роли; (3) критическое подтверждение (чекбокс) перед опасными изменениями прав роли owner, снятием критичных ролей у себя или deny `rbac.manage` у себя — затем вызов соответствующей мутации.
- **AdminDrawer, GlassModal:** нет.
- **Alert, Tooltip:** множественные подсказки и предупреждения (защита owner, гранты/денаи).

## Целевой UX (target vs as-built)

- *target:* пошаговые мастера, симуляция эффективных прав до сохранения, разделение «политики клиники» и «RBAC» на разные маршруты.
- *as-built:* один тяжёлый экран с вкладками; дублирование части переключателей уведомлений с отдельной страницей `notification-policy` (разные API-контуры).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Политики уведомлений пациента редактируются и здесь (RBAC policies PATCH), и на `/admin/notification-policy` (отдельный PUT) — риск рассинхрона восприятия у оператора.
- Объём экрана и число сценариев на одной странице усложняют onboarding и регрессионное тестирование без e2e.
