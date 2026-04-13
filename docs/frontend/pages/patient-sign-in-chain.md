# Patient Sign In Chain

## Метаданные

- **Path:** дерево `/c/:clinicSlug` (index редирект на `sign-in`), `/c/:clinicSlug/sign-in`, `/c/:clinicSlug/app` и дочерние сегменты как у `/app/*`; отдельно `/c/sign-in` редирект на лендинг с query-подсказкой
- **Зона:** patient-entry + app
- **Компонент(ы) в App.tsx:** `PatientEntryBoundary`, `PatientSignInPage` внутри `PatientAuthProvider`, затем `AppLayout` с тем же `PATIENT_APP_PAGE_BY_SEGMENT`, что и для `/app`
- **Файлы:** `frontend/src/contexts/PatientEntryContext.tsx`, `frontend/src/auth/PatientSignInPage.tsx`, `frontend/src/auth/panels/PatientPhoneAuthPanel.tsx`, `frontend/src/auth/SignInShell.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/auth/PatientSignInPage.tsx (часть цепочки)`<br>`frontend/src/auth/SignInShell.tsx ← импорт из frontend/src/auth/PatientSignInPage.tsx`<br>`frontend/src/auth/panels/PatientPhoneAuthPanel.tsx ← импорт из frontend/src/auth/PatientSignInPage.tsx`<br>`frontend/src/contexts/PatientEntryContext.tsx ← импорт из frontend/src/auth/PatientSignInPage.tsx`<br>… +1 файлов |
| Строк (сумма по фрагментам) | 498 |
| Хуки (эвристика, union) | `useAgreement`, `useAuth`, `usePatientAuth`, `usePatientEntry`, `useSendCode`, `useVerifyCode` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 1, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Вход и регистрация пациента в контексте slug клиники: SMS-код по телефону, согласия ПД и рассылки из настроек клиники, опционально OAuth VK/Яндекс. После verify — сохранение токена и редирект в `/c/{slug}/app` или в безопасный `returnTo`. Контур slug пробрасывается в API как `clinic_slug`.

## Логика и данные

- **Контекст:** `PatientEntryBoundary` кладёт `clinicSlug` из `useParams` в `PatientEntryContext`.
- **Страница входа:** `PatientSignInPage` рендерит `SignInShell` и `PatientPhoneAuthPanel`.
- **Хуки панели:** `usePatientAuth` (login); `useAgreement`, `useSendCode`, `useVerifyCode` из `useAuth` (используют `clinicSlug` из entry context); UTM из `getCurrentUtm`; `safeAuthReturnTo` для редиректа.
- **queryKey:** `auth`, `agreement`, clinicSlug для GET соглашения.
- **API:**
  - `GET /v1/auth/agreement?clinic_slug=…` — текст ПД и флаг рассылки
  - `POST /v1/auth/send-code` — phone, clinic_slug
  - `POST /v1/auth/verify-code` — код, согласия, профиль при регистрации, UTM-поля, clinic_slug
  - OAuth: редирект на `${API_BASE}/v1/auth/oauth/vk/start` или yandex с query redirect и clinic_slug

## RBAC / entitlements / edition

- Публичные маршруты до выдачи JWT (**fact**). Ошибки `UNKNOWN_CLINIC_SLUG` и `CLINIC_SLUG_REQUIRED` показываются в `Alert`.

## UI-скелет (as-built)

`SignInShell`, заголовок с отображением slug, `SegmentedControl` вход/регистрация, шаг телефон затем код, чекбоксы согласий, кнопки OAuth, в DEV — подсказка про код в логах API.

## Инвентарь поверхностей UI (ось H)

- **Modal:** просмотр текста политики ПД при регистрации.
- **AdminDrawer, GlassModal:** нет.

## Целевой UX (target vs as-built)

- *target:* единый дизайн с маркетинговым сайтом, i18n.
- *as-built:* привязка только к slug в пути; глобального patient URL нет по задумке.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под цепочку не найдено.

## Gap scan (вторая редакция)

- Legacy `/app` без slug в пути: `useAgreement` и send-code могут уйти без clinic_slug — поведение зависит от бэкенда.
- Редирект `/c/sign-in` на маркетинг — защита от неверного матчинга маршрута (см. комментарий в `App.tsx`).
