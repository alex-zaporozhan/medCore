# Grafana dashboards (as code)

- **W1/W2 observability (L2 OPS «картинка»):** `dashboards/dental_booking_observability_w1_w2.json` — ERP L2 fallback, nightly vitrine, empty trusted; booking→ERP and Omni+AI chain errors; **notes** + **row** groupings. Имя файла — канон; отдельный дубликат `*_l2_observability.json` не требуется. JSON uses **`__inputs`** (`DS_PROMETHEUS`): on **Import**, map to your Prometheus datasource — no need to hand-edit `uid` in panels.  
- **Wave 7 booking/payment errors:** `dashboards/dental_booking_booking_errors_w7.json` — `booking_errors_total` by `code` and `source` (QA_ARCH BE4).
- **Укрепление ≠ упрощение:** переносимость через `__inputs`, а не через удаление переменных; расширенные панели / multicluster — см. `docs/artifacts/QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG.md` §1.

See also `docs/artifacts/NONFUNCTIONAL_AUDIT_NEXT.md` §6.3 and `deploy/prometheus/dental_booking_alerts.yml`.
