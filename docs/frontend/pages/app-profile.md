# App Profile

## Метаданные

- **Path:** `/app/profile` и зеркало `/c/:clinicSlug/app/profile`
- **Зона:** app (пациент)
- **Компонент(ы) в App.tsx:** `ProfilePage`
- **Файл страницы:** `frontend/src/app/pages/ProfilePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/app/pages/ProfilePage.tsx`<br>`frontend/src/contexts/PatientAuthContext.tsx ← импорт из frontend/src/app/pages/ProfilePage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/app/pages/ProfilePage.tsx`<br>`frontend/src/shared/semanticUi.ts ← импорт из frontend/src/app/pages/ProfilePage.tsx` |
| Строк (сумма по фрагментам) | 436 |
| Хуки (эвристика, union) | `usePatientAuth`, `usePatientLoyaltyMe` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Профиль пациента: блок кошелька лояльности (баланс, валюта, ссылка в раздел лояльности), заглушка если кошелька нет, реферальный блок с Web Share API или копированием origin+home в буфер, выход в маркетинговый лендинг.

## Логика и данные

- **Хуки:** `usePatientAuth` (`accessToken`, `logout`); `usePatientLoyaltyMe(accessToken)` из `@/hooks/useLoyalty`; `useNavigate`.
- **queryKey:** `patient`, `loyalty`, `me`.
- **API:** `GET /v1/patient/loyalty/me` через `authApi(accessToken)` (Bearer пациента).

## RBAC / entitlements / edition

- Страница внутри пациентского shell; без токена запрос лояльности не уходит (**fact**).

## UI-скелет (as-built)

`Stack` с `Title`, одна или две `Card` (кошелёк и/или подсказка про лояльность), `Card` реферала с кнопкой, `Button` выхода с `navigate` на лендинг.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal, Menu:** на странице нет.

## Целевой UX (target vs as-built)

- *target:* редактирование профиля, уведомления, привязка телефона.
- *as-built:* только лояльность, шаринг и logout; имя на домашней странице берётся отдельно из `/v1/patient/me`, не отсюда.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Текст шаринга и заголовок зашиты на «Dental Booking» и сумму в рублях без i18n.
- Нет отображения ошибки загрузки `loyalty/me` (при сбое кошелёк просто не показывается).
