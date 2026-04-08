# Пациенты

> **Аудитория:** сотрудник клиники с доступом к ПДн.  
> **Источник UI:** `frontend/src/admin/pages/AdminPatientsPage.tsx`, навигация `AdminLayout.tsx`.

## Адрес

`/admin/patients`

## Доступ

Пункт **«Пациенты»** в боковом меню показывается только если у сессии есть право **`patients.pii.read`** (`ADMIN_PERM_PATIENTS_PII_READ`). Без права раздел в меню скрыт.

## Назначение

Каталог пациентов клиники: просмотр, создание записи пациента (кнопка **«Добавить пациента»** в заголовке при наличии).

- Заголовок области: **«Пациенты»**.

## См. также

- [../RBAC_RIGHTS_POLICIES_GUIDE.md](../RBAC_RIGHTS_POLICIES_GUIDE.md)  
- [../PRODUCT_KNOWLEDGE_BASE.md](../PRODUCT_KNOWLEDGE_BASE.md) §5.2
