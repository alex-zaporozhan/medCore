# App Loyalty

## Метаданные

- **Path:** `/app/loyalty` и зеркало `/c/:clinicSlug/app/loyalty`
- **Зона:** app (пациент)
- **Компонент(ы) в App.tsx:** `LoyaltyPage`
- **Файл страницы:** `frontend/src/app/pages/LoyaltyPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/app/pages/LoyaltyPage.tsx`<br>`frontend/src/contexts/PatientAuthContext.tsx ← импорт из frontend/src/app/pages/LoyaltyPage.tsx`<br>`frontend/src/shared/emptyStateHint.tsx ← импорт из frontend/src/app/pages/LoyaltyPage.tsx`<br>`frontend/src/api/types.ts ← импорт из frontend/src/app/pages/LoyaltyPage.tsx`<br>… +2 файлов |
| Строк (сумма по фрагментам) | 1299 |
| Хуки (эвристика, union) | `usePatientAuth`, `usePatientLoyaltyHistory`, `usePatientLoyaltyMe` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Экран лояльности: кошелёк (баланс, валюта), активные абонементы с прогресс-баром и кнопкой записи с query `subscription_id`, истёкшие в таблице, история операций wallet/subscription. Навигация на booking с `use_loyalty=wallet` или без параметров. Пустое состояние при отсутствии подписок и кошелька.

## Логика и данные

- **Хуки:** `usePatientAuth`; `usePatientLoyaltyMe`, `usePatientLoyaltyHistory` из `@/hooks/useLoyalty`; `useNavigate`.
- **queryKey:** `patient`, `loyalty`, `me` и `patient`, `loyalty`, `history`.
- **API:** `GET /v1/patient/loyalty/me`, `GET /v1/patient/loyalty/history` через `authApi(accessToken)`.

## RBAC / entitlements / edition

- Запросы с Bearer пациента (**fact**).

## UI-скелет (as-built)

Загрузка: `Loader`. Ошибки: `QueryErrorAlert`. Контент: `Title`, карточки кошелька и Digital Pass, таблицы истёкших и истории.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal, Menu:** на странице нет.

## Целевой UX (target vs as-built)

- *target:* человекочитаемые названия пакетов вместо усечённого id.
- *as-built:* прогресс визитов использует эвристику totalVisits от remaining_visits.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Прогресс-бар: `Math.max(s.remaining_visits, 10)` как знаменатель — продуктово спорно.
- История и me грузятся последовательно до общего Loader; при ошибке только одного из запросов UX зависит от порядка проверок.
