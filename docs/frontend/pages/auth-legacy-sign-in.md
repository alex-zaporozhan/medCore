# Auth Legacy Sign In

## Метаданные

- **Path:** `/sign-in` (`ROUTE_PATHS.other.signIn`)
- **Зона:** patient-entry / legacy routing
- **Компонент(ы) в App.tsx:** `LegacySignInRedirect`
- **Файл страницы:** `frontend/src/auth/LegacySignInRedirect.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/auth/LegacySignInRedirect.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/auth/LegacySignInRedirect.tsx` |
| Строк (сумма по фрагментам) | 242 |
| Хуки (эвристика, union) | — |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Обратная совместимость со старым единым URL `/sign-in?tab=…`: перенаправление на актуальные входы основателя, админки клиники или на главную с подсказкой для пациента, с сохранением `returnTo` в query где уместно.

## Логика и данные

- **Хуки:** `useNavigate`, `useSearchParams`, `useEffect` (однократный редирект при монтировании).
- **Query:** `tab` — `founder` | `clinic` | иное; `returnTo` — пробрасывается в `URLSearchParams` целевого маршрута (кроме финального fallback на лендинг, где задаётся только `patientEntry`).
- **Маршрутизация (fact):**
  - `tab=founder` → `navigate` на `ROUTE_PATHS.platform.login` + search.
  - `tab=clinic` → `ROUTE_PATHS.admin.login` + search.
  - иначе → `ROUTE_PATHS.marketing.landing` с `?patientEntry=need-clinic`.
- **API:** нет.

## RBAC / entitlements / edition

Публичный редирект; целевые страницы сами применяют свои гейты (**fact**).

## UI-скелет (as-built)

- Только `Center` на весь viewport и `Loader` на время выполнения `useEffect` (кратковременно).

## Инвентарь поверхностей UI (ось H)

Отдельных `Modal` / `Drawer` / `Menu` / `Alert` **нет**; единственная поверхность — индикатор загрузки (**fact**).

## Целевой UX (target vs as-built)

- *as-built:* `replace: true`, чтобы не засорять историю.
- *target:* со временем удалить legacy URL из маркетинга и оставить редирект только для старых закладок (**gap** коммуникации).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- `frontend/src/__tests__/routePaths.test.ts` — путь `/sign-in` в `ROUTE_PATHS.other` / паритет публичных path.
- Отдельных тестов на матрицу `tab` **не найдено** (**gap**).

## Gap scan (вторая редакция)

- Нет обработки некорректного `returnTo` здесь — делегировано целевым экранам (`safeAuthReturnTo` и т.д. на стороне login).
- Миграция ссылок в письмах/доках на прямые `/platform/login` и `/admin/login` снизит трафик через этот компонент.
