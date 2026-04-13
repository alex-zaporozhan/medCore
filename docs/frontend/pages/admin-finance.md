# Admin Finance

## Метаданные

- **Path:** `/admin/finance`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminFinancePage`
- **Файл страницы:** `frontend/src/admin/pages/AdminFinancePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminFinancePage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminFinancePage.tsx`<br>`frontend/src/components/layout/ThreeColumnLayout.tsx ← импорт из frontend/src/admin/pages/AdminFinancePage.tsx` |
| Строк (сумма по фрагментам) | 1073 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminSession`, `useBusinessLexicon`, `useCashboxes`, `useClinics`, `useCreateFinanceTransaction`, `useDoctors`, `useFinanceLiability`, `useFinanceTransactions`, `useInventoryProducts`, `useInventoryStock`, `useInventoryTransactions`, `usePayrollPolicies`, `useSalaryTransactions`, `useWarehouses` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 3, GlassModal: 0, Modal: 0, Menu: 6 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Финансы и ERP клиники: вкладки **Кассы** (балансы, меню внесение/изъятие/перевод), **Транзакции** (фильтры, список, `ThreeColumnLayout`), **Зарплаты** (политики, начисления по врачу), **Склад** (товары, склады, движения, остаток). Операции прихода/расхода/перевода — через один **`AdminDrawer`** с режимом `income` | `expense` | `transfer`.

## Логика и данные

- **Хуки:** `useCashboxes`, `useFinanceTransactions`, `useFinanceLiability`, `useCreateFinanceTransaction` (`useErpFinance.ts`); `useDoctors`; `usePayrollPolicies`, `useSalaryTransactions` (`useErpPayroll.ts`); `useInventoryProducts`, `useWarehouses`, `useInventoryTransactions`, `useInventoryStock` (`useErpInventory.ts`); `useAdminClinic`.
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/clinics/{clinicId}/finance/cashboxes`
  - `GET /v1/admin/clinics/{clinicId}/finance/transactions?...`
  - `GET /v1/admin/clinics/{clinicId}/finance/liability`
  - `POST /v1/admin/clinics/{clinicId}/finance/transactions`
  - `GET /v1/admin/clinics/{clinicId}/payroll/policies` · `GET .../payroll/transactions?...`
  - `GET /v1/admin/clinics/{clinicId}/inventory/products` · `.../warehouses` · `.../transactions?...` · `.../stock?...`

## RBAC / entitlements / edition

- **fact:** Сегмент `finance` **не** в `SEGMENT_ENTITLEMENT`.

## UI-скелет (as-built)

- `ContextBar` «Финансы и ERP» (при отсутствии клиники — подсказка).
- **`Tabs`:** cashboxes | transactions | payroll | inventory.
- Таблицы касс с **`Menu`** действий; карточка unearned revenue; складские карточки с фильтрами по датам.

## Инвентарь поверхностей UI (ось H)

- **Один `AdminDrawer`:** заголовок зависит от `txDrawerMode` («Внести в кассу» / «Изъять» / «Перевод между кассами»); форма суммы, категории, выбор касс для transfer.
- **GlassModal:** нет.
- **fact:** `EmptyState` «Добавить кассу» с `onClick: () => {}` — **gap:** нет реализации создания кассы из UI.

## Целевой UX (target vs as-built)

- *target:* касса, зарплата и склад в одном разделе для операционного учёта.
- *as-built:* транзакции закрыты через drawer; создание кассы не подключено.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** тестов страницы не найдено.

## Gap scan (вторая редакция)

- Реализовать создание кассы или убрать вводящую в заблуждение кнопку; покрыть перевод между кассами интеграционным тестом из-за валидации пар from/to.
