# QA_ARCH: вердикт по пакету LEAD (документация фронта + исправление Finance)

> **Дата:** 2026-04-08  
> **Роль:** зафиксировать, что принято, что отклонено как дубль или ошибка размещения, и куда смотреть дальше.

## 1. Что принято без оговорок

- **Исправление контура зарплат на `/admin/finance`:** опциональный `doctor_id` в `GET /api/v1/admin/clinics/{clinic_id}/payroll/transactions`, снятие взаимной блокировки React Query (`enabled` только при выбранном враче), заполнение селекта врачей из справочника (`useDoctors`), а не из производных salary-транзакций. Это соответствует правилу приёмки, описанному в [../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md) §8.

## 2. Что было формально или дублировало канон

- Три новых файла в **`documentation/`** с рубрикой, политикой копирайта и матрицей маршрутов **дублировали** уже существующую более полную рубрику в **`docs/architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md`** (матрица UI↔API, итерации A/B/C, ссылки на `docs/design/`).
- В одном из черновиков утверждалось, что каталога **`docs/design/`** нет — **неверно**: токены и playbook лежат в `docs/design/`.
- Размещение инженерной рубрики в **`documentation/`** не совпадало с политикой: клиенто-ориентированные материалы отдельно от **`docs/`**.

## 3. Что сделано при миграции (QA_ARCH)

- **Единый источник правды** по рубрике — `docs/architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md` (дополнен §8 кейсом Payroll, §6 — практика сверки API, ссылки на матрицу маршрутов и COPY_STYLE).
- **`docs/COPY_STYLE_POLICY_RU.md`**, **`docs/review/FRONTEND_ROUTE_AUDIT_MATRIX.md`**, **`docs/frontend/UI_THEME.md`** — канон для разработчиков.
- **`documentation/`** — короткие указатели на `docs/`, чтобы не плодить дубли.
- **[DOCUMENTATION_POLICY.md](../../DOCUMENTATION_POLICY.md)** и **[.gitignore](../../.gitignore)** — согласованы: `docs/` отслеживается в git; `documentation/` описан как контур для клиентов/интеграторов.

## 4. Остаточные задачи (не блокер этого PR)

- Массовый перенос прочих инженерных файлов из `documentation/` в `docs/` — отдельный эпик.

## 4.1 Регрессионный тест API

- [`tests/api/test_admin_payroll_transactions.py`](../../tests/api/test_admin_payroll_transactions.py) — `GET .../payroll/transactions` без `doctor_id` и с `doctor_id` (200, список).

## 5. Ссылки

- Рубрика: [../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md)  
- Матрица маршрутов: [FRONTEND_ROUTE_AUDIT_MATRIX.md](./FRONTEND_ROUTE_AUDIT_MATRIX.md)  
- Копирайт: [../COPY_STYLE_POLICY_RU.md](../COPY_STYLE_POLICY_RU.md)  
- Тема UI: [../frontend/UI_THEME.md](../frontend/UI_THEME.md)
