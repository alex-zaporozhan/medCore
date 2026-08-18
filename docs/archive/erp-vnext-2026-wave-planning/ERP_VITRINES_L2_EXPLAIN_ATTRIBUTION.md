# ERP L2 — EXPLAIN / индексы для ROI / attribution (QA_ARCH A15)

> **Цель:** зафиксировать план эталонного запроса `ErpReportsRepository.get_attribution_revenue_by_period` и существующие индексы, чтобы ops/DBA могли повторить `EXPLAIN (ANALYZE, BUFFERS)` на staging без «угадывания» SQL.

## 1. Эталонный запрос (логика)

Источник: `src/application/services/erp_reports_repository.py` — `get_attribution_revenue_by_period`.

- **Фильтр:** `financial_transactions.clinic_id`, `type = 'income'`, `happened_at` в полуинтервале `[date_from 00:00, date_to+1)`.
- **Join:** `LEFT OUTER JOIN visit_attributions ON visit_attributions.id = financial_transactions.visit_attribution_id`.
- **Группировка:** `visit_date` (= `date(happened_at)`), `traffic_source_id`, `campaign_id` (из join; могут быть NULL).
- **Сортировка результата:** `visit_date`, `traffic_source_id NULLS LAST`, `campaign_id NULLS LAST` (согласовано с чтением из витрины `ErpAggregateService.fetch_attribution_revenue_aggregate`).

## 2. Индексы (уже в схеме)

| Таблица | Индекс | Назначение |
|---------|--------|------------|
| `financial_transactions` | `idx_fin_tx_clinic_happened_at` (`clinic_id`, `happened_at`) | узкий по клинике и окну дат |
| `financial_transactions` | `idx_fin_tx_clinic_visit_attr` (`clinic_id`, `visit_attribution_id`) | связка с атрибуцией |
| `financial_transactions` | `ix_financial_transactions_visit_attribution_id` | FK к `visit_attributions` |
| `visit_attributions` | `ix_visit_attributions_clinic_id` и др. | доступ к источнику кампании |

Новая миграция под A15 **не вводилась**: для типичного окна отчёта фильтр по `(clinic_id, happened_at)` + join по `visit_attribution_id` покрывается перечисленными индексами; при росте данных повторить `EXPLAIN` и при seq scan на больших клиниках рассмотреть составной индекс под конкретный план (отдельный ADR).

## 3. Как снять EXPLAIN на PostgreSQL

Подставить реальные `clinic_id`, даты и при необходимости ограничить выборку:

```sql
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT ... -- текст запроса, эквивалентный ORM (см. репозиторий);
```

Рекомендация: снимать на **staging** с объёмом, близким к prod, и хранить вывод в тикете при регрессии latency отчёта.

## 4. Связанные пункты бэклога

- **A18:** детерминированный порядок materials — см. `ORDER BY` в `get_visit_inventory_by_period` и сортировка в `fetch_inventory_aggregate`; OpenAPI — поля `items` в `MaterialsByPeriodReport` / `RoiBySourceReport`.
