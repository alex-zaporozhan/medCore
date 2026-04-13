# Admin Administrators

## Метаданные

- **Path:** `/admin/administrators`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminAdministratorsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminAdministratorsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminAdministratorsPage.tsx`<br>`frontend/src/hooks/useStaffDirectory.ts ← импорт из frontend/src/admin/pages/AdminAdministratorsPage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/admin/pages/AdminAdministratorsPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminAdministratorsPage.tsx`<br>… +3 файлов |
| Строк (сумма по фрагментам) | 2228 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreateStaffDirectoryAdminMutation`, `useCreateStaffProfessionCategoryMutation`, `useDeleteStaffProfessionCategoryMutation`, `useMutation`, `usePatchStaffDirectoryAdminMutation`, `usePatchStaffProfessionCategoryMutation`, `useQuery`, `useQueryClient`, `useRbacCatalog`, `useStaffDirectory`, `useStaffDirectoryAdmins`, `useStaffProfessionCategories` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 5, Menu: 5 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Каталог персонала клиники (Enterprise): категории профессий с типовыми ролями, таблица сотрудников с вкладками по категориям, смена категории у сотрудника, мастер создания категории (2 шага: название, типовые роли), мастер нового сотрудника (3 шага: учётка, категория, роли), редактирование категории с предупреждением о синхронизации ролей. Ссылка на «Права и политики» для тонкой настройки RBAC. Контекст клиники — `Select` в шапке блока.

## Логика и данные

- **Хуки:** `useAdminClinic`; `useStaffProfessionCategories`, `useStaffDirectoryAdmins`, `useCreateStaffProfessionCategoryMutation`, `usePatchStaffProfessionCategoryMutation`, `useDeleteStaffProfessionCategoryMutation`, `useCreateStaffDirectoryAdminMutation`, `usePatchStaffDirectoryAdminMutation`; `useRbacCatalog` (`frontend/src/hooks/useStaffDirectory.ts`, `useAdminRbacManagement.ts`).
- **queryKey:** `queryKeys.staffDirectory.professionCategories`, `staffDirectory.admins`, `queryKeys.rbac.catalog(effectiveClinicId)` и др. по префиксу RBAC при инвалидации.
- **API:** `GET/POST/PATCH/DELETE /v1/admin/clinics/{clinic_id}/staff-directory/profession-categories` и `.../{category_id}`; `GET/POST/PATCH /v1/admin/clinics/{clinic_id}/staff-directory/admins` и `.../admins/{admin_id}`; каталог ролей — `GET /v1/admin/rbac/catalog` (с учётом effective clinic query, см. хук).

## RBAC / entitlements / edition

- Каталог ролей требует права уровня **`rbac.manage`** (сообщения в `Alert` при недоступности каталога); без ролей мастера категорий/сотрудников деградируют.
- В `SEGMENT_ENTITLEMENT` для `administrators` ключа нет (**fact**).
- Box не блокирует сегмент.
- Операции при `clinicId === null` отключены (кнопки `disabled`).

## UI-скелет (as-built)

Заголовок и пояснение — `Paper` с `Select` клиники — две колонки `SimpleGrid`: категории (таблица, кнопка мастера) и сотрудники (фильтр, кнопка «Новый сотрудник», `Tabs` с таблицами) — модальные сценарии ниже.

## Инвентарь поверхностей UI (ось H)

- **`Modal` (Mantine), несколько:** смена категории у сотрудника; развёрнутая таблица (`ScrollArea`); мастер категории (`Stepper`, `Progress`, `Alert`); мастер сотрудника (3 шага); редактирование категории (`MultiSelect` типовых ролей, предупреждение о синхронизации).
- **`Menu`:** действия по строке сотрудника (контекстные пункты).
- **`AdminDrawer` / `GlassModal`:** нет.

## Целевой UX (target vs as-built)

- *target:* единый стиль модалок с `GlassModal` при унификации админки.
- *as-built:* тяжёлые сценарии в Mantine `Modal` + `Stepper`.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Ошибки бэкенда прогоняются через `humanizeStaffDirectoryError` для части кейсов; остальное — сырой текст.
