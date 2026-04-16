# Передача проекта: пакет документации

Назначение: единая точка входа для команды, которая принимает репозиторий. Описание опирается на текущее состояние кода и конфигурации в дереве `dental_booking`.

## Состав пакета

| Файл | Содержание |
|------|------------|
| [01_technology_stack.md](./01_technology_stack.md) | Версии и роли основных технологий (backend, БД, очереди, frontend, интеграции). |
| [02_architecture_and_decisions.md](./02_architecture_and_decisions.md) | Слои приложения, мультитенантность, платежи и события, безопасность, масштабирование; ссылки на ADR и ключевые модули. |
| [03_repository_navigation.md](./03_repository_navigation.md) | Карта каталогов: где API, домен, инфраструктура, миграции, тесты, фронт, скрипты. |
| [04_delivery_operations_observability.md](./04_delivery_operations_observability.md) | CI/CD, Docker, окружения, метрики и алерты, типовые операции. |

## Связанные материалы вне этого каталога

- Переменные окружения: `.env.example` (канонический перечень с комментариями).
- Запуск и миграции: корневой `README.md`, `docs/RUN_SERVICES.md`, `docs/MIGRATION_UPGRADE.md`, `documentation/DEVELOPMENT.md`.
- Политика документации и границы `docs/` vs `documentation/`: `DOCUMENTATION_POLICY.md`.
- Решения по архитектуре (ADR): `docs/adr/README.md` и файлы `docs/adr/ADR-*.md`.
- Детальный разбор архитектуры из кода (расширенная карта): `docs/product_state/ARCHITECTURE_FROM_CODE.md`, `docs/product_state/INDEX.md`.

Рекомендуемый порядок чтения для онбординга: этот `README` → `01` → `03` → `02` → `04`, затем `.env.example` и `docs/adr/README.md` по мере задач.
