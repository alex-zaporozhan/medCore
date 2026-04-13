# Admin Client Reference

## Метаданные

- **Path:** `/admin/client-reference`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminClientReferencePage`
- **Файл страницы:** `frontend/src/admin/pages/AdminClientReferencePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminClientReferencePage.tsx`<br>`frontend/src/hooks/useAdminClientReference.ts ← импорт из frontend/src/admin/pages/AdminClientReferencePage.tsx`<br>`frontend/src/shared/ui/DataSkeleton.tsx ← импорт из frontend/src/admin/pages/AdminClientReferencePage.tsx`<br>`frontend/src/shared/ui/ContextBar.tsx ← импорт из frontend/src/admin/pages/AdminClientReferencePage.tsx` |
| Строк (сумма по фрагментам) | 159 |
| Хуки (эвристика, union) | `useAdminClientReference`, `useMutation`, `useQuery`, `useQueryClient`, `useUpdateAdminClientReferenceMutation` |
| Пути в строках `/v1/...` | `/v1/admin/client-reference` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Редактируемый Markdown-документ «справка для заказчика»: загрузка из API, правка в моноширинном поле, сохранение целиком. Контекст клиники не используется (организационный уровень админки).

## Логика и данные

- **Хуки:** `useAdminClientReference`, `useUpdateAdminClientReferenceMutation` из `@/hooks/useAdminClientReference`.
- **queryKey:** `queryKeys.adminClientReference()` — массив `admin-client-reference`.
- **API:** `GET /v1/admin/client-reference` и `PUT /v1/admin/client-reference` с телом JSON, поле `content` (строка). После успешного PUT инвалидация того же query.

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` для сегмента `client-reference` ключа нет (**fact**).

## UI-скелет (as-built)

Состояния загрузки / ошибки: `ContextBar` плюс `DataSkeleton` или `QueryErrorAlert`. Основной вид: `ContextBar`, подсказка `Text`, `Paper` с `ScrollArea` и большим `Textarea` (моноширинный стиль), кнопка «Сохранить».

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal, Menu, Stepper:** на странице нет.

## Целевой UX (target vs as-built)

- *target:* предпросмотр Markdown, версии, права «кто может менять».
- *as-built:* только сырой текст и сохранение; превью в UI нет.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Нет подтверждения перед перезаписью длинного документа.
- Ошибки мутации в UI не выведены отдельно (только query load).
