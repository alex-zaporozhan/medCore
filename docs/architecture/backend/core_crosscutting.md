# Core: сквозная инфраструктура

> Каталог: `src/core/*.py` (множество модулей).

## Назначение

Конфигурация, логирование, метрики, edition (Box/Enterprise), безопасность (sanitizer, tokenization), сообщения пользователю, IP, Prometheus labels — всё, что импортируется из разных слоёв без циклов с бизнес-логикой.

## Как это работает (сквозная логика)

1. **Конфиг:** `src/core/config.py` — Pydantic `Settings` с чтением env; один объект `settings` импортируется в `main`, роутеры, сервисы, Celery. Отсюда же DSN primary/replica, Redis, JWT секреты, лимиты rate limit, флаги ERP-кэшей.
2. **Логи:** `setup_logging()` вызывается при импорте `main` до создания приложения; дальше модули используют `logging.getLogger(__name__)`.
3. **Метрики:** `src/core/metrics.py` при отсутствии `prometheus_client` подменяет метрики no-op объектами, чтобы импорт API не падал. Путь для лейблов нормализуется (`normalize_metrics_path`, `metrics_path_for_request`) — см. тесты `tests/core/test_metrics_path.py`.
4. **Edition:** `src/core/edition.py` читает переменную окружения редакции; `is_box_edition()` используется в API (`require_crm_enterprise_edition`) и на фронте зеркально через `VITE_EDITION` (`frontend/src/config/edition.ts`) — две стороны одного продукта.
5. **Безопасность:** JWT создаётся/парсится в `src/core/security.py`; AI/PII — `ai_sanitizer`, `tokenization`; IP для rate limit — `request_ip` (подключается в местах, где нужен ключ лимита).

## Ключевые модули

| Модуль | Роль |
|--------|------|
| `config.py` | `Settings` (Pydantic Settings): env, БД primary/replica, Redis, JWT, rate limits, feature flags кэшей ERP/staff directory, omni rate limits. |
| `metrics.py` | Prometheus метрики, нормализация путей, `render_prometheus_metrics`; fallback no-op без `prometheus_client`. |
| `prometheus_labels.py` | Ограничение кардинальности labels (см. тесты `tests/core/test_prometheus_labels.py`). |
| `logging.py` | Настройка логирования (`setup_logging` в `main`). |
| `edition.py` | Режим поставки Box vs Enterprise для API/фич. |
| `ai_sanitizer.py`, `tokenization.py` | Безопасность AI/PII. |
| `request_ip.py`, контекст запроса | Если есть — для rate limit и аудита. |

## Связь с остальным кодом

- `main.py` тянет `settings`, metrics, logging.
- Роутеры и сервисы тянут `settings` для лимитов и URL внешних сервисов.

## Статус

| Аспект | Статус |
|--------|--------|
| Централизованный config | Реализовано |
| Метрики опциональны при отсутствии библиотеки | Реализовано |

## Непонятное

- Полный перечень `src/core/*.py` меняется; при добавлении модуля — обновить этот список или сослаться на glob.

### Enterprise-аудит (честная оценка)

- **Критические риски:** edition Box/Enterprise в env — при ошибке конфигурации гейт на бэкенде и UI может разъехаться.
- **Средние риски:** rate limits завязаны на settings; без централизованного dashboard сложно ловить злоупотребления.
- **Формально / недоделано:** SLO/SLI как продукт не зафиксированы в `core`.
- **Рекомендуемые доработки:** единый модуль feature flags с версионированием контракта для фронта и API.

### Соответствие фактам (проверка)

- `settings`, `metrics.py` no-op ветка, `edition.py` — по статическому чтению `src/core/`.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** секреты и ключи провайдеров в настройках клиники — компрометация админки = компрометация платежей; глубина защиты — вне этого файла.
- **Что усилить:** единый реестр feature flags с версией контракта для фронта и API.
- **С нуля:** централизованный secret manager (Vault и т.д.) — вне репозитория.
- **БД:** не напрямую; косвенно — шифрование полей в entity.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) (§4).
