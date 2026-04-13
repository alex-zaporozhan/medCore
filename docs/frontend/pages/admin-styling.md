# Admin Styling

## Метаданные

- **Path:** `/admin/styling`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminStylingPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminStylingPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminStylingPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminStylingPage.tsx`<br>`frontend/src/shared/emptyStateHint.tsx ← импорт из frontend/src/admin/pages/AdminStylingPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminStylingPage.tsx` |
| Строк (сумма по фрагментам) | 333 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useUpdateClinicMutation` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Поля темы пациентского приложения для **выбранной клиники**: основной цвет (`--primary`), URL логотипа в шапке, глобальный шрифт. Отдельная карточка показывает **справочную** палитру базовой темы (имена CSS-переменных и пример hex) без редактирования из UI.

## Логика и данные

- **Хуки:** `useAdminClinic`, `useClinics`, `useUpdateClinicMutation` (`frontend/src/hooks/useClinics.ts`).
- **queryKey:** `queryKeys.clinics.list(includeDeleted)` для списка клиник; поиск текущей клиники в памяти клиента.
- **API:** `GET /v1/clinics`; `PUT /v1/clinics/{clinicId}` с полями `theme_primary_color`, `theme_logo_url`, `theme_font_family` (через общий `body` клиники).

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для `styling` ключа нет (**fact**).
- Box не блокирует сегмент.
- Без клиники в шапке — `EmptyStateHint`.

## UI-скелет (as-built)

`ContextBar` («Оформление») — пояснение — `Card` с тремя `TextInput` и кнопкой «Сохранить» (`loading` на локальном `saving`) — второй `Card` со списком переменных палитры.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` / `GlassModal` / `Modal`:** нет.

## Целевой UX (target vs as-built)

- *target:* превью темы в iframe или story, загрузка логотипа в хранилище вместо сырого URL.
- *as-built:* простые строковые поля и справочная палитра.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Палитра в коде статична; расхождение с реальными токенами темы возможно при смене дизайн-системы.
