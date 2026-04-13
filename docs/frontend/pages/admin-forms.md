# Admin Forms

## Метаданные

- **Path:** `/admin/forms`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminFormsPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminFormsPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminFormsPage.tsx`<br>`frontend/src/api/types.ts ← импорт из frontend/src/admin/pages/AdminFormsPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminFormsPage.tsx`<br>`frontend/src/shared/ui/EmptyState.tsx ← импорт из frontend/src/admin/pages/AdminFormsPage.tsx`<br>… +1 файлов |
| Строк (сумма по фрагментам) | 1324 |
| Хуки (эвристика, union) | `useAdminFormSubmissionDetail`, `useAdminFormSubmissions`, `useAdminFormTemplates`, `useUpsertAdminFormTemplate` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 5, GlassModal: 0, Modal: 0, Menu: 6 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Два режима: шаблоны цифровых форм (создание и правка JSON-схемы, флаги подписи и обязательности для визита) и список отправленных форм с фильтрами и просмотром детали (данные, подпись). Поддержка deep link: `patient_id` из query string подставляется в фильтр.

## Логика и данные

- **Хуки:** `useAdminFormTemplates`, `useAdminFormSubmissions`, `useAdminFormSubmissionDetail`, `useUpsertAdminFormTemplate` (`frontend/src/hooks/useForms.ts`).
- **queryKey:** `["admin","forms","templates"]`; `["admin","forms","submissions", params]`; `["admin","forms","submission", submissionId]`.
- **Мутация:** `POST /v1/admin/forms/templates` или `PATCH /v1/admin/forms/templates/{id}`.
- **API:** `GET /v1/admin/forms/templates`; `GET /v1/admin/forms/submissions` с query; `GET /v1/admin/forms/submissions/{id}`. Хук `useSendFormLink` (`POST /v1/admin/forms/send-link`) на странице не подключён (**gap**, если нужна отправка ссылок из этого UI).

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для сегмента `forms` отдельного ключа нет (**fact**).
- Box не скрывает сегмент (не входит в `BOX_DISALLOWED_ADMIN_SEGMENTS`).

## UI-скелет (as-built)

`ContextBar` с `SegmentedControl` (шаблоны / отправленные). Шаблоны: описание, кнопка «Новый шаблон», `Table` и `Menu` (редактировать, дублировать; пункт «Удалить» disabled с подсказкой про отсутствие API). Отправленные: фильтры `TextInput`, `Table`, кнопка «Детали» и клик по строке. Ошибки — `QueryErrorAlert`.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` (два экземпляра):**
  1. Деталь отправки: `opened={!!selectedSubmissionId}`, данные из `useAdminFormSubmissionDetail`, подпись как картинка при наличии.
  2. Редактор шаблона: создание или правка, `JsonInput` схемы, переключатели, сохранение через `upsertTemplate` с `loading={upsertTemplate.isPending}`.
- **`Menu`:** действия по строке шаблона (три точки).
- **`Modal` / `GlassModal`:** нет; ошибки парсинга JSON — `alert` в браузере.

## Целевой UX (target vs as-built)

- *target:* конструктор схемы или подсветка JSON без `alert`.
- *as-built:* два drawer; удаление шаблона на API не реализовано (явно в UI).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- `alert` для ошибок JSON и пустых полей — слабее остального admin UX.
- Удаление шаблона отсутствует (disabled в меню).
- Отправка ссылки на форму не интегрирована при наличии хука `useSendFormLink`.
