# Admin Discounts

## Метаданные

- **Path:** `/admin/discounts`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminDiscountsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminDiscountsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminDiscountsPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminDiscountsPage.tsx`<br>`frontend/src/hooks/useAdminDiscounts.ts ← импорт из frontend/src/admin/pages/AdminDiscountsPage.tsx`<br>`frontend/src/hooks/useAdminClinicServices.ts ← импорт из frontend/src/admin/pages/AdminDiscountsPage.tsx`<br>… +3 файлов |
| Строк (сумма по фрагментам) | 742 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminClinicServices`, `useAdminDiscounts`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCreateAdminClinicService`, `useCreateAdminDiscountMutation`, `useDeleteAdminClinicService`, `useDeleteAdminDiscountMutation`, `useDoctor`, `useDoctors`, `useMutation`, `useQuery`, `useQueryClient`, `useUpdateAdminClinicService`, `useUpdateAdminDiscountMutation` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 3, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Список скидок клиники с типами (первый визит, услуга, врач, период), суммой или процентом, датами и флагом активности. Создание и правка в правой панели; удаление из строки таблицы без отдельного overlay.

## Логика и данные

- **Хуки:** `useAdminClinic`; `useAdminDiscounts`, `useCreateAdminDiscountMutation`, `useUpdateAdminDiscountMutation`, `useDeleteAdminDiscountMutation` из `@/hooks/useAdminDiscounts`; `useAdminClinicServices` для услуг при типе `service`; `useDoctors` с фильтром `clinic_id` и `is_active: true` для типа `doctor`; `useDisclosure` (Mantine) для панели.
- **queryKey:** `queryKeys.adminDiscounts(clinicId)`; услуги — ключ `admin`, `clinics`, `clinicId`, `services`; врачи — ключ `doctors` с объектом фильтров.
- **API:** `GET/POST /v1/admin/clinics/{clinicId}/discounts`; `PUT/DELETE /v1/admin/clinics/{clinicId}/discounts/{id}`; справочники `GET /v1/admin/clinics/{clinicId}/services` и `GET /v1/doctors` с query `clinic_id`, `is_active`.

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для сегмента `discounts` ключа нет (**fact**).

## UI-скелет (as-built)

Без клиники — короткая подсказка. Загрузка / ошибка — `DataSkeleton` / `QueryErrorAlert`. Основной экран: `ContextBar` с кнопкой «Добавить скидку», `Paper` с таблицей или `EmptyStateHint`, в строке кнопки «Изменить» и «Удалить».

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer** справа (`size="md"`): создание и редактирование; заголовок «Новая скидка» или «Изменить скидку»; внутри форма; при ошибке мутации — Mantine `Alert` с кнопкой закрытия; успех закрывает drawer.
- **GlassModal, Modal, Menu, Stepper:** на странице нет.
- Удаление — inline-кнопка, диалога подтверждения нет.

## Целевой UX (target vs as-built)

- *target:* предпросмотр применения скидки, аудит, подтверждение удаления.
- *as-built:* CRUD и drawer; удаление сразу по клику.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Нет диалога подтверждения удаления.
- Тип `period` в форме не добавляет отдельных полей периода сверх общих дат.
