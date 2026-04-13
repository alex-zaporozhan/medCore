# Admin Doctor Schedule

## Метаданные

- **Path:** `/admin/doctor-schedule`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminDoctorSchedulePage`
- **Файл страницы:** `frontend/src/admin/pages/AdminDoctorSchedulePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminDoctorSchedulePage.tsx`<br>`frontend/src/hooks/useDoctors.ts ← импорт из frontend/src/admin/pages/AdminDoctorSchedulePage.tsx`<br>`frontend/src/hooks/useDoctorScheduleConfig.ts ← импорт из frontend/src/admin/pages/AdminDoctorSchedulePage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminDoctorSchedulePage.tsx`<br>… +4 файлов |
| Строк (сумма по фрагментам) | 752 |
| Хуки (эвристика, union) | `useAbsence`, `useAdminClinic`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreateAbsence`, `useCreateOrUpdateWorkingHours`, `useDeleteAbsence`, `useDeleteWorkingHours`, `useDoctor`, `useDoctorScheduleConfig`, `useDoctors`, `useMutation`, `useQuery`, `useQueryClient`, `useUpdateWorkingHours`, `useWorkingHours` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 1, GlassModal: 7, Modal: 1, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Выбор врача клиники и настройка рабочих часов по дням недели и периодов отсутствия (отпуск/нерабочие дни). Связь со слотами расписания — пояснение в UI. Query `doctor_id` предзаполняет селект, если id есть среди врачей клиники.

## Логика и данные

- **Хуки:** `useDoctors({ clinic_id })`, `useWorkingHours`, `useCreateOrUpdateWorkingHours`, `useDeleteWorkingHours`, `useAbsence`, `useCreateAbsence`, `useDeleteAbsence` (`frontend/src/hooks/useDoctorScheduleConfig.ts`).
- **queryKey:** `["doctors", filters]`; `["admin","doctor-schedule", doctorId, "working-hours"]`; `["admin","doctor-schedule", doctorId, "absence"]`.
- **API:** `GET|POST /v1/admin/doctors/{doctor_id}/working-hours`; `DELETE .../working-hours/{wh_id}`; `GET|POST /v1/admin/doctors/{doctor_id}/absence`; `DELETE .../absence/{absence_id}`.

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для `doctor-schedule` ключа нет (**fact**).
- Box не блокирует сегмент.

## UI-скелет (as-built)

`ContextBar` («График врачей») → `Paper` с `Select` врача → при отсутствии выбора — `EmptyStateHint` → два `Paper`: таблица рабочих часов с «Добавить день», таблица отпусков с «Добавить период»; `DataSkeleton` при загрузке.

## Инвентарь поверхностей UI (ось H)

- **`GlassModal` (2):** «Рабочий день» — день недели, время начала/конца, сохранение через `createWh` (`loading={createWh.isPending}`); «Отпуск / нерабочий период» — даты и причина, `createAbsence`.
- **`AdminDrawer` / Mantine `Modal`:** на странице нет.
- **Удаление:** `ActionIcon` в строках таблиц вызывает `deleteWh` / `deleteAbsence` без дополнительного диалога.

## Целевой UX (target vs as-built)

- *target:* подтверждение удаления, копирование недели, валидация пересечений интервалов на клиенте или сообщения с бэкенда.
- *as-built:* минималистичные модалки + прямое удаление строки.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Нет confirm перед удалением рабочего дня или отпуска.
- Ввод времени — свободный текст `ЧЧ:ММ` без маски.
