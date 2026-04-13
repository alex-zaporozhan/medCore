# Smoke: Docker Compose observability (OBS-1)

> **Цель:** закрепить DoD [§15b 1d](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) «≥1 end-to-end алерт» на **локальном/staging** стеке: Prometheus → Alertmanager → HTTP receiver (echo).  
> **Связь:** [05_PHASE_1D_OBSERVABILITY.md](../architecture/arch_plan/05_PHASE_1D_OBSERVABILITY.md), [07_metrics_observability.md](../architecture/07_metrics_observability.md), [deploy/grafana/README.md](../../deploy/grafana/README.md), [PLATFORM_FOUNDER_TOTP_AND_OBSERVABILITY.md](./PLATFORM_FOUNDER_TOTP_AND_OBSERVABILITY.md) (краткий LEAD-runbook: TOTP + стек).

## Предусловия

- Из корня репозитория: `docker compose up -d db redis migrations backend`
- Backend healthy (`/health` = 200)
- Переменная `GRAFANA_ADMIN_PASSWORD` в `.env` (опционально; иначе пароль Grafana по умолчанию из compose)

## Поднять стек наблюдаемости

```bash
docker compose --profile observability up -d
```

Сервисы слушают **только 127.0.0.1** (МП §11 M5):

| Сервис | URL |
|--------|-----|
| Prometheus | http://127.0.0.1:9090 |
| Alertmanager | http://127.0.0.1:9093 |
| Grafana | http://127.0.0.1:3001 |
| Echo (webhook Alertmanager) | http://127.0.0.1:8888 |

## Проверка scrape

1. Открыть Prometheus → **Status → Targets**: цель `backend` должна быть **UP**.
2. В **Graph** выполнить запрос, например `up{job="backend"}` — значение `1`.

## Проверка цепочки алерта (e2e)

1. В Alertmanager UI (**http://127.0.0.1:9093**) откройте вкладку **Alerts** — активные алерты отображаются после срабатывания правил из `deploy/prometheus/dental_booking_alerts.yml`.
2. **Доказательство доставки:** в конфиге `deploy/alertmanager/alertmanager.yml` receiver по умолчанию указывает на `alertmanager-webhook-echo`. При срабатывании алерта тело запроса видно в логах контейнера `dental_booking_alertmanager_echo` или через POST на echo (см. документацию образа `mendhak/http-https-echo`).
3. Для **staging/prod** OPS настраивает реальный receiver (Telegram и т.д.) по `deploy/alertmanager/alertmanager.telegram.example.yml`; токены не коммитить.

## Grafana

- Datasource Prometheus подхватывается из `deploy/grafana/provisioning/`.
- Импорт дашбордов: UI Grafana → **Dashboards → Import** → JSON из `deploy/grafana/dashboards/` (см. deploy/grafana/README.md).

## Автоматическая проверка в CI

- Синтаксис YAML правил: `tests/deploy/test_prometheus_alert_rules_yaml.py`.
- JSON дашбордов: `tests/core/test_grafana_dashboard_json.py`.

## Чеклист OPS (staging)

- [ ] Профиль `observability` поднят, targets UP  
- [ ] Хотя бы одно правило из `dental_booking_alerts.yml` переходит в firing при искусственном условии **или** естественно нагруженной среде  
- [ ] Alertmanager доставил уведомление в echo/Telegram  
- [ ] Grafana за VPN/BasicAuth вне локали (M5) — см. [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md)

---

**Версия:** 2026-04-06 (OBS-1).
