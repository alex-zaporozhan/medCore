# Фаза 1d — наблюдаемость (Phase_1d_Observability)

**Узлы МП mermaid:** `Prometheus_Grafana_compose`, `Alertmanager_TG_webhook`.  
**Связь МП:** §11, §28 (реестр имён), [07_metrics_observability.md](../07_metrics_observability.md), [SLO_CRITICAL_PATHS.md](../../operations/SLO_CRITICAL_PATHS.md).

## Архитектурный целевой образ

1. **Compose** — Prometheus + Grafana в profile или отдельном compose-файле (МП §11, §2 таблица).
2. **Alertmanager** — Telegram + настраиваемый HTTP webhook; дедупликация, severity, `runbook_url` (МП §11 M6).
3. **Cardinality** — не включать `organization_id` на каждом ряду в дефолтные scrapes; агрегаты и лимиты (МП §11 M1).
4. **Grafana** — не в публичной сети без auth; матрица кто видит тенантные срезы (МП §11 M5).
5. **Реестр имён** — новые `security_*`, `spam_*`, platform billing метрики только через реестр в [07_metrics_observability.md](../07_metrics_observability.md) (МП §11, PRINCIPLE цикл 2).

## Порядок работ @DEV / @OPS

1. Добавить сервисы в `docker-compose` (профиль `observability`) или отдельный compose-файл; подключить существующие правила из `deploy/prometheus`, дашборды `deploy/grafana`. **Сделано:** профиль в корневом `docker-compose.yml` + `deploy/prometheus/prometheus.yml`.
2. Настроить Alertmanager; один **end-to-end алерт** в staging (DoD §15b 1d).
3. Проверка на staging: новые метрики **не взрывают** cardinality (чеклист ARCH или автоматический контроль — МП §15b 1d).
4. Обновить [RELEASE_CHECKLIST.md](../../operations/RELEASE_CHECKLIST.md) и при необходимости [DR_RUNBOOK.md](../../operations/DR_RUNBOOK.md) — отсылка на M5 (МП §11 усиление).
5. **Контур B (подписка платформы, ADR-012):** добавить в `deploy/prometheus/dental_booking_alerts.yml` (после проверки cardinality) правила на аномалии по **`platform_billing_billing_revocation_total`** (`result` low-cardinality) и при необходимости **сочетание** с **`platform_billing_webhook_total`** (например всплеск `refund_reconciled` / `skipped_billing_revoked` при деградации провайдера или рассинхроне). Пороги и `for:` согласовать с OPS; runbook — отсылка к [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §12 и reconcile Основателя.
6. **Контур B — гейт каталога подписки (QA_ARCH, §4.3 модуля биллинга):** при появлении реального checkout с `billing_period` мониторить всплески `platform_billing_webhook_total` с `result` в множестве **`amount_mismatch_catalog`**, **`invalid_billing_period`**, **`unknown_plan_slug`**, **`billing_period_requires_plan_slug`**, **`missing_payment_amount`** — деньги могли пройти, а intent остался в `pending_payment` (`provision_last_error` = `tariff_gate:*`). Добавить панель Grafana и опциональный алерт после калибровки на staging; runbook — reconcile + проверка snapshot/intent; эпик закрытия обхода retry — [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **1b-F6**.
7. При добавлении правил — обновить реестр в [07_metrics_observability.md](../07_metrics_observability.md) и панели Grafana при появлении дашборда для контура B.

## DoD (МП §15b 1d)

- Grafana недоступна из интернета без auth.
- ≥1 e2e алерт в staging.
- Проверка cardinality выполнена для новых метрик/правил.

## Ссылки

- `deploy/prometheus/dental_booking_alerts.yml`
- `deploy/grafana/dashboards/`
- OPS smoke (OBS-1): [OBSERVABILITY_COMPOSE_SMOKE.md](../../operations/OBSERVABILITY_COMPOSE_SMOKE.md)

## Статус @DEV (2026-04-06)

- **Compose:** профиль `observability` в корневом `docker-compose.yml` — Prometheus (`deploy/prometheus/prometheus.yml`), Alertmanager (`deploy/alertmanager/alertmanager.yml`), Grafana с provisioning datasource, HTTP-echo для webhook Alertmanager; порты **127.0.0.1** (M5).
- **Правила:** в `dental_booking_alerts.yml` добавлены алерты контура B (ADR-012) на `platform_billing_webhook_total` / `platform_billing_billing_revocation_total` с `runbook_url` → `platform_subscription_billing.md` §12.
- **Реестр:** [07_metrics_observability.md](../07_metrics_observability.md) обновлён под факт правил и кардинальность.
- **OPS:** [RELEASE_CHECKLIST.md](../../operations/RELEASE_CHECKLIST.md) (staging e2e алерт + M5), [DR_RUNBOOK.md](../../operations/DR_RUNBOOK.md) §7; инструкция по стеку — [deploy/grafana/README.md](../../../deploy/grafana/README.md); пример Telegram — `deploy/alertmanager/alertmanager.telegram.example.yml`.

**Остаётся на OPS/staging:** подтвердить ≥1 e2e алерт на реальной среде, подобрать пороги `for:` / `rate` под трафик; при необходимости добавить `telegram_configs` в Alertmanager (без секретов в git).
