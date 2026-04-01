# QA_ARCH — план доработок по отчёту W1/W2 (2026-03-20)

Цель: закрыть **6 направлений** из отчёта @QA_ARCH по unified backlog (критичные и средние риски + процесс).

| # | Направление | Действие |
|---|-------------|----------|
| 1 | `NONFUNCTIONAL_AUDIT_NEXT.md` | Файл **`docs/artifacts/NONFUNCTIONAL_AUDIT_NEXT.md`** поддерживается (§5 ERP L2, §6 пороги / кардинальность / runbook / Grafana / SLO); перекрёстные ссылки на `deploy/prometheus/dental_booking_alerts.yml` и подвал «Связанные артефакты» ↔ этот план. |
| 2 | Кардинальность Prometheus | `erp_aggregate_nightly_kind_failures_total`: лейблы только `aggregate_kind`. Цепочка **Booking→ERP** (`business_chain_booking_*`, локальные `booking_completion_*`): лейбл **`clinic_bucket`** (0…31) через `src/core/prometheus_labels.py::clinic_bucket_label`. |
| 3 | `docs/MIGRATION_UPGRADE.md` | Параграф: ревизия **`q3r4s5t6u7v8`** (watermark), флаги **`ERP_AGGREGATE_EVENT_*`**, порядок деплоя с Celery/Redis. |
| 4 | Trade-off nightly | Зафиксировать в `ARCH_DEV_ERP_VITRINES_026_TASKS.md` и §6 `NONFUNCTIONAL`: одна транзакция на клинику = атомарность всех четырёх витрин при сбое; drill-down по клинике — **логи** (`clinic_id` в structured log). |
| 5 | Риск «ложного нуля» по watermark | §6 `NONFUNCTIONAL`: инварианты, когда доверять пустому ряду; рекомендация: алерты по `erp_aggregate_read_fallback_total` + мониторинг **`erp_aggregate_empty_trusted_total`**. |
| 6 | Счётчик доверия пустому агрегату | Метрика `erp_aggregate_empty_trusted_total{aggregate_kind}` + инкремент в `resolve_erp_aggregate_rows` при успешном `trust_empty_if`. |

**Регрессия:** `pytest` по затронутым модулям; при изменении имён лейблов — проверить Grafana/Prometheus дашборды вне репо (runbook в §6).
