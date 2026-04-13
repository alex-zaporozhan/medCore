# App Forms

## Метаданные

- **Path:** `/app/forms` и зеркало `/c/:clinicSlug/app/forms`
- **Зона:** app (пациент)
- **Компонент(ы) в App.tsx:** `FormsPage`
- **Файл страницы:** `frontend/src/app/pages/FormsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/app/pages/FormsPage.tsx`<br>`frontend/src/contexts/PatientAuthContext.tsx ← импорт из frontend/src/app/pages/FormsPage.tsx`<br>`frontend/src/api/types.ts ← импорт из frontend/src/app/pages/FormsPage.tsx`<br>`frontend/src/shared/ui/SignatureCanvas.tsx ← импорт из frontend/src/app/pages/FormsPage.tsx`<br>… +1 файлов |
| Строк (сумма по фрагментам) | 1263 |
| Хуки (эвристика, union) | `usePatientAuth`, `usePatientPendingForms`, `useSubmitPatientForm` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Список ожидающих цифровых анкет пациента и заполнение по JSON-схеме: text, textarea, number, select, checkbox (включая мультивыбор по options), date как строка ГГГГ-ММ-ДД. При флаге шаблона — обязательная электронная подпись (`SignatureCanvas`) и опциональное ФИО подписанта.

## Логика и данные

- **Хуки:** `usePatientAuth`; `usePatientPendingForms`, `useSubmitPatientForm` из `@/hooks/useForms`.
- **queryKey:** `patient`, `forms`, `pending`, token, опционально booking_id.
- **API:** `GET /v1/patient/forms/pending` с Bearer; `POST /v1/patient/forms/{templateCode}/submit` с телом data, опционально signature_payload и signer_name.

## RBAC / entitlements / edition

- Запросы только с токеном пациента (**fact**).

## UI-скелет (as-built)

Список: `Card` по шаблону, клик открывает форму. Форма: динамические поля Mantine, блок подписи, кнопки Отмена и Отправить.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal, Menu:** на странице нет.

## Целевой UX (target vs as-built)

- *target:* валидация схемы на клиенте по типам, прогресс сохранения черновика.
- *as-built:* отправка без пошаговой валидации кроме required в UI и блокировки submit без подписи.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Хук pending поддерживает фильтр `booking_id`, страница его не передаёт.
- Нет отображения ошибки мутации submit в UI.
