# Auth Legacy Login Redirect

## Метаданные

- **Path:** `/login` (`ROUTE_PATHS.other.login`) → **мгновенный** редирект на главную с query
- **Зона:** patient-entry / legacy routing
- **Компонент(ы) в App.tsx:** `Navigate` → `ROUTE_PATHS.marketing.landing` + query `patientEntry=need-clinic`, `replace`
- **Файл страницы:** объявление маршрута в `frontend/src/App.tsx` (отдельного компонента-страницы нет)

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend\src\auth\LegacySignInRedirect.tsx` |
| Строк (сумма по фрагментам) | 44 |
| Хуки (эвристика, union) | — |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Сохранить старый URL `/login` (легаси «единый вход»): любой заход сюда перенаправляется на лендинг с подсказкой **patientEntry=need-clinic**, чтобы пользователь выбрал slug клиники, а не попадал в пустой экран.

## Логика и данные

- **Реализация:** статический `Navigate` с `replace` — без хуков, без API.
- **Целевой URL:** `/?patientEntry=need-clinic` (см. паспорт [`marketing-landing.md`](./marketing-landing.md) — обработка значения `need-clinic` для ключа `patientEntry`).

## RBAC / entitlements / edition

Публичный редирект; гейтов нет (**fact**).

## UI-скелет (as-built)

Нет собственного UI — один кадр перенаправления (как у [`auth-legacy-sign-in.md`](./auth-legacy-sign-in.md) с лоадером, здесь даже лоадера нет: мгновенный `Navigate`).

## Инвентарь поверхностей UI (ось H)

Модалок, drawer, alert **нет** — маршрут не рендерит контент (**fact**).

## Целевой UX (target vs as-built)

- *as-built:* жёсткая подсказка «нужна клиника» вместо забытого `/login`.
- *target:* со временем убрать ссылки на `/login` из внешних материалов (**gap** коммуникации).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- `frontend/src/__tests__/routePaths.test.ts` — `/login` в `ROUTE_PATHS.other`.
- Теста на факт редиректа **не найдено** (**gap**).

## Gap scan (вторая редакция)

- Поведение отличается от [`/sign-in`](./auth-legacy-sign-in.md) (там выбор таба): пользователи могут путать `/login` и `/sign-in` — при аудите копирайта рассмотреть единое сообщение.
