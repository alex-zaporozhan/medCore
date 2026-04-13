# App History

## Метаданные

- **Path:** `/app/history` и зеркало `/c/:clinicSlug/app/history`
- **Зона:** app (пациент)
- **Компонент(ы) в App.tsx:** `HistoryPage`
- **Файл страницы:** `frontend/src/app/pages/HistoryPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/app/pages/HistoryPage.tsx`<br>`frontend/src/contexts/PatientAuthContext.tsx ← импорт из frontend/src/app/pages/HistoryPage.tsx`<br>`frontend/src/shared/emptyStateHint.tsx ← импорт из frontend/src/app/pages/HistoryPage.tsx` |
| Строк (сумма по фрагментам) | 156 |
| Хуки (эвристика, union) | `useCancelPatientBooking`, `useClinics`, `usePatientAuth`, `usePatientBookings` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Таблица записей пациента по клиникам: дата, время, статус; для активных записей кнопка отмены с мутацией DELETE. Пустое состояние с подсказкой перейти в быструю запись.

## Логика и данные

- **Хуки:** `usePatientAuth`; `useClinics` для подписи названия клиники; `usePatientBookings`; `useCancelPatientBooking(accessToken)`.
- **queryKey:** `patient-bookings`, patientId; список клиник — как в `useClinics`.
- **API:** `GET /v1/patient/bookings?patient_id=…` с токеном; `DELETE /v1/patient/bookings/{bookingId}?patient_id=…` при отмене.

## RBAC / entitlements / edition

- Запросы завязаны на `patientId` и Bearer пациента (**fact**).

## UI-скелет (as-built)

Загрузка — полноэкранный `Loader`. Ошибка — `Title` + `QueryErrorAlert`. Пусто — `EmptyStateHint`. Данные — `Title` + `Table` с кнопкой «Отменить» в строке (если статус не cancelled/completed).

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal:** нет; отмена без диалога подтверждения.

## Целевой UX (target vs as-built)

- *target:* подтверждение отмены, детали записи, повторная запись.
- *as-built:* плоская таблица и прямой DELETE по клику.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Нет модалки «Вы уверены?» перед отменой.
- Нет пагинации при длинной истории.
