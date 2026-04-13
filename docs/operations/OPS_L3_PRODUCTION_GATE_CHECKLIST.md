# OPS: ворота Production Launch (L3) — консолидированный чеклист

> **Роли:** OPS исполняет; **LEAD** подписывает периметр; **QA_ARCH** прикладывает evidence.  
> **Матрица PRC:** [STREAM_PRODUCTION_READINESS.md](../architecture/arch_plan/STREAM_PRODUCTION_READINESS.md).  
> **Общий релиз:** [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md).

## 1. Секреты (PRC-A3)

- [ ] Критичные ключи не только в `.env` на ВМ: **AWS Secrets Manager** (или Vault / K8s External Secrets) с JSON телом.
- [ ] В runtime API/Celery заданы `AWS_SECRETS_MANAGER_SECRET_ID` (+ регион при необходимости). См. [PLATFORM_AND_TENANT_SECRETS_RUNBOOK.md](./PLATFORM_AND_TENANT_SECRETS_RUNBOOK.md), код `src/core/runtime_secrets.py`.
- [ ] Ротация webhook B и founder JWT согласована с SEC; тикет OPS: _ссылка_.

## 2. Edge / WAF / rate limit (PRC-B7, 10-Q4)

- [ ] `POST /api/v1/platform/billing/webhooks/yookassa` защищён на edge (лимиты/WAF по политике). См. [deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md](../../deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md).
- [ ] `PUBLIC_RATE_LIMIT_TRUSTED_PROXY_CIDRS` соответствует реальным ingress CIDR (иначе лимиты по неверному IP).
- [ ] Публичный signup/checkout при необходимости — те же принципы (см. [STREAM_CROSS_CUTTING_GO_LIVE.md](../architecture/arch_plan/STREAM_CROSS_CUTTING_GO_LIVE.md)).

## 3. §17.1 Multi-replica (PRC-E1, 1b-F12)

- [ ] Если **`replicas(API) ≥ 2`**: заполнена таблица governance в [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](./API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md) (факт ingress, outbox включён для контура B, или зафиксирован sticky singleton / ADR риска). Репозиторий: outbox-путь контура B задокументирован (2026-04-08); runtime-строки OPS/LEAD — при первом scale-out.
- [ ] Подпись OPS + LEAD с датой.

## 4. DR / RPO / RTO (PRC-E2, 2-F2)

- [ ] После реального restore на staging: целевые и **фактические** RPO/RTO в [DR_RUNBOOK.md](./DR_RUNBOOK.md) §1.
- [ ] Журнал учений §6.1 актуален (квартальный U-009).

## 5. Наблюдаемость (PRC-F1, PRC-F2)

- [ ] Grafana **не** в открытом интернете без auth; prod — VPN/reverse-proxy.
- [ ] Smoke observability: [OBSERVABILITY_COMPOSE_SMOKE.md](./OBSERVABILITY_COMPOSE_SMOKE.md); на staging — ≥1 доставка алерта до Alertmanager/канала OPS.
- [ ] Пороги Prometheus для contour B/outbox откалиброваны или зафиксированы как «стартовые» с датой пересмотра.

## 6. Celery / фон (контур B)

- [ ] Beat: `platform_billing.expire_stale_signup_intents`, `domain_outbox.dispatch_pending` (и прочие обязательные задачи) включены в prod.
- [ ] Worker имеет доступ к БД и Redis.

## 7. Ссылка для QA_ARCH

После выполнения: один OPS-тикет или run с датой; шаблон evidence для @QA_ARCH — **приложение A** в [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md).

**Версия:** 2026-04-06 (QA_ARCH / Wave 1)
