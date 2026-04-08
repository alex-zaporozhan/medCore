# Вход в админку

> **Аудитория:** сотрудник клиники.  
> **Источник UI:** `frontend/src/admin/pages/AdminLoginPage.tsx` (актуальность сверяйте с кодом).

## Адрес

`/admin/login` (`ROUTE_PATHS.admin.login` в `routePaths.ts`).

## Что показывает экран

- Заголовок: **«Вход в админку»**.
- Поля: **Email**, **Пароль** (минимум **8** символов, константа `MIN_PASSWORD_LENGTH` в компоненте).
- Подсказка: пароль не короче 8 символов; данные по защищённому соединению.
- Отправка формы: `POST /v1/admin/auth/login` с телом `{ email, password }` (email приводится к lower-case); при успехе сохраняются токен и идентификаторы сессии, выполняется переход на `/admin`.
- Ссылка **«На главную»** ведёт на `/`.

## После входа

Маршрутизация ведёт в оболочку админки с дашбордом `/admin` (`App.tsx`, `AdminAuthGuard`).

## См. также

- [ADMIN_DASHBOARD.md](./ADMIN_DASHBOARD.md)  
- [../PRODUCT_KNOWLEDGE_BASE.md](../PRODUCT_KNOWLEDGE_BASE.md) §5.2  
- [../RBAC_RIGHTS_POLICIES_GUIDE.md](../RBAC_RIGHTS_POLICIES_GUIDE.md)
