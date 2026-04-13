# Admin Clinics

## Метаданные

- **Path:** `/admin/clinics`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminClinicsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminClinicsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminClinicsPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminClinicsPage.tsx`<br>`frontend/src/api/types.ts ← импорт из frontend/src/admin/pages/AdminClinicsPage.tsx` |
| Строк (сумма по фрагментам) | 1020 |
| Хуки (эвристика, union) | `useClinics`, `useCreateClinicMutation`, `useUpdateClinicMutation` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 3, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Список организаций (клиник) в контуре админа: просмотр таблицей, создание и редактирование карточки (контакты, slug для публичных URL, тип бизнеса, кастомная лексика «пациент/клиент», «врачи/мастера»).

## Логика и данные

- **Хуки:** `useClinics`, `useCreateClinicMutation`, `useUpdateClinicMutation` (`frontend/src/hooks/useClinics.ts`); `useDisclosure` (Mantine) для модалки.
- **Типовые API (`/v1/...`):**
  - `GET /v1/clinics` (+ query при расширении списка в хуке)
  - `POST /v1/clinics`
  - `PUT /v1/clinics/{clinicId}`

## RBAC / entitlements / edition

- **fact:** Сегмент `clinics` **не** задан в `SEGMENT_ENTITLEMENT` (`adminEntitlementNav.ts`) — отдельного SaaS-ключа `adminShellSegmentEntitlementKey` для этого пункта нет.
- **fact:** Ограничения на создание/редактирование определяются бэкендом на маршрутах `/v1/clinics*`.

## UI-скелет (as-built)

- `ContextBar` «Клиники» + «Добавить клинику».
- Состояния: `DataSkeleton` при загрузке, `QueryErrorAlert` при ошибке.
- Таблица: название, адрес, телефон, email, тип/лексика, кнопка «Редактировать».
- Пустой список — текст-подсказка.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer:** нет на странице.
- **GlassModal:** одна модалка создания/редактирования (`opened` из `useDisclosure`), форма полей + «Сохранить» с локальным `saving` и `mutateAsync` + `refetch` (**fact:** ошибки без отдельного `Alert` внутри модалки — зависят от проброса из мутаций/try).
- **Menu / Mantine Modal:** нет.

## Целевой UX (target vs as-built)

- *target:* быстрый онбординг первой клиники и правка slug/лексики без ошибок в публичных ссылках.
- *as-built:* таблица + одна модалка на create/edit.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** выделенных тестов страницы не найдено.

## Gap scan (вторая редакция)

- Нет inline-валидации slug на клиенте (кроме подсказки в label) — риск 4xx с API; при продуктовой политике стоит явно показывать ответ бэкенда в модалке.
