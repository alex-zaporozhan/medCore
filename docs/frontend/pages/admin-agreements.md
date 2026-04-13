# Admin Agreements

## Метаданные

- **Path:** `/admin/agreements`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminAgreementsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminAgreementsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminAgreementsPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminAgreementsPage.tsx`<br>`frontend/src/hooks/useAdminAgreements.ts ← импорт из frontend/src/admin/pages/AdminAgreementsPage.tsx`<br>`frontend/src/shared/emptyStateHint.tsx ← импорт из frontend/src/admin/pages/AdminAgreementsPage.tsx`<br>… +1 файлов |
| Строк (сумма по фрагментам) | 337 |
| Хуки (эвристика, union) | `useAdminAgreementSettings`, `useAdminAgreements`, `useAdminClinic`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useMutation`, `useQuery`, `useQueryClient`, `useUpdateAdminAgreementSettingsMutation` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Настройка текста соглашения на обработку ПД для регистрации пациента и флага «разрешить регистрацию без согласия на рассылку». Сохранение одной кнопкой обоих полей.

## Логика и данные

- **Хуки:** `useAdminClinic`; `useAdminAgreementSettings`, `useUpdateAdminAgreementSettingsMutation` из `@/hooks/useAdminAgreements`; локальный `useState` + `useEffect` для синхронизации с ответом GET.
- **queryKey:** `queryKeys.agreementSettings(clinicId)`.
- **API:**
  - `GET /v1/admin/clinics/{clinicId}/agreement-settings` — `clinic_id`, `pd_agreement_text`, `allow_registration_without_mailing_consent`.
  - `PUT /v1/admin/clinics/{clinicId}/agreement-settings` — то же в теле; пустой текст уходит как `null`.

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для сегмента `agreements` ключа нет (**fact**).

## UI-скелет (as-built)

Без клиники: `ContextBar` + `EmptyStateHint`. Загрузка: `ContextBar` + `Text` «Загрузка...». Ошибка: `QueryErrorAlert`. Основной вид: `ContextBar`, поясняющий `Text`, `Textarea` для ПД-текста, `Switch` для рассылки, кнопка «Сохранить» с `loading` мутации.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal, Menu, Stepper:** на странице нет.

## Целевой UX (target vs as-built)

- *target:* версионирование текста, предпросмотр как у пациента, юридические шаблоны.
- *as-built:* одно текстовое поле и один флаг без превью.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Ошибка сохранения не показана в UI (нет `QueryErrorAlert` на мутацию).
- Загрузка без `DataSkeleton`, только текст.
