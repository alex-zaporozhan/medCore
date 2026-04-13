# Admin Stickers

## Метаданные

- **Path:** `/admin/stickers`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminStickersPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminStickersPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminStickersPage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminStickersPage.tsx` |
| Строк (сумма по фрагментам) | 60 |
| Хуки (эвристика, union) | — |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Информационный экран: в чатах используется встроенный набор стикеров. Кастомная загрузка своих изображений заявлена как следующая версия. На странице нет форм и вызовов API.

## Логика и данные

- **Хуки:** нет.
- **queryKey и мутации:** нет.
- **API:** нет.

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для сегмента `stickers` ключа нет (**fact**).
- Box не блокирует сегмент.

## UI-скелет (as-built)

`ContextBar` с заголовком «Стикеры» и два абзаца `Text`.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal, Menu:** на странице нет.

## Целевой UX (target vs as-built)

- *target:* библиотека стикеров клиники, загрузка файлов, модерация.
- *as-built:* только текст-заглушка.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Нет превью или списка встроенных стикеров из кода чата.
