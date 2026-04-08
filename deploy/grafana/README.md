# Grafana dashboards (as code)

- **W1/W2 observability (L2 OPS «картинка»):** `dashboards/dental_booking_observability_w1_w2.json` — ERP L2 fallback, nightly vitrine, empty trusted; booking→ERP and Omni+AI chain errors; **ряд Platform SaaS — contour B (1b):** `platform_signup_intent_stuck`, `platform_signup_intent_dead_letter`; **notes** + **row** groupings. Имя файла — канон; отдельный дубликат `*_l2_observability.json` не требуется. JSON uses **`__inputs`** (`DS_PROMETHEUS`): on **Import**, map to your Prometheus datasource — no need to hand-edit `uid` in panels.  
- **Wave 7 booking/payment errors:** `dashboards/dental_booking_booking_errors_w7.json` — `booking_errors_total` by `code` and `source` (QA_ARCH BE4).
- **§27–§28 SOC (arch_plan/10):** `dashboards/dental_booking_security_soc_w10.json` — `spam_blocked_total`, `security_auth_failure_total`, `security_suspicious_request_total` (низкая кардинальность; алерты в `dental_booking_alerts.yml`).
- **Укрепление ≠ упрощение:** переносимость через `__inputs`; контекст — `docs/METRICS_PROTOCOL.md` и этот README.

See also `deploy/prometheus/dental_booking_alerts.yml`.

**Практический сценарий (TOTP основателя + где поднять Prometheus/Grafana):** [docs/operations/PLATFORM_FOUNDER_TOTP_AND_OBSERVABILITY.md](../../docs/operations/PLATFORM_FOUNDER_TOTP_AND_OBSERVABILITY.md).

## Docker Compose: Prometheus + Alertmanager + Grafana (фаза 1d)

Пошаговый smoke (targets, e2e алерт, чеклист OPS): [docs/operations/OBSERVABILITY_COMPOSE_SMOKE.md](../../docs/operations/OBSERVABILITY_COMPOSE_SMOKE.md).

Из корня репозитория:

1. Поднять приложение: `docker compose up -d db redis migrations backend` (и при необходимости остальное).
2. Включить стек наблюдаемости: `docker compose --profile observability up -d`.

Сервисы (порты **только на 127.0.0.1**, [SAAS_STRENGTHENING_MASTER_PLAN.md](../../docs/architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) §11 M5):

| Сервис | URL на хосте |
|--------|----------------|
| Prometheus | http://127.0.0.1:9090 |
| Alertmanager | http://127.0.0.1:9093 |
| Grafana | http://127.0.0.1:3001 (логин `admin`, пароль `GRAFANA_ADMIN_PASSWORD` из `.env` или значение по умолчанию из compose) |
| Echo (тело webhook Alertmanager) | http://127.0.0.1:8888 |

По умолчанию Alertmanager шлёт уведомления в контейнер `alertmanager-webhook-echo` (доказательство цепочки Prometheus → Alertmanager → HTTP без секретов). Для **Telegram** или внешнего webhook добавьте receiver в `deploy/alertmanager/alertmanager.yml` (см. черновик `deploy/alertmanager/alertmanager.telegram.example.yml`); токены не коммитить.

Datasource Prometheus подключается автоматически из `provisioning/datasources/datasource.yml`. Дашборды JSON из `dashboards/` — импорт вручную через UI Grafana (**Dashboards → Import**) с привязкой к источнику Prometheus.
