# Лиды (лог)

> **Аудитория:** сотрудник с правом просмотра лида.  
> **Источник:** `frontend/src/admin/pages/AdminLeadsLogPage.tsx`, `AdminLayout.tsx`.

## URL

`/admin/leads-log`

## Доступ

Пункт меню **«Лиды (лог)»** виден только при праве **`leads.log.view`**.

## Поведение

Страница рендерит `AdminTasksPage` с `mode="leads-log"` и заголовком **«Лиды (лог)»** — тот же канбан, что задачи, но отдельный поток.

## См. также

- [../PRODUCT_KNOWLEDGE_BASE.md](../PRODUCT_KNOWLEDGE_BASE.md) §5.2
