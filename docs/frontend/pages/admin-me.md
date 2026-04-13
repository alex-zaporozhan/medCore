# Admin Me

## Метаданные

- **Path:** `/admin/me`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminStaffCabinetPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminStaffCabinetPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminStaffCabinetPage.tsx` |
| Строк (сумма по фрагментам) | 131 |
| Хуки (эвристика, union) | `useMyStaffProfile`, `usePatchMyStaffProfile`, `useUploadMyStaffAvatar` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Личный кабинет сотрудника в админке: просмотр ФИО, email, должности (из справочника), загрузка аватара, редактирование поля «о себе» (bio).

## Логика и данные

- **Хуки:** `useMyStaffProfile`, `usePatchMyStaffProfile`, `useUploadMyStaffAvatar` (`frontend/src/hooks/useMyStaffCabinet.ts`).
- **queryKey:** `["staff-me-profile"]`.
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/staff/me/profile`
  - `PATCH /v1/admin/staff/me/profile` (тело: `{ bio?: string }`)
  - `POST /v1/admin/staff/me/avatar` (`multipart/form-data`, поле `file`)

## RBAC / entitlements / edition

- **fact:** Сегмент `me` **не** маппится в `adminShellSegmentEntitlementKey` — блокировки по SaaS-entitlement из `SEGMENT_ENTITLEMENT` для этого пути нет (as-built).
- **fact:** Ограничения редактирования определяются бэкендом на перечисленных эндпоинтах; на странице нет дополнительных permission-checkов (кроме disabled-состояний при loading/pending).

## UI-скелет (as-built)

- `ContextBar` «Личный кабинет» + короткий подзаголовок.
- `QueryErrorAlert` при ошибке загрузки профиля.
- Карточка: `Avatar`, ФИО/email/должность, скрытый file input, кнопки «Выбрать фото» / «Загрузить».
- Карточка «О себе»: `Textarea`, «Сохранить», inline-тексты ошибок patch/upload.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer / GlassModal / Mantine Modal / Menu / Stepper:** нет (as-built).
- **Alert:** не используется; ошибки — `QueryErrorAlert` и красный `Text` под формой.

## Целевой UX (target vs as-built)

- *target:* минимальный self-service профиля без лишних шагов.
- *as-built:* два блока (аватар + bio), явные состояния loading и ошибок мутаций.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** тестов страницы не найдено.

## Gap scan (вторая редакция)

- Нет превью аватара до загрузки (только имя файла) — при желании улучшить UX.
- Расширение полей профиля потребует синхронизации с DTO бэкенда и этим паспортом.
