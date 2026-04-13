# Поток 1b — Commerce и контур B: эпик-срезы

> **МП:** [03_PHASE_1B_COMMERCE_AND_UX.md](./03_PHASE_1B_COMMERCE_AND_UX.md), **§6**, **§15c**, **§16.6**.  
> **Долг:** [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **1b-F1…F9**.  
> **Модуль:** [platform_subscription_billing.md](../modules/platform_subscription_billing.md).  
> **Индекс:** [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md).  
> **PRC (L3):** [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) — **PRC-B1…B7**, пересечение **PRC-E1** / **§17.1**.

## QA_ARCH: префлайт для @ARCH и приёмка

**Цикл:** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](../LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md). Инспектор: [ROLE_QA_ARCH.md](../../ROLE_QA_ARCH.md). **PRC:** блок **B** (+ **PRC-E1** при multi-replica). **Модуль:** [platform_subscription_billing.md](../modules/platform_subscription_billing.md).

| Этап | Что должно быть зафиксировано |
|------|--------------------------------|
| **Выход @ARCH до @DEV** | **Sequence** (коротко): клиент → checkout → провайдер → **webhook B** → идемпотентность → провижининг → `organization_entitlements`; отдельно ветка **refund/chargeback** (ADR-012). Таблица **состояний сущностей** (intent / payment / org / entitlements). Для **1b-E3b**: **реестр веток YooKassa** (имя события → ожидаемое действие → HTTP ответ webhook) + какие ветки покрыты **pytest**; для OpenAPI — какие **operations** ссылаются на схемы ошибок (не «мертвые» components). Для **§17.1**: явное решение sticky vs outbox vs single replica — ссылка на [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md). |
| **Минимум в `QA_REPORT`** | Имена тестовых модулей на идемпотентность и **не-happy** ветки; grep-доказательство **двух секретов** (A/B) или эквивалент в конфиге; для E4/E5 — метрика/алерт + один сценарий «застрял провижининг» / «retry без обхода гейта». |
| **Красные флаги** | OpenAPI только с `200` и одним example; тесты только `succeeded`; один URL/секрет на оба контура; «reconcile» без UI или без runbook; объявление **1b-F2** закрытой без **1b-E3b**. |

| Срез | Содержание | DoD (минимум) |
|------|------------|----------------|
| **1b-E1** | Публичный каталог тарифов; `billing_period`; сумма из каталога | API + тесты гейта суммы; UI по согласованию с FE-E1 |
| **1b-E2** | Провижининг: первый AdminUser/invite + `organization_entitlements` из snapshot | E2E тест happy path после `paid`; нет «только Org+Clinic» |
| **1b-E3** | OpenAPI webhook B + матрица веток YooKassa (согласованный список SEC/Product) | `/openapi.json` или отдельный контракт + pytest веток |
| **1b-E3b** | Завершение **1b-F2** после минимального E3: полный контракт веток/кодов, reconcile UI | Согласованный реестр событий SEC+Product; при необходимости отдельный YAML; UI reconcile по модулю §7; `docs/artifacts/QA_REPORT_1b_E3b_webhook_contract.md` |
| **1b-E4** | Retry провижининга, DLQ/stuck state, метрики | Алерты + runbook фрагмент в модуле биллинга §10 |
| **1b-E5** | Согласованность **1b-F6**: retry не обходит гейт каталога без audit/override | Тест негативного обхода; документ в модуле §4.3 |
| **1b-E6** | Rate limit / WAF на публичном webhook B | OPS/edge + ссылка в **10-Q4** |

**Связь §17.1:** перед публичным трафиком на B при multi-replica — запись в [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md).

**Статус срезов:** **1b-E1** (каталог + checkout) и **1b-E3** (минимум: OpenAPI examples + pytest периметр) закрыты — [QA_REPORT_1b_E1_checkout.md](../../artifacts/QA_REPORT_1b_E1_checkout.md), [QA_REPORT_1b_E3_openapi_b.md](../../artifacts/QA_REPORT_1b_E3_openapi_b.md). **1b-E2** — [QA_REPORT_1b_E2_provision.md](../../artifacts/QA_REPORT_1b_E2_provision.md). **1b-E3b** — реестр [platform_yookassa_webhook_b_branches.yaml](../contracts/platform_yookassa_webhook_b_branches.yaml), отчёт [QA_REPORT_1b_E3b_webhook_contract.md](../../artifacts/QA_REPORT_1b_E3b_webhook_contract.md), reconcile UI + очередь tariff_gate; **1b-E4** — gauges `platform_signup_intent_stuck` / `dead_letter`, алерты Prometheus, runbook в модуле §10, панели Grafana W1/W2; **1b-E5** — гейт в `execute_platform_provision` + pytest; **1b-E6** — app rate limit + [deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md](../../../deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md) + ссылка в [10_CROSS_CUTTING](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md). **Приёмка QA_ARCH (пост-ревью потоков):** [QA_ARCH_PHASE_2_STREAM_EPICS_POSTDEV_REVIEW_2026-04-13.md](../../artifacts/QA_ARCH_PHASE_2_STREAM_EPICS_POSTDEV_REVIEW_2026-04-13.md). Хвосты эпика — [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (**1b-F6a**, **1b-F11**, **1b-F12**, **1b-F3**, **1b-F7–F9**).

**Очередь:** **1b-E3b** (хвост F2) → **1b-E4** → **1b-E5** → **1b-E6** (или параллель E6 по SEC при готовности edge).

## Хвост **1b-F2** после **1b-E3** (срез **1b-E3b**)

- Полный перечень веток уведомлений YooKassa для контура B (успех, отмена, возврат, промежуточные статусы по решению SEC/Product) и отображение в OpenAPI (`responses` / `examples` / при необходимости отдельный артефакт контракта).
- Матрица pytest по каждой согласованной ветке (не только unknown provider).
- Reconcile / очередь для оператора: см. [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §7 и МП **§16.6**; связка с **1b-E4** по DLQ/метрикам.

## Улучшения после **1b-E1** (backlog, до отдельного эпика)

- Верификация email до редиректа на оплату (или подтверждение владения ящиком) — согласование с **1b-F3** / [10_CROSS_CUTTING](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md).
- Идемпотентность повторного checkout (тот же email + план + период) — продуктовая политика (новый intent vs отказ).
- Выделенный маршрут маркетинга «Тарифы» (`/pricing` и т.п.) вместо только блока на `/` — см. **FE-E1**.

---

**Версия:** 2026-04-07.
