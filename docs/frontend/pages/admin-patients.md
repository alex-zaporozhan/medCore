# Admin Patients

## Метаданные

- **Path:** `/admin/patients`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminPatientsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminPatientsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminPatientsPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminPatientsPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminPatientsPage.tsx`<br>`frontend/src/admin/components/entity/PatientEntityDrawer.tsx ← импорт из frontend/src/admin/pages/AdminPatientsPage.tsx`<br>… +2 файлов |
| Строк (сумма по фрагментам) | 2084 |
| Хуки (эвристика, union) | `useAddFamilyMember`, `useAdminBookings`, `useAdminClinic`, `useAdminFormTemplates`, `useAdminLoyaltySummaryByContact`, `useAdminPatientDiagnoses`, `useAdminPatientMedicalFiles`, `useAdminPatientMedicalVisits`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreateAdminPatientDiagnosis`, `useCreateAdminPatientMedicalVisit`, `useCreatePatient`, `useDeletePatient`, `useDoctors`, `usePatientAiInsight`, `usePatients`, `useQueryClient`, `useSendFormLink`, `useUpdatePatient`, `useUploadAdminPatientMedicalFile` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 6, GlassModal: 3, Modal: 2, Menu: 13 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Реестр пациентов клиники с фильтрами (телефон, ФИО, интервал дат визита), карточка пациента в drawer, создание/правка, отправка ссылки на цифровую форму и удаление с подтверждением. Deep link `?patient_id=` открывает просмотр после загрузки списка.

## Логика и данные

- **Хуки:** `useAdminSession`, `useAdminClinic`, `usePatients`, `useAdminFormTemplates`, `useSendFormLink`, `useDeletePatient`, `useQueryClient`.
- **queryKey:** `["patients", filters]` (объект фильтров включает `clinic_id`, `phone`, `full_name`, `visited_from`, `visited_to`, …).
- **API:** `GET /v1/patients?...`; мутации карточки — в `PatientEntityDrawer` / `useCreatePatient`, `useUpdatePatient` (`POST/PUT /v1/patients`); `DELETE /v1/patients/{id}`; отправка формы — `POST /v1/admin/forms/send-link` (через `useSendFormLink`).

## RBAC / entitlements / edition

- **Permission:** без `ADMIN_PERM_PATIENTS_PII_READ` в сессии показывается жёлтый `Alert` «Нет доступа» (константа `frontend/src/shared/adminPermissions.ts`).
- **Entitlement:** в `SEGMENT_ENTITLEMENT` для сегмента `patients` записи нет (**fact**).
- **Box:** сегмент не в `BOX_DISALLOWED_ADMIN_SEGMENTS`.

## UI-скелет (as-built)

`ContextBar` + `AdminDataTableToolbar` с полями фильтра; предупреждение, если фильтр по датам визита без выбранной клиники; `EmptyState` или `AdminDataTableSurface` / `Table`; строки кликабельны (`data-table-clickable-row`), меню действий в ячейке.

## Инвентарь поверхностей UI (ось H)

- **`PatientEntityDrawer`:** на базе **`AdminDrawer`** (+ внутри **`GlassModal`** и прочие формы — см. `PatientEntityDrawer.tsx`).
- **`AdminDrawer`:** «Отправить форму» — выбор шаблона и канала (`copy_only` / WhatsApp / SMS), `sendFormLink.mutate` с `loading={sendFormLink.isPending}`; при успехе и `copy_only` — попытка `navigator.clipboard.writeText`.
- **`Modal` (Mantine):** подтверждение удаления пациента; `deletePatient.mutate` с `loading={deletePatient.isPending}`.
- **`Menu` / `HoverCard`:** действия и превью по ФИО.

## Целевой UX (target vs as-built)

- *target:* единый стиль подтверждений (`GlassModal` / политика админки).
- *as-built:* удаление через Mantine `Modal`; отправка формы — отдельный `AdminDrawer` (соответствует гайду правой панели).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Если `patient_id` в URL не попадает в отфильтрованный список — жёлтое предупреждение; UX зависит от того, сбросит ли пользователь фильтры.
