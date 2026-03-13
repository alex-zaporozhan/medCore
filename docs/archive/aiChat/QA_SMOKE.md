# Дымовые тесты после деплоя

Минимальный набор проверок после выката: health, auth send-code (с моком в TESTING=1), один GET admin с admin_auth, один POST payments/webhook.

## Запуск

Из корня проекта (требуется тестовая БД и Redis, `TESTING=1` в окружении выставляется conftest):

```bash
poetry run pytest tests/smoke/test_smoke.py -v
```

В CI после деплоя можно запускать этот набор для быстрой проверки доступности API.
