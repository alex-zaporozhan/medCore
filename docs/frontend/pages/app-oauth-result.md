# App Oauth Result

## Метаданные

- **Path:** `/oauth/result` (`ROUTE_PATHS.other.oauthResult`)
- **Зона:** app (пациентский контур, коллбек OAuth)
- **Компонент(ы) в App.tsx:** `OAuthResultPage` (вложен в ветку с layout приложения — см. `App.tsx`)
- **Файл страницы:** `frontend/src/app/pages/OAuthResultPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/app/pages/OAuthResultPage.tsx`<br>`frontend/src/contexts/PatientAuthContext.tsx ← импорт из frontend/src/app/pages/OAuthResultPage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/app/pages/OAuthResultPage.tsx` |
| Строк (сумма по фрагментам) | 340 |
| Хуки (эвристика, union) | `usePatientAuth`, `useQueryParams` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Обработка возврата с OAuth-провайдера: разбор query, установка пациентской сессии при успехе, иначе — редирект на лендинг с кодами `patientEntry` для сообщений об отмене/ошибке.

## Логика и данные

- **Хуки:** `usePatientAuth().login`, `useNavigate`, `useLocation` + `useMemo` для `URLSearchParams`.
- **Query (fact):** `oauth` (`vk` | `yandex` | иное → подпись «соцсеть»), `status`, `token`, `patient_id`.
- **Ветвление в `useEffect`:**
  - `status=ok` + `token` + `patient_id` → `login(token, patientId)`, затем `navigate` на текущий путь если он под `/app`, иначе на `ROUTE_PATHS.patient.home`, `replace`.
  - `status=cancelled` → лендинг с `?patientEntry=oauth-cancelled`.
  - `status` ∈ `error` | `state_invalid` | `provider_error` → сообщение на странице ~3 с, затем лендинг `?patientEntry=oauth-error`.
  - иначе → лендинг `?patientEntry=need-clinic`.
- **API:** HTTP к бэкенду на этой странице **нет** — токен приходит в query (контракт с провайдером/бэкенд-редиректом).

## RBAC / entitlements / edition

Публичная страница коллбека; после `login` действует пациентская сессия (**fact**).

## UI-скелет (as-built)

- `Center` → `Paper` → `Stack`: заголовок с именем провайдера, `Loader`, поясняющий `Text` (зависит от `status`).

## Инвентарь поверхностей UI (ось H)

`Modal` / `Drawer` / `Menu` **нет**. Интерактив только косвенно через эффект навигации; визуально — `Loader` + текст (**fact**).

## Целевой UX (target vs as-built)

- *as-built:* быстрый переход в `/app` при успехе; ошибки не «молча», но уводят на главную через таймер.
- *target:* для ошибок можно показать кнопку «повторить» без ожидания 3 с (**gap** UX).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Маршрут в паритете публичных path (`routePaths`).
- Нет vitest на матрицу query → навигация (**gap**).

## Gap scan (вторая редакция)

- Зависимость от `window.location.pathname` для выбора редиректа — учитывать зеркало `/c/:slug/app/...` при расширении сценариев.
- Безопасность: токен в URL — ограниченное окно, не логировать в проде (**gap** ops).
