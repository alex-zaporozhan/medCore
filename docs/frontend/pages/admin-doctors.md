# Admin Doctors

## Метаданные

- **Path:** `/admin/doctors`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminDoctorsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminDoctorsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminDoctorsPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminDoctorsPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminDoctorsPage.tsx`<br>`frontend/src/admin/components/entity/DoctorEntityDrawer.tsx ← импорт из frontend/src/admin/pages/AdminDoctorsPage.tsx`<br>… +1 файлов |
| Строк (сумма по фрагментам) | 1695 |
| Хуки (эвристика, union) | `useAbsence`, `useAdminClinic`, `useAdminClinicServices`, `useAdminPublicDoctorProfileByDoctor`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreateAdminPublicDoctorProfileMutation`, `useCreateDoctor`, `useDeleteDoctor`, `useDoctorScheduleConfig`, `useDoctors`, `useErpPayroll`, `usePatchAdminPublicDoctorProfileMutation`, `usePayrollPolicies`, `useQueryClient`, `useSalaryTransactions`, `useUpdateDoctor`, `useWorkingHours` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 3, GlassModal: 3, Modal: 0, Menu: 12 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Список врачей выбранной клиники: просмотр карточки (клик по ФИО / меню), создание и редактирование через единый `DoctorEntityDrawer`, удаление из меню строки. Deep link: `doctor_id` и опционально `doctor_tab` (`profile` | `schedule` | `payroll` | `services`) открывают drawer после загрузки списка.

## Логика и данные

- **Хуки:** `useDoctors({ clinic_id: currentClinicId })`, `useDeleteDoctor`, `useQueryClient` для инвалидации `["doctors"]` после сохранения в drawer.
- **queryKey:** `["doctors", filters]` с объектом фильтров.
- **API (страница + drawer):** `GET /v1/doctors?clinic_id=...`; мутации создания/обновления/удаления — в `DoctorEntityDrawer` / `useDoctorsMutations` (`POST/PUT/DELETE /v1/doctors`, `GET /v1/doctors/{id}` и др. — см. компонент drawer).

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для `doctors` ключа нет (**fact**).
- Box не блокирует сегмент.

## UI-скелет (as-built)

Загрузка — `PageSkeleton`; ошибка — `ContextBar` + `QueryErrorAlert`. Успех: `ContextBar` с кнопкой «Добавить врача», подсказка-текст, `EmptyState` или `Table` с `HoverCard` на ФИО, колонка действий — `Menu` (редактировать, карточка, удалить).

## Инвентарь поверхностей UI (ось H)

- **`DoctorEntityDrawer`** (`frontend/src/admin/components/entity/DoctorEntityDrawer.tsx`): обёртка на базе **`AdminDrawer`**; внутри также **`GlassModal`**, вкладки, формы профиля/расписания (read)/payroll/services — детали см. паспорт компонента при необходимости. На **самой** странице списка отдельных `Modal` нет.
- **`HoverCard`:** превью по наведению на ФИО.
- **`Menu`:** операции по строке.

## Целевой UX (target vs as-built)

- *target:* согласованный список + drawer уже близок к паттерну админки.
- *as-built:* удаление без подтверждающего модального окна на уровне страницы (**gap** UX/безопасность).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- `deleteMutation.mutate(d.id)` без confirm на странице списка.
- Синхронизация URL: при закрытии drawer сбрасываются `doctor_id` / `doctor_tab` из query.
