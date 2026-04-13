# Admin RAG KB

## Метаданные

- **Path:** `/admin/rag-kb`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminRagKbPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminRagKbPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminRagKbPage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/admin/pages/AdminRagKbPage.tsx`<br>`frontend/src/hooks/useAdminRagKb.ts ← импорт из frontend/src/admin/pages/AdminRagKbPage.tsx`<br>`frontend/src/hooks/useAdminSession.ts ← импорт из frontend/src/admin/pages/AdminRagKbPage.tsx` |
| Строк (сумма по фрагментам) | 852 |
| Хуки (эвристика, union) | `useAdminRagKb`, `useAdminRagKbDocument`, `useAdminRagKbDocuments`, `useAdminSession`, `useCreateRagKbDocumentMutation`, `useDeleteRagKbDocumentMutation`, `useMutation`, `useQuery`, `useQueryClient`, `useUpdateRagKbDocumentMutation` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/admin/auth/session`, `/v1/admin/organization/rag-kb/documents`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 1, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Управление фрагментами базы знаний организации для RAG: создание (заголовок + текст), список с датой обновления, правка в модальном окне (подгрузка полного текста по id), удаление строки.

## Логика и данные

- **Хуки:** `useAdminSession`, `useAdminRagKbDocuments`, `useAdminRagKbDocument`, `useCreateRagKbDocumentMutation`, `useUpdateRagKbDocumentMutation`, `useDeleteRagKbDocumentMutation` (`frontend/src/hooks/useAdminRagKb.ts`).
- **queryKey:** `queryKeys.adminRagKb.documents()`, `queryKeys.adminRagKb.document(id)`.
- **API:** `GET /v1/admin/organization/rag-kb/documents`; `GET /v1/admin/organization/rag-kb/documents/{id}`; `POST` (create); `PATCH` (update); `DELETE`.

## RBAC / entitlements / edition

- **Entitlement:** `ai.rag.org_kb` — `SEGMENT_ENTITLEMENT["rag-kb"]`; при отказе — жёлтый `Alert` с текстом про опцию тарифа.
- Без `organization_id` в сессии — серый `Alert` про привязку и опцию.
- **Box:** сегмент `rag-kb` в `BOX_DISALLOWED_ADMIN_SEGMENTS` — редирект на дашборд в редакции Box.

## UI-скелет (as-built)

`ContextBar` → при `orgReady`: **`Modal`** редактирования → `AdminSettingsSectionCard` «Новый фрагмент» → `AdminSettingsSectionCard` «Документы» с `Table` и кнопками «Изменить» / «Удалить».

## Инвентарь поверхностей UI (ось H)

- **`Modal` (Mantine):** редактирование — загрузка детали (`Loader` / `Alert` при ошибке), поля `TextInput`/`Textarea`, сохранение с `loading={updateMut.isPending}`.
- **`AdminDrawer` / `GlassModal`:** нет.
- **Удаление:** кнопка в таблице вызывает `delMut.mutate(id)` без диалога подтверждения (**gap**).

## Целевой UX (target vs as-built)

- *target:* подтверждение удаления; для длинных текстов — `AdminDrawer` вместо модалки.
- *as-built:* компактный `Modal` + прямое удаление.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Сырой `Modal` вместо `GlassModal` — расхождение с частью остальной админки (зафиксировать при унификации оси H).
