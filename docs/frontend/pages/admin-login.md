# Admin Login

## Метаданные

- **Path:** `/admin/login` (в `App.tsx` вложенный route `path="login"` под родителем `/admin`; канонический путь совпадает с `ROUTE_PATHS.admin.login`)
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `ClinicSignInPage`
- **Файл страницы:** `frontend/src/auth/ClinicSignInPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/auth/ClinicSignInPage.tsx`<br>`frontend/src/auth/SignInShell.tsx ← импорт из frontend/src/auth/ClinicSignInPage.tsx`<br>`frontend/src/auth/panels/ClinicStaffSignInPanel.tsx ← импорт из frontend/src/auth/ClinicSignInPage.tsx` |
| Строк (сумма по фрагментам) | 224 |
| Хуки (эвристика, union) | `useQueryClient` |
| Пути в строках `/v1/...` | `/v1/admin/auth/login` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Вход сотрудников и **владельца** клиники в Business OS по одному URL и одной форме (**`/admin/login`**): email + пароль, выдача admin JWT и привязка `admin_id` / `clinic_id` в клиенте. Это **не** пациентский контур и **не** кабинет основателя платформы — у них отдельные экраны и токены (см. `SignInShell`: «разные контура с разными токенами»).

## Логика и данные

- **Оболочка:** `SignInShell` + `ClinicStaffSignInPanel` (`frontend/src/auth/panels/ClinicStaffSignInPanel.tsx`).
- **API:** `POST /v1/admin/auth/login` — тело `{ email, password }` через `api.post` (`frontend/src/api/client.ts`); ответ: `access_token`, `admin_id`, `clinic_id`, `full_name`.
- **После успеха:** `setAdminToken`, `setAdminId`, `setAdminClinicId`, `queryClient.invalidateQueries({ queryKey: queryKeys.adminSession() })`, `navigate(returnTo, { replace: true })` где `returnTo = safeAuthReturnTo(searchParams.get("returnTo"), defaultReturnToForTab("clinic"))`.
- **React Query:** только инвалидация сессии; отдельного `useQuery` на странице нет.

## RBAC / entitlements / edition

Публичная страница входа; права в UI появляются после получения токена и загрузки сессии (**fact**). Entitlements не проверяются на самом логине.

## UI-скелет (as-built)

- **`SignInShell`** (двухколоночная сетка): слева маркетинговый блок — подпись «Dental Booking», заголовок **«Business OS для клиник»**, абзац про разные контуры и токены; три списка с иконками: **Безопасность** (раздельные токены пациент / персонал / платформа, HTTPS), **Запись и расписание**, **Омниканал и задачи**. Справа в `Paper` — контент страницы.
- Внутри карточки: `ClinicSignInPage` → заголовок **«Вход в Business OS»**, подзаголовок про рабочий email и роли; панель **`ClinicStaffSignInPanel`**: блок **«Клиника: сотрудники и владелец»** (текст: роль owner и права в админке; отдельного входа владельца нет), поля **Email** / **Пароль** (описание «Минимум 8 символов»), кнопка **«Войти в Business OS»**, ссылка **«На главную»**.

### Evidence / QA (скриншоты локальной сборки)

- URL вида `/admin/login?returnTo=%2Fadmin` — после успешного входа редирект на выбранный `returnTo` (по умолчанию — дашборд клиники).

## Инвентарь поверхностей UI (ось H)

| Тип | Триггер | Поведение |
|-----|---------|-----------|
| `Alert` (red, с крестиком) | `error` после неуспешного submit | Закрытие `onClose` (**fact**) |
| `TextInput` | Email, пароль | Валидация минимальной длины пароля (8) до submit (**fact**) |
| `Button` submit | Форма | `loading={loading}` на время запроса (**fact**) |
| Ссылка | «На главную» | `Link` на `ROUTE_PATHS.marketing.landing` (**fact**) |

`AdminDrawer` / `Modal` **нет**.

## Целевой UX (target vs as-built)

- *as-built:* единая форма для staff и owner; отдельного «владельческого» URL нет (как в копирайте панели).
- *target:* совпадает; опционально MFA/SSO — **gap** если появится в продукте.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- `routePaths` / публичные path.
- Нет интеграционного теста на успешный login (**gap**).

## Gap scan (вторая редакция)

- Ошибки — общее сообщение из `catch`; детализация кодов API в UI ограничена.
- Сравнить с требованиями rate limit на бэкенде для `/v1/admin/auth/login` (не отражено на странице).
