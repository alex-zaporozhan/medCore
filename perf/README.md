# Perf / нагрузка (QA_ARCH)

Минимальный повторяемый контур для **QA-AUDIT-003**:

- Скрипт без новых зависимостей: `scripts/perf_smoke.py` (httpx из проекта). Запуск против поднятого API:  
  `PERF_SMOKE_BASE_URL=http://127.0.0.1:8000 poetry run python scripts/perf_smoke.py`
- Несколько путей и таймаут: `PERF_SMOKE_PATHS=/health,/metrics` и `PERF_SMOKE_TIMEOUT_SECONDS=15`.
- Инвентаризация кандидатов на пагинацию (роутеры): `poetry run python scripts/inventory_list_scalar_all.py` (опция `--markdown`).
- Расширение: k6/Locust/Jenkins stage с профилем RPS — по envelope @LEAD и `docs/NONFUNCTIONAL_SCORECARD.md`.
